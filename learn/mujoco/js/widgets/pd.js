// pd: four joint-space controllers tracking the same trajectory on arm7, with a
// controller model whose link masses and inertias can be scaled. Mirrors
// examples/l8_2_model_based.py: q*(t) = home + A sin(2 pi f t), 4 s, feedback
// bandwidth 20 rad/s, damping ratio 1, errors measured after the first second.
//
// The controller model is exact for scale 1. A uniform scale s of every link's
// mass and inertia scales M - diag(armature) and the bias forces by s, so
//   M_ctrl = A + s (M - A),   c_ctrl = s c,
// with A the (unscaled) armature: what the script gets by editing the model.
//
// Config: {"title": "...", "height": 280}

import { h, frame, select, slider, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";

const WN = 20, ZETA = 1, FREQ = 0.5, DURATION = 4, SKIP = 1;
const AMP = [0.3, 0.2, 0.3, 0.3, 0.4, 0.3, 0.5];

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Four controllers, one trajectory", kind: "Lab" });
  const view = await createSimView(body, {
    model: "reach", key: 1, height: config.height || 280, toolbar: false,
    camera: config.camera || { azimuth: -55, elevation: 20, distance: 2.1, target: [0.25, 0, 0.5] },
  });
  const sim = view.sim;
  const { mj, model, data } = sim;
  const nv = model.nv, hstep = model.opt.timestep;
  const scratch = new mj.MjData(model);
  const mbuf = new mj.DoubleBuffer(nv * nv);
  const home = Array.from(data.qpos);
  const arm = Array.from(model.dof_armature), damp = Array.from(model.dof_damping);
  const w = 2 * Math.PI * FREQ;
  const plan = (t) => [home.map((v, j) => v + AMP[j] * Math.sin(w * t)), AMP.map((a) => a * w * Math.cos(w * t)), AMP.map((a) => -a * w * w * Math.sin(w * t))];

  function massAndBias(q, qd) {               // M and c of the true model at (q, qd), from the scratch data
    for (let j = 0; j < nv; j++) { scratch.qpos[j] = q[j]; scratch.qvel[j] = qd[j]; }
    mj.mj_forward(model, scratch);
    mj.mj_fullM(model, scratch, mbuf);
    const v = Array.from(mbuf.GetView());
    return [Array.from({ length: nv }, (_, i) => v.slice(i * nv, i * nv + nv)), Array.from(scratch.qfrc_bias)];
  }
  const mHome = massAndBias(home, new Array(nv).fill(0))[0].map((r, i) => r[i]);
  const kp = mHome.map((m) => m * WN * WN), kd = mHome.map((m) => 2 * ZETA * m * WN);
  const opt = { kind: "PD", scale: 1 };
  const stats = { sum: 0, n: 0, peak: 0, sat: 0, running: false };

  sim.controller = (s) => {
    if (!stats.running) return;
    const t = s.data.time;
    const q = Array.from(s.data.qpos), qd = Array.from(s.data.qvel);
    const [qs, qds, qdds] = plan(t);
    const e = qs.map((v, j) => v - q[j]), ed = qds.map((v, j) => v - qd[j]);
    if (t >= SKIP + hstep / 2) {
      for (const x of e) { stats.sum += x * x; stats.peak = Math.max(stats.peak, Math.abs(x)); }
      stats.n += nv;
    }
    if (t >= DURATION - hstep / 2) { stats.running = false; s.pause(); return; }
    let tau;
    const sc = opt.scale;
    const ctrlModel = (M, c) => [M.map((r, i) => r.map((v, k) => (i === k ? arm[i] + sc * (v - arm[i]) : sc * v))), c.map((v) => sc * v)];
    if (opt.kind === "PD") tau = e.map((x, j) => kp[j] * x + kd[j] * ed[j]);
    else if (opt.kind === "gravity") {
      const [, c] = ctrlModel(...massAndBias(q, qd));
      tau = e.map((x, j) => kp[j] * x + kd[j] * ed[j] + c[j]);
    } else if (opt.kind === "feedforward") {
      const [M, c] = ctrlModel(...massAndBias(qs, qds));
      tau = e.map((x, j) => kp[j] * x + kd[j] * ed[j] + M[j].reduce((acc, m, k) => acc + m * qdds[k], 0) + c[j] + damp[j] * qds[j]);
    } else {
      const [M, c] = ctrlModel(...massAndBias(q, qd));
      const v = qdds.map((a, j) => a + WN * WN * e[j] + 2 * ZETA * WN * ed[j]);
      tau = M.map((r, j) => r.reduce((acc, m, k) => acc + m * v[k], 0) + c[j] + damp[j] * qd[j]);
    }
    for (let j = 0; j < nv; j++) {
      const lim = model.actuator_ctrlrange[2 * j + 1];
      if (Math.abs(tau[j]) > lim) stats.sat += 1;
      s.data.ctrl[j] = tau[j];
    }
  };

  const plotHolder = h("div");
  const plot = new Plot(plotHolder, { mode: "time", window: DURATION, xlabel: "time (s)", ylabel: "largest joint error (mrad)",
    height: 150, traces: [{ label: "largest joint error (mrad)" }] });
  const outs = { t: readout("time (s)"), rms: readout("RMS error after 1 s (mrad)"), peak: readout("peak error after 1 s (mrad)"), sat: readout("steps with saturation") };
  let alive = true;
  const tick = () => {
    if (!alive) return;
    if (stats.running || data.time > 0) {
      const [qs] = plan(data.time);
      const err = Math.max(...Array.from(data.qpos).map((v, j) => Math.abs(v - qs[j])));
      if (stats.running) { plot.push(data.time, [1000 * err]); plot.draw(); }
      outs.t.set(fmt(data.time, 3));
      outs.rms.set(stats.n ? fmt(1000 * Math.sqrt(stats.sum / stats.n), 2) : "-");
      outs.peak.set(stats.n ? fmt(1000 * stats.peak, 2) : "-");
      outs.sat.set(String(stats.sat));
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  const run = () => {
    sim.reset();
    const [, qd0] = plan(0);
    for (let j = 0; j < nv; j++) data.qvel[j] = qd0[j];
    mj.mj_forward(model, data);
    Object.assign(stats, { sum: 0, n: 0, peak: 0, sat: 0, running: true });
    plot.clear();
    sim.play();
  };
  body.append(h("div", { class: "toolbar" }, button("Run 4 s", run, "btn btn--primary")),
    h("div", { class: "controls" },
      select({ label: "controller", options: [["PD", "PD"], ["PD + gravity compensation", "gravity"], ["PD + inverse-dynamics feedforward", "feedforward"], ["computed torque", "computed"]],
        value: "PD", onChange: (v) => { opt.kind = v; } }),
      slider({ label: "controller model: link masses × s", min: 0.5, max: 1.5, step: 0.05, value: 1, digits: 2, onInput: (v) => { opt.scale = v; } })),
    h("div", { class: "readouts" }, Object.values(outs)), plotHolder,
    h("p", { class: "widget__note", html: "Choose a controller and a model scale, then run. The arm itself never changes; only the controller's model does. With s = 1 the controller's model is exact." }));

  return { destroy() { alive = false; plot.dispose(); mbuf.delete(); scratch.delete(); view.destroy(); } };
}
