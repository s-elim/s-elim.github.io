// integrators: the same model, the same initial state, five integrators side by
// side. Plots the relative energy error of each, and the measured cost per step.
//
// Config: {"model": "double_pendulum", "key": 0, "timestep": 0.002,
//          "integrators": ["Euler", "RK4", "implicit", "implicitfast", "discrete"],
//          "models": [["double_pendulum", "Double pendulum"], ["pendulum", "Pendulum"]]}
//
// Each integrator gets its own compiled MjModel, because the integrator is a
// model option (mjModel.opt.integrator), not a property of mjData.

import { h, frame, slider, select, button, fmt } from "./ui.js";
import { Plot, PALETTE } from "../plot.js";
import { loadModel, getMujoco } from "../runtime.js";
import { Sim } from "../sim.js";
import { register } from "../loop.js";

const CODES = { Euler: 0, RK4: 1, implicit: 2, implicitfast: 3, discrete: 4 };

export async function mount(el, config) {
  const { body } = frame(el, { title: config.title || "Five integrators, one initial state", kind: "Lab" });
  const mj = await getMujoco();
  const names = config.integrators || Object.keys(CODES);
  let modelName = config.model || "double_pendulum";
  let timestep = config.timestep || 0.002;
  let sims = [];
  let running = false;
  let e0 = [];
  let wall = names.map(() => 0), steps = 0;

  const plot = new Plot(body, {
    mode: "time", window: config.window || 20, height: 210, ylabel: "energy error (% of initial)",
    traces: names.map((n) => ({ label: n })), refLines: [{ y: 0 }],
  });
  const cost = h("div", { class: "readouts" });
  const costEls = names.map((n, i) => {
    const r = h("div", { class: "readout" }, h("span", { style: { color: PALETTE[i] } }, n), h("b", {}, "-"));
    cost.appendChild(r);
    return r.querySelector("b");
  });

  const build = async () => {
    sims.forEach((s) => s.dispose());
    sims = [];
    for (const n of names) {
      const m = await loadModel(modelName);
      m.opt.integrator = CODES[n];
      m.opt.timestep = timestep;
      const s = new Sim(mj, m);
      if (config.key != null && m.nkey > config.key) { s.keyframe = config.key; s.reset(config.key); }
      sims.push(s);
    }
    e0 = sims.map((s) => s.energy().total);
    wall = names.map(() => 0); steps = 0;
    plot.clear();
    plot.draw();
    time.textContent = "t = 0.000 s";
  };

  const time = h("span", { class: "chip" }, "t = 0.000 s");
  const runBtn = button("Run", () => { running = !running; runBtn.textContent = running ? "Pause" : "Run"; }, "btn btn--primary");
  const resetBtn = button("Reset", async () => { running = false; runBtn.textContent = "Run"; await build(); });
  const models = config.models || [["double_pendulum", "Double pendulum (chaotic, no damping)"], ["pendulum", "Pendulum (no damping)"]];
  const modelSel = select({ label: "model", options: models, value: modelName, onChange: async (v) => { modelName = v; running = false; runBtn.textContent = "Run"; await build(); } });
  const hSlider = slider({ label: "timestep h", unit: "s", min: 0.0005, max: 0.02, step: 0.0005, value: timestep, digits: 4,
    onInput: async (v) => { timestep = v; running = false; runBtn.textContent = "Run"; await build(); } });
  body.prepend(h("div", { class: "toolbar" }, runBtn, resetBtn, time), h("div", { class: "controls" }, modelSel, hSlider));
  body.appendChild(h("p", { class: "widget__note" }, "Cost per step, measured in this browser (microseconds):"));
  body.appendChild(cost);
  body.appendChild(h("p", { class: "widget__note", html: config.note || "Each curve is a separate MuJoCo model differing only in <code>opt.integrator</code>. The run advances 0.1 s of simulated time per frame and stops at 20 s." }));
  await build();

  const unregister = register(body, () => {
    if (!running || !sims.length) return;
    const n = Math.max(1, Math.round(0.1 / timestep));
    sims.forEach((s, i) => {
      const t0 = performance.now();
      s.step(n);
      wall[i] += performance.now() - t0;
    });
    steps += n;
    const t = sims[0].time;
    plot.push(t, sims.map((s, i) => 100 * (s.energy().total - e0[i]) / Math.abs(e0[i] || 1)));
    plot.draw();
    costEls.forEach((b, i) => { b.textContent = fmt(1000 * wall[i] / steps, 1); });
    time.textContent = `t = ${t.toFixed(3)} s`;
    if (t >= (config.duration || 20)) { running = false; runBtn.textContent = "Run"; }
  }, { toggle: () => runBtn.click(), reset: () => resetBtn.click() });

  return { destroy() { unregister(); plot.dispose(); sims.forEach((s) => s.dispose()); } };
}
