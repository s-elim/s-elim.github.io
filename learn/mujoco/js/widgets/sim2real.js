// sim2real: the delay margin of the Level 8 pendulum controller, live (Lesson 19.1). The pendulum holds
// 0.05 rad under u = kp (q* - q) - kd v + m g L sin q (compensation for the nominal 1 kg). The plant has
// MuJoCo's actuator delay (200-sample history, linear interpolation), an optional first-order motor lag
// (dyntype filterexact), a torque gain (gear) and a mass; the controller can run slower than the simulation
// and can read a 4096-count encoder with differenced, low-pass-filtered velocity. The predicted margin uses
// the same loop model as examples/l19_1_sim_to_real.py; "Find the margin" bisects in simulation.
//
// Config: {"title": "...", "height": 260}

import { h, frame, slider, select, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";
import { compileXml } from "../runtime.js";

const H = 0.002, MGL = 4.905, TARGET = 0.05, COUNTS = 4096;

function xmlFor(p) {
  const dyn = p.lag > 0 ? `dyntype="filterexact" dynprm="${p.lag}"` : `dyntype="none"`;
  return `
<mujoco model="pendulum_sim2real">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="${H}"/>
  <visual><headlight diffuse=".6 .6 .6"/></visual>
  <worldbody>
    <light pos="0 -1 2" dir="0 1 -2"/>
    <geom name="floor" type="plane" size="1 1 0.05" pos="0 0 -0.2" rgba=".85 .87 .85 1"/>
    <geom type="box" size="0.04 0.04 0.04" pos="0 0 1" rgba=".3 .3 .3 1" contype="0" conaffinity="0"/>
    <body name="pole" pos="0 0 1">
      <joint name="hinge" type="hinge" axis="0 1 0"/>
      <inertial pos="0 0 -0.5" mass="${p.mass}" diaginertia="1e-4 1e-4 1e-4"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.5" size="0.01" rgba=".5 .5 .5 1" contype="0" conaffinity="0"/>
      <geom type="sphere" pos="0 0 -0.5" size="0.04" rgba=".85 .33 .1 1" contype="0" conaffinity="0"/>
    </body>
  </worldbody>
  <actuator>
    <general name="torque" joint="hinge" gear="${p.gain}" ${dyn} gainprm="1" ctrlrange="-100 100"
             nsample="200" interp="linear" delay="${p.delay}"/>
  </actuator>
</mujoco>`;
}

// complex helpers: [re, im]
const cAdd = (a, b) => [a[0] + b[0], a[1] + b[1]];
const cMul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
const cDiv = (a, b) => { const d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; };
const cExp = (re, im) => [Math.exp(re) * Math.cos(im), Math.exp(re) * Math.sin(im)];
const cAbs = (a) => Math.hypot(a[0], a[1]);

/** The linearized loop at w (rad/s), as loop_response in the script. */
function loopAt(c, p, w) {
  const s = [0, w];
  let deriv = s;
  if (c.encoder) {
    deriv = cMul([1 / H, 0], cAdd([1, 0], cMul([-1, 0], cExp(0, -w * H))));
    if (c.cutoff) {
      const a = 1 - Math.exp(-2 * Math.PI * c.cutoff * H);
      deriv = cMul(deriv, cDiv([a, 0], cAdd([1, 0], cMul([-(1 - a), 0], cExp(0, -w * H)))));
    }
  }
  const ctrl = cAdd([c.kp - MGL, 0], cMul([c.kd, 0], deriv));
  const act = cMul(cDiv([p.gain, 0], [1, w * p.lag]), cExp(0, -w * (p.delay + c.period * H / 2)));
  const inertia = 0.25 * p.mass + 1e-4;
  return cDiv(cMul(act, ctrl), [MGL * p.mass - inertia * w * w, 0]);
}

function predictMargin(c, p) {
  let lo = 0.5, hi = 2000;
  for (let i = 0; i < 200; i++) { const mid = Math.sqrt(lo * hi); if (cAbs(loopAt(c, p, mid)) > 1) lo = mid; else hi = mid; }
  const L = loopAt(c, p, lo);
  let pm = Math.PI + Math.atan2(L[1], L[0]);
  pm = ((pm + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
  return { margin: pm / lo, w: lo };
}

/** A controller with its own sensing state; step(data) writes data.ctrl[0]. */
function makeController(c) {
  let k = 0, qPrev = 0, v = 0, u = 0;
  const alpha = c.cutoff ? 1 - Math.exp(-2 * Math.PI * c.cutoff * H) : 1;
  return (data) => {
    let q = data.qpos[0];
    if (c.encoder) {
      q = Math.round(q * COUNTS / (2 * Math.PI)) * 2 * Math.PI / COUNTS;
      v += alpha * ((q - qPrev) / H - v);
      qPrev = q;
    } else v = data.qvel[0];
    if (k % c.period === 0) u = c.kp * (TARGET - q) - c.kd * v + MGL * Math.sin(q);
    k++;
    data.ctrl[0] = u;
    return u;
  };
}

function std(xs) { const m = xs.reduce((a, b) => a + b, 0) / xs.length; return Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length); }
/** The script's test: diverged, growing spread, or a sustained oscillation above 5 mrad. */
function settles(err) {
  if (err.some((e) => !Number.isFinite(e))) return false;
  const n = err.length, q = [0, 1, 2, 3].map((i) => std(err.slice((i * n) / 4, ((i + 1) * n) / 4)));
  return !(q[3] > 1.1 * q[2] || (q[3] > 0.005 && q[3] > 0.5 * q[1]));
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Delay margin, live", kind: "Lab" });
  const plant = { delay: 0, lag: 0, gain: 1, mass: 1 };
  const ctl = { kp: 80, zeta: 0.7, period: 1, encoder: false, cutoff: 0 };
  const kdOf = () => 2 * ctl.zeta * Math.sqrt(ctl.kp * 0.2501);
  const view = await createSimView(body, { xml: xmlFor(plant), height: config.height || 260, toolbar: false,
    camera: { azimuth: 90, elevation: 0, distance: 1.6, target: [0, 0, 0.7] } });
  const { mj } = view.sim;

  const plotEl = h("div");
  const plot = new Plot(plotEl, { mode: "time", window: 6, xlabel: "time (s)", ylabel: "error (mrad)", height: 150, symmetric: true,
    traces: [{ label: "angle error (mrad)" }] });
  const outs = { pred: readout("predicted delay margin"), meas: readout("measured (bisection)"), live: readout("live loop"), chatter: readout("torque chatter, std (N m)") };
  let controller = null, errs = [], torques = [], diverged = false;

  function predicted() {
    const c = { ...ctl, kd: kdOf() }, p = predictMargin(c, plant);
    outs.pred.set(p.margin > 0 ? `${fmt(1000 * p.margin, 1)} ms at ${fmt(p.w, 1)} rad/s` : "none: unstable as it is");
  }
  function start() {
    view.reset();
    controller = makeController({ ...ctl, kd: kdOf() });
    errs = []; torques = []; diverged = false;
    plot.clear();
    view.sim.controller = (s) => {
      const u = controller(s.data);
      const e = TARGET - s.data.qpos[0];
      errs.push(e); torques.push(u);
      if (Math.abs(e) > 0.5) { diverged = true; view.pause(); }
    };
    outs.meas.set("-");
    predicted();
    view.play();
  }
  async function rebuild() {
    await view.replaceModel(xmlFor(plant), { isXml: true });
    start();
  }
  const tickPlot = () => {
    const s = view.sim;
    if (errs.length) plot.push(s.time, [1000 * errs[errs.length - 1]]);
    if (diverged) outs.live.set("left the linear range (|error| > 0.5 rad)");
    else if (errs.length > 2500) {                       // after 5 s, past the step's transient
      outs.live.set(std(errs.slice(-1000)) > 0.005 ? "oscillating (> 5 mrad)" : "settled");
      outs.chatter.set(std(torques.slice(-1000)).toFixed(3));
    } else { outs.live.set("step in progress"); outs.chatter.set("-"); }
    if (alive) requestAnimationFrame(tickPlot);
  };
  let alive = true;
  requestAnimationFrame(tickPlot);

  async function findMargin() {
    outs.meas.set("searching...");
    await new Promise((r) => setTimeout(r, 30));
    const model = await compileXml(xmlFor(plant));
    const data = new mj.MjData(model);
    const c = { ...ctl, kd: kdOf() };
    const run = (extra) => {
      model.actuator_delay[0] = plant.delay + extra;
      mj.mj_resetData(model, data);
      const step = makeController(c), err = new Float64Array(4000);
      for (let k = 0; k < 4000; k++) {
        step(data);
        mj.mj_step(model, data);
        err[k] = TARGET - data.qpos[0];
        if (Math.abs(err[k]) > 0.5) { err.fill(Infinity, k); break; }
      }
      return Array.from(err);
    };
    let lo = 0, hi = 0.38, result;
    if (!settles(run(0))) result = "none: the loop does not settle without extra delay";
    else {
      while (hi - lo > 2e-4) { const mid = 0.5 * (lo + hi); if (settles(run(mid))) lo = mid; else hi = mid; }
      result = `${fmt(1000 * hi, 1)} ms of extra delay`;
    }
    data.delete(); model.delete();
    outs.meas.set(result);
  }

  const sl = (label, min, max, step, value, unit, digits, onInput) => slider({ label, min, max, step, value, unit, digits, onInput });
  body.append(
    h("div", { class: "toolbar" }, button("Step to 0.05 rad", start, "btn btn--primary"), button("Find the margin", findMargin)),
    h("div", { class: "controls" },
      sl("kp", 5, 300, 1, ctl.kp, "N m/rad", 0, (v) => { ctl.kp = v; predicted(); }),
      sl("damping ratio", 0.2, 1.5, 0.05, ctl.zeta, "", 2, (v) => { ctl.zeta = v; predicted(); }),
      sl("actuator delay", 0, 150, 1, 0, "ms", 0, (v) => { plant.delay = v / 1000; view.sim.model.actuator_delay[0] = plant.delay; predicted(); }),
      sl("motor lag", 0, 40, 1, 0, "ms", 0, (v) => { plant.lag = v / 1000; rebuild(); }),
      sl("torque gain", 0.5, 1.2, 0.05, 1, "", 2, (v) => { plant.gain = v; rebuild(); }),
      sl("mass", 0.8, 1.4, 0.05, 1, "kg", 2, (v) => { plant.mass = v; rebuild(); }),
      select({ label: "controller rate", options: [["500 Hz (every step)", "1"], ["100 Hz", "5"], ["50 Hz", "10"]], value: "1", onChange: (v) => { ctl.period = Number(v); predicted(); } }),
      select({ label: "sensing", options: [["true angle and velocity", "true"], ["encoder, raw velocity", "0"], ["encoder, velocity at 100 Hz", "100"], ["encoder, velocity at 30 Hz", "30"], ["encoder, velocity at 10 Hz", "10"]],
        value: "true", onChange: (v) => { ctl.encoder = v !== "true"; ctl.cutoff = ctl.encoder ? Number(v) : 0; predicted(); } })),
    h("div", { class: "readouts" }, Object.values(outs)), plotEl,
    h("p", { class: "widget__note", html: "Gains and sensing apply at the next <b>Step</b>; the delay applies at once; lag, gain and mass rebuild the model. Both margins are extra delay beyond the delay set: the prediction from the linearized loop of the plant as set, the measurement by bisection on 8 s runs (the extra delay at which the loop stops settling)." }));
  start();

  return { destroy() { alive = false; plot.dispose(); view.destroy(); } };
}
