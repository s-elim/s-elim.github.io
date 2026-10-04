// dr: domain randomization for an open-loop strike (Lesson 17.1). A puck (the one of push.xml:
// cylinder r 3.5 cm, 0.2 kg, elliptic cones, impratio 10, 2 ms) is launched toward a goal D away at
// v = sqrt(2 mu_hat g D) and slides. The strategies differ in mu_hat: tuned on the nominal friction
// 0.5, tuned on a randomized range you choose (the best single value over that range, found by grid
// search), or measured by a probe launch at 0.3 m/s before the strike. "Sweep" plots success over
// 20 tasks against the true friction.
//
// Config: {"title": "...", "height": 220}

import { h, frame, select, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";

const XML = `
<mujoco model="strike">
  <option timestep="0.002" integrator="implicitfast" cone="elliptic" impratio="10"/>
  <visual><headlight diffuse=".6 .6 .6"/></visual>
  <worldbody>
    <light pos="0.2 -0.4 1.2" dir="0 0.3 -1"/>
    <geom name="floor" type="plane" size="0.6 0.3 0.05" pos="0.2 0 0" rgba=".86 .88 .86 1" friction="0.5 0.005 0.0001"/>
    <site name="goal" pos="0.2 0 0.001" type="cylinder" size="0.03 0.001" rgba=".1 .7 .3 .5"/>
    <body name="puck" pos="0 0 0.02">
      <freejoint name="puck"/>
      <geom name="puck" type="cylinder" size="0.035 0.02" mass="0.2" rgba=".85 .33 .1 1" friction="0.5 0.005 0.0001"/>
    </body>
  </worldbody>
</mujoco>`;
const G = 9.81, MU_GRID = [0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5], PROBE = 0.3;

function mulberry32(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Randomize, or measure?", kind: "Lab" });
  const view = await createSimView(body, { xml: XML, height: config.height || 220, toolbar: false,
    camera: { azimuth: -90, elevation: 35, distance: 0.7, target: [0.15, 0, 0] } });
  const sim = view.sim;
  const { mj, model } = sim;
  const scratch = new mj.MjData(model);
  const floorId = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM.value, "floor"), puckId = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM.value, "puck");
  const goalSite = mj.mj_name2id(model, mj.mjtObj.mjOBJ_SITE.value, "goal");
  const opt = { strategy: "nominal", lo: 0.25, hi: 1.0, mu: 0.5 };
  let tunedRange = null;

  function setFriction(mu) { model.geom_friction[3 * floorId] = mu; model.geom_friction[3 * puckId] = mu; }
  /** Launch the puck from where it is along +x at `speed` and let it slide for up to `seconds` (stopping
   *  early once every degree of freedom is at rest: a stopped puck can still be rocking); returns its x. */
  function slide(d, speed, seconds) {
    d.qvel[0] = speed;
    for (let k = 0; k < Math.round(seconds / model.opt.timestep); k++) {
      mj.mj_step(model, d);
      let still = k > 10;
      for (let i = 0; still && i < 6; i++) still = Math.abs(d.qvel[i]) < 1e-6;
      if (still) break;
    }
    return d.qpos[0];
  }
  function reset(d) { mj.mj_resetData(model, d); mj.mj_forward(model, d); }
  /** Final distance to the goal for one task (goal distance D, true friction mu) under a strategy. */
  function trial(D, mu, strategy, d = scratch) {
    setFriction(mu);
    reset(d);
    let muHat;
    if (strategy === "probe") {
      const slid = slide(d, PROBE, 1.0);
      muHat = PROBE * PROBE / (2 * G * Math.max(slid, 1e-4));
    } else muHat = strategy === "nominal" ? 0.45 : tunedRange.muHat;
    const remaining = D - d.qpos[0];
    if (remaining > 0) slide(d, Math.sqrt(2 * muHat * G * remaining), 3.0);
    return Math.abs(d.qpos[0] - D);
  }
  const tasks = (seed, n) => { const r = mulberry32(seed); return Array.from({ length: n }, () => 0.1 + 0.15 * r()); };

  function tuneRange() {
    const r = mulberry32(17), train = tasks(17, 40).map((D) => [D, opt.lo + (opt.hi - opt.lo) * r()]);
    let best = { muHat: 0.05, score: -1 };
    for (let m = 0.05; m <= 1.5001; m += 0.05) {
      tunedRange = { muHat: m };
      const score = train.filter(([D, mu]) => trial(D, mu, "range") < 0.03).length / train.length;
      if (score > best.score) best = { muHat: Math.round(m * 100) / 100, score };
    }
    tunedRange = { muHat: best.muHat, lo: opt.lo, hi: opt.hi, score: best.score };
  }
  const strategyLabel = () => (opt.strategy === "nominal" ? "mu_hat 0.45 (tuned at 0.5)"
    : opt.strategy === "range" ? `mu_hat ${tunedRange.muHat} (best over ${opt.lo} to ${opt.hi})` : `probe at ${PROBE} m/s, then strike`);

  const plotEl = h("div");
  const plot = new Plot(plotEl, { mode: "xy", xlabel: "true friction", ylabel: "success over 20 tasks", height: 160, ymin: 0, ymax: 1,
    traces: [{ label: "tuned at 0.5" }, { label: "tuned on the range" }, { label: "probe, then strike" }] });
  const outs = { strategy: readout("strategy"), last: readout("last strike: distance to goal (mm)"), sweep: readout("last sweep") };

  function ensureTuned() { if (opt.strategy === "range" && (!tunedRange || tunedRange.lo !== opt.lo || tunedRange.hi !== opt.hi)) tuneRange(); }
  function sweep() {
    ensureTuned();
    const ts = tasks(1718, 20);
    const ys = MU_GRID.map((mu) => ts.filter((D) => trial(D, mu, opt.strategy) < 0.03).length / ts.length);
    plot.setSeries({ nominal: 0, range: 1, probe: 2 }[opt.strategy], MU_GRID, ys); plot.draw();
    outs.strategy.set(strategyLabel());
    outs.sweep.set(MU_GRID.map((m, i) => `${m}: ${fmt(ys[i], 2)}`).join("  "));
  }
  function strikeOnce() {
    ensureTuned();
    const D = 0.2;
    model.site_pos[3 * goalSite] = D;
    const err = trial(D, opt.mu, opt.strategy);
    outs.last.set(fmt(1000 * err, 1));
    outs.strategy.set(strategyLabel());
    // replay it visibly: the same physics on the displayed data
    setFriction(opt.mu);
    reset(sim.data);
    let phase = opt.strategy === "probe" ? "probe" : "strike", t0 = 0, muHat = opt.strategy === "nominal" ? 0.45 : opt.strategy === "range" ? tunedRange.muHat : null;
    sim.data.qvel[0] = phase === "probe" ? PROBE : Math.sqrt(2 * muHat * G * D);
    sim.controller = (s) => {
      if (phase === "probe" && s.data.time > 1.0) {
        muHat = PROBE * PROBE / (2 * G * Math.max(s.data.qpos[0], 1e-4));
        s.data.qvel[0] = Math.sqrt(2 * muHat * G * Math.max(D - s.data.qpos[0], 0));
        phase = "strike"; t0 = s.data.time;
      }
      if (phase === "strike" && s.data.time - t0 > 3.0) { phase = "done"; view.pause(); }
    };
    view.play();
  }

  body.append(
    h("div", { class: "toolbar" }, button("Strike once (D = 20 cm)", strikeOnce, "btn btn--primary"), button("Sweep the true friction", sweep)),
    h("div", { class: "controls" },
      select({ label: "strategy", options: [["tuned at nominal friction 0.5", "nominal"], ["tuned on a randomized range", "range"], ["probe, then strike", "probe"]], value: "nominal", onChange: (v) => { opt.strategy = v; } }),
      select({ label: "randomized range", options: [["0.25 to 1.0", "0.25,1.0"], ["0.4 to 0.6", "0.4,0.6"], ["0.05 to 1.5", "0.05,1.5"]], value: "0.25,1.0", onChange: (v) => { [opt.lo, opt.hi] = v.split(",").map(Number); } }),
      select({ label: "true friction (strike once)", options: MU_GRID.map((m) => [String(m), String(m)]), value: "0.5", onChange: (v) => { opt.mu = Number(v); } })),
    h("div", { class: "readouts" }, Object.values(outs)), plotEl,
    h("p", { class: "widget__note", html: "Success means the puck stops within 3 cm of the goal. Sweeping each strategy adds its curve to the plot; tasks are the same 20 goal distances (10 to 25 cm) for every strategy and friction." }));
  outs.strategy.set(strategyLabel());

  return { destroy() { scratch.delete(); plot.dispose(); view.destroy(); } };
}
