// dynamics: torque from motion. Plans a 2 s minimum-jerk motion for arm7, computes
// the joint torques with mj_inverse, then replays them open loop with mj_step and
// plots how far the arm drifts from the plan.
//
// The two choices are the ones Lesson 7.2 measures: accelerations taken from the
// continuous-time trajectory or from finite differences that semi-implicit Euler
// needs to land on the planned samples, and the discrete-time inverse flag.
//
// Config: {"title": "...", "height": 280}

import { h, frame, select, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";

const DURATION = 2.0;
const DELTA = [0.6, -0.3, 0.4, -0.5, 0.5, 0.4, 0.8];          // rad, as in the lesson's script

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Torque from motion, replayed open loop", kind: "Lab" });
  const view = await createSimView(body, {
    model: "reach", key: 1, height: config.height || 280, toolbar: false,
    camera: config.camera || { azimuth: -55, elevation: 20, distance: 2.1, target: [0.25, 0, 0.5] },
  });
  const sim = view.sim;
  const { mj, model, data } = sim;
  const nv = model.nv, hstep = model.opt.timestep, n = Math.round(DURATION / hstep);
  const q0 = Array.from(data.qpos);
  const flag = mj.mjtEnableBit.mjENBL_INVDISCRETE.value;
  const at = (t) => {
    const s = Math.min(Math.max(t / DURATION, 0), 1);
    const p = 10 * s ** 3 - 15 * s ** 4 + 6 * s ** 5;
    const dp = (30 * s ** 2 - 60 * s ** 3 + 30 * s ** 4) / DURATION;
    const ddp = (60 * s - 180 * s ** 2 + 120 * s ** 3) / DURATION ** 2;
    return [q0.map((v, j) => v + DELTA[j] * p), DELTA.map((d) => d * dp), DELTA.map((d) => d * ddp)];
  };
  const samples = Array.from({ length: n + 2 }, (_, k) => at(k * hstep)[0]);
  const opt = { accel: "analytic", invdiscrete: false };
  let tau = null, worst = 0, playing = false, alive = true;

  function computeTorques() {
    const d2 = new mj.MjData(model);
    if (opt.invdiscrete) model.opt.enableflags |= flag; else model.opt.enableflags &= ~flag;
    const out = [];
    for (let k = 0; k < n; k++) {
      let q, v, a;
      if (opt.accel === "analytic") [q, v, a] = at(k * hstep);
      else {
        q = samples[k];
        v = k ? q.map((x, j) => (x - samples[k - 1][j]) / hstep) : new Array(nv).fill(0);
        a = q.map((x, j) => ((samples[k + 1][j] - x) / hstep - v[j]) / hstep);
      }
      for (let j = 0; j < nv; j++) { d2.qpos[j] = q[j]; d2.qvel[j] = v[j]; d2.qacc[j] = a[j]; }
      mj.mj_inverse(model, d2);
      out.push(Array.from(d2.qfrc_inverse));
    }
    model.opt.enableflags &= ~flag;          // the replay itself is ordinary forward simulation
    d2.delete();
    return out;
  }

  const plotHolder = h("div");
  const plot = new Plot(plotHolder, { mode: "time", window: DURATION, xlabel: "time (s)", ylabel: "log10 error (rad)",
    height: 150, traces: [{ label: "largest joint error, log10 rad" }] });
  const outs = { t: readout("time (s)"), err: readout("joint error now (rad)"), worst: readout("largest so far (rad)") };

  sim.controller = (s) => {
    const k = Math.round(s.data.time / hstep);
    if (!tau || k >= n) return;
    for (let j = 0; j < nv; j++) s.data.ctrl[j] = tau[k][j];
  };
  sim.on((s, event) => { if (event === "reset") { playing = false; } });
  const tick = () => {
    if (playing) {
      const k = Math.round(data.time / hstep);
      if (k >= 1 && k <= n) {
        const err = Math.max(...Array.from(data.qpos).map((v, j) => Math.abs(v - samples[k][j])));
        worst = Math.max(worst, err);
        plot.push(data.time, [Math.log10(Math.max(err, 1e-17))]);
        plot.draw();
        outs.t.set(fmt(data.time, 3)); outs.err.set(fmt(err, 3)); outs.worst.set(fmt(worst, 3));
      }
      if (k >= n) { sim.pause(); playing = false; }
    }
    if (alive) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  const run = () => {
    tau = computeTorques();
    sim.reset();                              // back to home, time 0
    worst = 0; plot.clear();
    playing = true;
    sim.play();
  };
  const controls = h("div", { class: "controls" },
    select({ label: "accelerations given to mj_inverse", options: [["analytic, from the trajectory", "analytic"], ["consistent with the Euler step", "consistent"]],
      value: opt.accel, onChange: (v) => { opt.accel = v; } }),
    select({ label: "discrete-time inverse (invdiscrete)", options: [["off", "off"], ["on", "on"]], value: "off",
      onChange: (v) => { opt.invdiscrete = v === "on"; } }));
  body.append(h("div", { class: "toolbar" }, button("Compute torques and replay", run, "btn btn--primary")),
    controls, h("div", { class: "readouts" }, Object.values(outs)), plotHolder,
    h("p", { class: "widget__note", html: "The torques are computed once, before the replay, from the planned motion alone. During the replay nothing corrects the arm: the error you see is everything the open-loop torques get wrong." }));

  return { destroy() { alive = false; playing = false; tau = null; plot.dispose(); view.destroy(); } };
}
