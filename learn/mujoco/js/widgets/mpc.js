// mpc: predictive sampling on the cart-pole, planning live in the page (Showcase, Lesson 21.4). The planner
// of examples/showcase_predictive_sampling.py: every 40 ms a 4-knot control spline over the horizon is
// perturbed at three noise scales (0.5, 2, 8 N), each candidate and the unperturbed one are simulated on a
// copy of the model at a 10 ms timestep, and the cheapest is applied. Faint lines are the pole tip's path in
// every candidate; the orange line is the plan being executed. The real pole's mass can differ from the
// 0.2 kg the planner assumes.
//
// Config: {"title": "...", "height": 300}

import * as THREE from "three";
import { h, frame, slider, select, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";
import { loadModel, idOf } from "../runtime.js";

const SCALES = [0.5, 2, 8], KNOTS = 4, REPLAN = 0.04, PLAN_DT = 0.01, LIMIT = 20;

function mulberry32(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Piecewise-linear spline through `knots` at equally spaced times over [0, horizon], held outside. */
function spline(knots, horizon, t) {
  const n = knots.length, x = Math.min(Math.max(t / horizon, 0), 1) * (n - 1), i = Math.min(Math.floor(x), n - 2), f = x - i;
  return knots[i] * (1 - f) + knots[i + 1] * f;
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "A planner in the page", kind: "Lab" });
  const view = await createSimView(body, { model: "cartpole", key: 1, height: config.height || 300, toolbar: false,
    camera: { azimuth: 90, elevation: 8, distance: 3.2, target: [0, 0, 0.6] } });
  const sim = view.sim, { mj, model, data } = sim;
  const plan = await loadModel("cartpole");
  plan.opt.timestep = PLAN_DT;
  const pd = new mj.MjData(plan);
  const tipPlan = idOf(mj, plan, "mjOBJ_SITE", "pole_tip"), pole = idOf(mj, model, "mjOBJ_BODY", "pole");
  const pole0 = { mass: model.body_mass[pole], inertia: Array.from(model.body_inertia.slice(3 * pole, 3 * pole + 3)), ipos: model.body_ipos[3 * pole + 2] };
  const opt = { samples: 64, horizon: 1.0, show: true, poleMass: 0.2 };
  let rand = mulberry32(1), nominal = new Float64Array(KNOTS), tNominal = 0, nextReplan = 0, lastMs = 0, lastCost = 0, msAvg = 0;
  const gauss = () => Math.sqrt(-2 * Math.log(rand() + 1e-12)) * Math.cos(2 * Math.PI * rand());

  // rollout lines
  const ghostGeo = new THREE.BufferGeometry(), bestGeo = new THREE.BufferGeometry();
  const ghosts = new THREE.LineSegments(ghostGeo, new THREE.LineBasicMaterial({ color: 0x7a7a7a, transparent: true, opacity: 0.35 }));
  const best = new THREE.Line(bestGeo, new THREE.LineBasicMaterial({ color: 0xd55e00 }));
  ghosts.frustumCulled = best.frustumCulled = false;
  view.viewer.overlayGroup.add(ghosts, best);

  function setPoleMass(mass) {
    const r = mass / pole0.mass;
    model.body_mass[pole] = mass;
    for (let i = 0; i < 3; i++) model.body_inertia[3 * pole + i] = pole0.inertia[i] * r;
    mj.mj_setConst(model, data);                       // derived constants after a mass change (Lesson 17.1)
  }

  function replan() {
    const t0 = performance.now();
    const H = opt.horizon, steps = Math.round(H / PLAN_DT), shift = data.time - tNominal;
    const base = Array.from({ length: KNOTS }, (_, k) => spline(nominal, H, (k * H) / (KNOTS - 1) + shift));
    const segs = [];
    let bestCost = Infinity, bestKnots = base, bestPath = null;
    for (let i = 0; i < opt.samples; i++) {
      const knots = i === 0 ? base : base.map((v) => Math.min(Math.max(v + SCALES[(i - 1) % 3] * gauss(), -LIMIT), LIMIT));
      pd.qpos.set(data.qpos); pd.qvel.set(data.qvel); pd.time = 0;
      let c = 0;
      const path = [];
      for (let k = 0; k < steps; k++) {
        const u = spline(knots, H, k * PLAN_DT);
        pd.ctrl[0] = u;
        mj.mj_step(plan, pd);
        const x = pd.qpos[0], th = pd.qpos[1], xd = pd.qvel[0], thd = pd.qvel[1];
        c += (1 - Math.cos(th)) + 0.1 * x * x + 0.01 * xd * xd + 0.001 * thd * thd + 1e-4 * u * u;
        if (opt.show && k % 4 === 0) path.push(pd.site_xpos[3 * tipPlan], pd.site_xpos[3 * tipPlan + 1], pd.site_xpos[3 * tipPlan + 2]);
      }
      if (opt.show) for (let j = 3; j < path.length; j += 3) segs.push(path[j - 3], path[j - 2], path[j - 1], path[j], path[j + 1], path[j + 2]);
      if (c < bestCost) { bestCost = c; bestKnots = knots; bestPath = path; }
    }
    nominal = Float64Array.from(bestKnots); tNominal = data.time; lastCost = bestCost;
    ghostGeo.setAttribute("position", new THREE.Float32BufferAttribute(opt.show ? segs : [], 3));
    bestGeo.setAttribute("position", new THREE.Float32BufferAttribute(opt.show && bestPath ? bestPath : [], 3));
    lastMs = performance.now() - t0;
    msAvg = msAvg ? 0.9 * msAvg + 0.1 * lastMs : lastMs;
  }

  sim.controller = (s) => {
    if (s.data.time >= nextReplan) { replan(); nextReplan = s.data.time + REPLAN - 1e-9; }
    s.data.ctrl[0] = spline(nominal, opt.horizon, s.data.time - tNominal);
  };

  const plotEl = h("div");
  const plot = new Plot(plotEl, { mode: "time", window: 8, xlabel: "time (s)", ylabel: "pole angle (deg)", height: 140, ymin: -180, ymax: 180,
    traces: [{ label: "pole angle from upright (deg)" }] });
  const outs = { angle: readout("pole angle from upright"), cart: readout("cart position (m)"), plan: readout("planning time per replan"), cost: readout("best plan cost") };
  let alive = true;
  const tick = () => {
    if (!alive) return;
    const th = ((data.qpos[1] + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
    if (!sim.paused) { plot.push(data.time, [th * 180 / Math.PI]); plot.draw(); }
    outs.angle.set(`${fmt(th * 180 / Math.PI, 1)} deg`);
    outs.cart.set(fmt(data.qpos[0], 3));
    outs.plan.set(`${fmt(msAvg, 1)} ms (${Math.round(opt.samples * opt.horizon / PLAN_DT)} steps)`);
    outs.cost.set(fmt(lastCost, 2));
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  function restart() {
    view.reset();                                   // to the hanging keyframe
    data.qpos[1] += 0.05 * gauss();
    mj.mj_forward(model, data);
    nominal = new Float64Array(KNOTS); tNominal = 0; nextReplan = 0; plot.clear();
    view.play();
  }

  body.append(
    h("div", { class: "toolbar" }, button("Start from hanging", restart, "btn btn--primary"),
      button("Shove the pole", () => { data.qvel[1] += 3.0; }), button("Pause / play", () => view.toggle())),
    h("div", { class: "controls" },
      slider({ label: "samples per replan", min: 4, max: 128, step: 4, value: opt.samples, digits: 0, onInput: (v) => { opt.samples = v; } }),
      slider({ label: "horizon", min: 0.25, max: 2, step: 0.25, value: opt.horizon, unit: "s", digits: 2, onInput: (v) => { opt.horizon = v; } }),
      slider({ label: "real pole mass (planner assumes 0.2)", min: 0.1, max: 1.0, step: 0.05, value: 0.2, unit: "kg", digits: 2, onInput: (v) => { opt.poleMass = v; setPoleMass(v); } }),
      select({ label: "draw candidate rollouts", options: [["yes", "yes"], ["no", "no"]], value: "yes", onChange: (v) => { opt.show = v === "yes"; } })),
    h("div", { class: "readouts" }, Object.values(outs)), plotEl,
    h("p", { class: "widget__note", html: "The planner simulates every candidate in this page each 40 ms of simulated time; if that takes longer than 40 ms of wall time, the simulation slows down rather than skipping plans. Measured in Python over 20 starts: 128 samples balance the pole from all 20, 64 from 18, 4 from none (table below)." }));
  restart();

  return { destroy() { alive = false; view.viewer.overlayGroup.remove(ghosts, best); ghostGeo.dispose(); bestGeo.dispose(); pd.delete(); plan.delete?.(); plot.dispose(); view.destroy(); } };
}
