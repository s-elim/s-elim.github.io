// rl: the cross-entropy method of Lesson 13.1, searching a linear feedback policy for the
// two-link arm while you watch. The search runs on a scratch MjData a few candidates per
// frame; the visible arm plays the current mean policy on a new random target every 2 s.
// Same task, policy, parameter scaling and CEM settings as examples/l13_1_policy_search.py;
// the random numbers differ (a JavaScript generator), so individual runs differ too.
//
// Config: {"title": "...", "height": 280}

import { h, frame, select, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";

const SKIP = 10, STEPS = 100, ELITE = 6, TARGETS_PER = 4;
const SCALE = [100, 100, 100, 100, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10];

function mulberry32(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "A policy search you can watch", kind: "Lab" });
  const view = await createSimView(body, {
    model: "arm2", key: 0, height: config.height || 280,
    camera: config.camera || { azimuth: -90, elevation: 5, distance: 2.4, target: [0.35, 0, 1.0] },
  });
  const sim = view.sim;
  const { mj, model, data } = sim;
  const scratch = new mj.MjData(model);
  const lo = [model.actuator_ctrlrange[0], model.actuator_ctrlrange[2]], hi = [model.actuator_ctrlrange[1], model.actuator_ctrlrange[3]];

  let rand = mulberry32(1);
  const normal = () => Math.sqrt(-2 * Math.log(rand() + 1e-12)) * Math.cos(2 * Math.PI * rand());
  const sampleTarget = (r = rand) => { const rad = 0.35 + 0.5 * r(), a = -0.5 + 2 * r(); return [rad * Math.cos(a), 1 + rad * Math.sin(a)]; };
  const heldOut = (() => { const r = mulberry32(1234); return Array.from({ length: 20 }, () => sampleTarget(r)); })();

  const opt = { size: 10, population: 32 };
  let mean, std, iteration, running = false, evalSuccess = null;

  function policy(theta, d, target) {
    const ee = [d.site_xpos[0], d.site_xpos[2]], e = [target[0] - ee[0], target[1] - ee[1]];
    const p = theta.map((v, i) => v * SCALE[i]);
    const u = [p[0] * e[0] + p[1] * e[1] + p[4] * d.qvel[0] + p[5] * d.qvel[1] + p[8],
               p[2] * e[0] + p[3] * e[1] + p[6] * d.qvel[0] + p[7] * d.qvel[1] + p[9]];
    if (theta.length === 14) {
      const g = [Math.cos(d.qpos[0]), Math.cos(d.qpos[0] + d.qpos[1])];
      u[0] += p[10] * g[0] + p[11] * g[1];
      u[1] += p[12] * g[0] + p[13] * g[1];
    }
    return u.map((v, i) => Math.min(Math.max(v, lo[i]), hi[i]));
  }

  /** One episode on the scratch data: [return, final distance]. */
  function rollout(theta, target) {
    mj.mj_resetDataKeyframe(model, scratch, 0);
    scratch.mocap_pos[0] = target[0]; scratch.mocap_pos[1] = 0; scratch.mocap_pos[2] = target[1];
    mj.mj_forward(model, scratch);
    let ret = 0, dist = 0;
    for (let k = 0; k < STEPS; k++) {
      const u = policy(theta, scratch, target);
      scratch.ctrl[0] = u[0]; scratch.ctrl[1] = u[1];
      for (let s = 0; s < SKIP; s++) mj.mj_step(model, scratch);
      mj.mj_forward(model, scratch);
      dist = Math.hypot(target[0] - scratch.site_xpos[0], target[1] - scratch.site_xpos[2]);
      ret -= dist;
    }
    return [ret, dist];
  }

  const plotEl = h("div");
  const curve = new Plot(plotEl, { mode: "xy", xlabel: "iteration", ylabel: "return", height: 150,
    traces: [{ label: "population mean" }, { label: "elite mean" }] });
  const series = [[], []], xs = [];
  const outs = { it: readout("iteration"), elite: readout("elite mean return"), success: readout("held-out success, 20 targets"), shown: readout("shown episode: final distance (mm)") };

  function resetSearch() {
    rand = mulberry32(1);
    mean = new Array(opt.size).fill(0); std = new Array(opt.size).fill(0.5);
    iteration = 0; evalSuccess = null;
    xs.length = 0; series[0].length = 0; series[1].length = 0;
    curve.setSeries(0, [], []); curve.setSeries(1, [], []); curve.draw();
  }

  // One CEM iteration is spread over frames: `work` holds its population and returns so far.
  let work = null;
  function searchStep() {
    if (!running) return;
    if (!work) {
      const targets = Array.from({ length: TARGETS_PER }, () => sampleTarget());
      const thetas = Array.from({ length: opt.population }, () => mean.map((m, i) => m + std[i] * normal()));
      work = { targets, thetas, returns: [] };
    }
    const t0 = performance.now();
    while (work.returns.length < work.thetas.length && performance.now() - t0 < 12) {
      const th = work.thetas[work.returns.length];
      work.returns.push(work.targets.reduce((s, tg) => s + rollout(th, tg)[0], 0) / work.targets.length);
    }
    if (work.returns.length === work.thetas.length) {
      const order = work.returns.map((r, i) => [r, i]).sort((a, b) => b[0] - a[0]).slice(0, ELITE).map(([, i]) => i);
      const elite = order.map((i) => work.thetas[i]);
      mean = mean.map((_, j) => elite.reduce((s, th) => s + th[j], 0) / ELITE);
      std = mean.map((m, j) => Math.sqrt(elite.reduce((s, th) => s + (th[j] - m) ** 2, 0) / ELITE) + 0.01);
      iteration += 1;
      xs.push(iteration);
      series[0].push(work.returns.reduce((s, r) => s + r, 0) / work.returns.length);
      series[1].push(order.reduce((s, i) => s + work.returns[i], 0) / ELITE);
      curve.setSeries(0, xs, series[0]); curve.setSeries(1, xs, series[1]); curve.draw();
      if (iteration % 5 === 0) evalSuccess = heldOut.filter((tg) => rollout(mean, tg)[1] < 0.02).length;
      work = null;
    }
  }

  // The visible arm plays the current mean policy, a new target every 2 s.
  let shown = { target: [0.6, 1.3], start: 0 };
  function newEpisode() {
    shown = { target: sampleTarget(Math.random), start: data.time };
    mj.mj_resetDataKeyframe(model, data, 0);
    data.mocap_pos[0] = shown.target[0]; data.mocap_pos[2] = shown.target[1];
    shown.start = data.time;
    mj.mj_forward(model, data);
  }
  let hold = [0, 0], count = 0;
  sim.controller = (s) => {
    if (count++ % SKIP === 0) { mj.mj_forward(model, s.data); hold = policy(mean, s.data, shown.target); }
    s.data.ctrl[0] = hold[0]; s.data.ctrl[1] = hold[1];
    if (s.data.time - shown.start > STEPS * SKIP * model.opt.timestep) {
      outs.shown.set(fmt(1000 * Math.hypot(shown.target[0] - s.data.site_xpos[0], shown.target[1] - s.data.site_xpos[2]), 1));
      newEpisode(); count = 0;
    }
  };

  let alive = true;
  const tick = () => {
    if (!alive) return;
    searchStep();
    outs.it.set(String(iteration));
    outs.elite.set(series[1].length ? fmt(series[1][series[1].length - 1], 2) : "-");
    outs.success.set(evalSuccess == null ? "after 5 iterations" : `${evalSuccess} / 20`);
    requestAnimationFrame(tick);
  };

  const startBtn = button("Start search", () => { running = !running; startBtn.textContent = running ? "Pause search" : "Start search"; if (running) view.play(); }, "btn btn--primary");
  body.append(h("div", { class: "toolbar" }, startBtn, button("Reset search", () => { resetSearch(); work = null; }), button("New target", newEpisode)),
    h("div", { class: "controls" },
      select({ label: "policy observes", options: [["e and qdot (10 parameters)", "10"], ["also cos q1, cos(q1 + q2) (14)", "14"]], value: "10", onChange: (v) => { opt.size = Number(v); resetSearch(); work = null; } }),
      select({ label: "population", options: [["16", "16"], ["32", "32"], ["64", "64"]], value: "32", onChange: (v) => { opt.population = Number(v); work = null; } })),
    h("div", { class: "readouts" }, Object.values(outs)), plotEl,
    h("p", { class: "widget__note", html: "Each iteration samples a population of parameter vectors around the current mean, scores each on 4 random targets (2 s each), and refits the mean and spread to the best 6. The curve is noisy because every iteration draws new targets. The arm shows the current mean policy." }));
  resetSearch();
  newEpisode();
  requestAnimationFrame(tick);

  return { destroy() { alive = false; scratch.delete(); curve.dispose(); view.destroy(); } };
}
