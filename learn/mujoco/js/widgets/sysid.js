// sysid: least-squares identification of a pendulum's mass, damping and friction loss (Lesson 18.1).
// A pendulum with hidden parameters is driven by a multisine torque for 10 s; its angle is
// measured with noise; derivatives come from finite differences or a Savitzky-Golay filter;
// tau = m (L^2 qdd + g L sin q) + I_c qdd + b qd + f sign(qd) is solved for (m, b, f); the
// estimate is validated by simulating a held-out excitation. Same model and method as
// examples/l18_1_sysid_least_squares.py; the hidden values here are drawn at random.
//
// Config: {"title": "..."}

import { h, frame, select, button, readout, fmt } from "./ui.js";
import { Plot } from "../plot.js";
import { getMujoco, loadModel, idOf } from "../runtime.js";
import { solve, transpose, matMul, matVec } from "../linalg.js";

const L = 0.5, IC = 1e-4, G = 9.81, T = 10, WINDOW = 51;

function mulberry32(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Savitzky-Golay kernels (cubic, centred) for the value, first and second derivative. */
function sgKernels(window, h) {
  const half = (window - 1) / 2;
  const A = Array.from({ length: window }, (_, i) => { const x = i - half; return [1, x, x * x, x * x * x]; });
  const AtA = matMul(transpose(A), A);
  const inv = [0, 1, 2, 3].map((c) => solve(AtA, [0, 1, 2, 3].map((r) => (r === c ? 1 : 0))));   // columns of (AtA)^-1
  const pinv = matMul(transpose(inv), transpose(A));                                            // 4 x window
  return [pinv[0], pinv[1].map((v) => v / h), pinv[2].map((v) => (2 * v) / (h * h))];
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Identify a pendulum", kind: "Lab" });
  const mj = await getMujoco();
  const model = await loadModel("pendulum");
  const data = new mj.MjData(model);
  const pole = idOf(mj, model, "mjOBJ_BODY", "pole"), hinge = idOf(mj, model, "mjOBJ_JOINT", "hinge");
  const h0 = model.opt.timestep, N = Math.round(T / h0);
  const opt = { method: "sg", noise: 0.0005, amplitude: 2.5, skipSlow: false };
  let rand = mulberry32(42), hidden = null, record = null, estimate = null, revealed = false;

  function setParams(p) {
    model.body_mass[pole] = p.mass;
    model.dof_damping[hinge] = p.damping;
    model.dof_frictionloss[hinge] = p.frictionloss;
    mj.mj_setConst(model, data);                     // derived constants after a mass change
  }
  function multisine(seed, amplitude) {
    const r = mulberry32(seed);
    const f = Array.from({ length: 5 }, () => 0.2 + 2.8 * r()), ph = Array.from({ length: 5 }, () => 2 * Math.PI * r());
    return Array.from({ length: N }, (_, k) => amplitude * f.reduce((s, fi, i) => s + Math.sin(2 * Math.PI * fi * k * h0 + ph[i]), 0) / 5);
  }
  function simulate(p, torque) {
    setParams(p);
    mj.mj_resetData(model, data);
    const q = new Float64Array(N);
    for (let k = 0; k < N; k++) { q[k] = data.qpos[0]; data.ctrl[0] = torque[k]; mj.mj_step(model, data); }
    return q;
  }
  const gauss = (r) => Math.sqrt(-2 * Math.log(r() + 1e-12)) * Math.cos(2 * Math.PI * r());

  function derivatives(q) {
    if (opt.method === "fd") {
      const qd = q.map((_, k) => (q[Math.min(k + 1, N - 1)] - q[Math.max(k - 1, 0)]) / ((Math.min(k + 1, N - 1) - Math.max(k - 1, 0)) * h0));
      const qdd = qd.map((_, k) => (qd[Math.min(k + 1, N - 1)] - qd[Math.max(k - 1, 0)]) / ((Math.min(k + 1, N - 1) - Math.max(k - 1, 0)) * h0));
      return [Array.from(q), Array.from(qd), Array.from(qdd)];
    }
    const kernels = sgKernels(WINDOW, h0), half = (WINDOW - 1) / 2;
    return kernels.map((kern) => Array.from({ length: N }, (_, k) => {
      if (k < half || k >= N - half) return NaN;
      let s = 0;
      for (let j = 0; j < WINDOW; j++) s += kern[j] * q[k - half + j];
      return s;
    }));
  }

  function fit() {
    const [q, qd, qdd] = derivatives(record.q);
    const X = [], y = [];
    for (let k = 30; k < N - 30; k++) {
      if (!Number.isFinite(qdd[k]) || (opt.skipSlow && Math.abs(qd[k]) < 0.1)) continue;
      X.push([L * L * qdd[k] + G * L * Math.sin(q[k]), qd[k], Math.sign(qd[k])]);
      y.push(record.torque[k] - IC * qdd[k]);
    }
    if (X.length < 100) return null;
    const XT = transpose(X);
    const theta = solve(matMul(XT, X), matVec(XT, y));
    return { mass: theta[0], damping: theta[1], frictionloss: theta[2], samples: X.length };
  }

  const plotEl = h("div");
  const plot = new Plot(plotEl, { mode: "xy", xlabel: "time (s)", ylabel: "angle (rad)", height: 170,
    traces: [{ label: "measured, held-out excitation" }, { label: "simulated with the estimate" }] });
  const outs = { hidden: readout("hidden parameters"), est: readout("estimate: mass, damping, friction loss"), used: readout("samples used"), val: readout("held-out angle RMS error (mrad)") };
  const showHidden = () => outs.hidden.set(hidden ? (revealed ? `${fmt(hidden.mass, 3)} kg, ${fmt(hidden.damping, 3)}, ${fmt(hidden.frictionloss, 3)}` : "hidden") : "-");

  function newPendulum() {
    hidden = { mass: 0.6 + 1.4 * rand(), damping: 0.02 + 0.15 * rand(), frictionloss: 0.01 + 0.09 * rand() };
    record = null; estimate = null; revealed = false;
    outs.est.set("-"); outs.used.set("-"); outs.val.set("-"); showHidden();
    plot.setSeries(0, [], []); plot.setSeries(1, [], []); plot.draw();
  }
  function recordRun() {
    if (!hidden) newPendulum();
    const torque = multisine(1, opt.amplitude);
    const clean = simulate(hidden, torque), r = mulberry32(7);
    record = { torque, q: clean.map((v) => v + opt.noise * gauss(r)) };
    outs.est.set("recorded; press Fit"); outs.used.set("-"); outs.val.set("-");
  }
  function doFit() {
    if (!record) recordRun();
    estimate = fit();
    if (!estimate) { outs.est.set("too few samples (the pendulum barely moved)"); return; }
    outs.est.set(`${fmt(estimate.mass, 3)} kg, ${fmt(estimate.damping, 3)}, ${fmt(estimate.frictionloss, 3)}`);
    outs.used.set(String(estimate.samples));
    // validation: a different excitation, measured with noise, against the estimate simulated open loop
    const torque = multisine(7, 2.5), r = mulberry32(8);
    const measured = simulate(hidden, torque).map((v) => v + opt.noise * gauss(r));
    const ok = Number.isFinite(estimate.mass) && estimate.mass > 0.01;
    const predicted = ok ? simulate({ mass: estimate.mass, damping: Math.max(estimate.damping, 0), frictionloss: Math.max(estimate.frictionloss, 0) }, torque) : null;
    const step = 10, xs = [], ym = [], yp = [];
    let se = 0;
    for (let k = 0; k < N; k++) {
      if (predicted) se += (predicted[k] - measured[k]) ** 2;
      if (k % step === 0) { xs.push(k * h0); ym.push(measured[k]); yp.push(predicted ? predicted[k] : NaN); }
    }
    outs.val.set(predicted ? fmt(1000 * Math.sqrt(se / N), 2) : "estimate not physical (mass near zero)");
    plot.setSeries(0, xs, ym); plot.setSeries(1, xs, predicted ? yp : []); plot.draw();
  }

  body.append(
    h("div", { class: "toolbar" }, button("New hidden pendulum", newPendulum), button("Record 10 s", recordRun), button("Fit", doFit, "btn btn--primary"),
      button("Reveal", () => { revealed = true; showHidden(); })),
    h("div", { class: "controls" },
      select({ label: "derivatives", options: [["Savitzky-Golay (0.1 s cubic)", "sg"], ["finite differences", "fd"]], value: "sg", onChange: (v) => { opt.method = v; } }),
      select({ label: "angle noise (mrad)", options: [["0", "0"], ["0.5", "0.0005"], ["2", "0.002"]], value: "0.0005", onChange: (v) => { opt.noise = Number(v); record = null; } }),
      select({ label: "excitation amplitude (N m)", options: [["2.5", "2.5"], ["0.25", "0.25"]], value: "2.5", onChange: (v) => { opt.amplitude = Number(v); record = null; } }),
      select({ label: "leave out samples slower than 0.1 rad/s", options: [["no", "no"], ["yes", "yes"]], value: "no", onChange: (v) => { opt.skipSlow = v === "yes"; } })),
    h("div", { class: "readouts" }, Object.values(outs)), plotEl,
    h("p", { class: "widget__note", html: "Changing the noise or the excitation needs a new recording; Fit records one if needed. The validation plot shows 10 s of a different excitation: the measured angle and the angle the estimated model predicts, open loop." }));
  newPendulum();

  return { destroy() { data.delete(); plot.dispose(); } };
}
