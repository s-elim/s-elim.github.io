// peg: peg-in-hole insertion of Lesson 10.3, running in the page with the script's controller.
// A 6-D Cartesian impedance with gravity compensation and null-space posture (as
// mjcourse.control.cartesian_impedance) drives the peg tip: 1.5 s to 3 cm above the hole's
// estimated position, then a descent at 2 cm/s. "Stiff" tracks the descent at 20 kN/m;
// "compliant" (2 kN/m across, 1 kN/m along the hole) never lets its target run more than
// 5 mm below the tip; "compliant + search" adds an Archimedean spiral (pitch 2 mm, 10 mm/s)
// when the peg stalls on the rim.
//
// Config: {"title": "...", "height": 300}

import { h, frame, slider, select, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";
import { idOf } from "../runtime.js";
import { solve, transpose, matMul, matVec, quatFromMat, quatMul, quatConj, quatToRotvec } from "../linalg.js";

const DELTA = 0.005, PITCH = 0.002, SPEED = 0.01, K_NULL = 20, K_ROT = 300;
const minJerk = (s) => { s = Math.min(Math.max(s, 0), 1); return s * s * s * (10 - 15 * s + 6 * s * s); };

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Peg in hole, 2 mm clearance", kind: "Lab" });
  let ep = null;
  const view = await createSimView(body, {
    model: "peg_insert", key: 1, height: config.height || 300, onReset: () => { ep = null; },
    camera: config.camera || { azimuth: -125, elevation: 18, distance: 0.55, target: [0.5, 0, 0.08] },
  });
  const sim = view.sim;
  const { mj, model, data } = sim;
  const nv = model.nv, h0 = model.opt.timestep;
  const tip = idOf(mj, model, "mjOBJ_SITE", "tool/peg_tip");
  const pegGeom = idOf(mj, model, "mjOBJ_GEOM", "tool/peg");
  const block = new Set(["hole_px", "hole_nx", "hole_py", "hole_ny", "hole_floor"].map((n) => idOf(mj, model, "mjOBJ_GEOM", n)));
  const jp = new mj.DoubleBuffer(3 * nv), jr = new mj.DoubleBuffer(3 * nv), mbuf = new mj.DoubleBuffer(nv * nv);
  mj.mj_forward(model, data);
  const home = Array.from(data.qpos);
  const down = quatFromMat(Array.from(data.site_xmat.slice(9 * tip, 9 * tip + 9)));
  const topSite = idOf(mj, model, "mjOBJ_SITE", "hole_top");
  const top = Array.from(data.site_xpos.slice(3 * topSite, 3 * topSite + 3));
  const tipPos = () => Array.from(data.site_xpos.slice(3 * tip, 3 * tip + 3));
  const opt = { mode: "compliant", error: 5, angle: 90 };

  /** mjcourse.control.cartesian_impedance for the peg tip (all 7 dofs are the arm's). */
  function impedance(xDes, k) {
    mj.mj_jacSite(model, data, jp, jr, tip);
    const P = Array.from(jp.GetView()), R = Array.from(jr.GetView());
    const rows = (M) => [0, 1, 2].map((i) => M.slice(i * nv, i * nv + nv));
    const J = rows(P).concat(rows(R)), JT = transpose(J);
    const qv = Array.from(data.qvel), q = Array.from(data.qpos);
    const xdot = matVec(rows(P), qv), omega = matVec(rows(R), qv), x = tipPos();
    const cur = quatFromMat(Array.from(data.site_xmat.slice(9 * tip, 9 * tip + 9)));
    const eRot = quatToRotvec(quatMul(down, quatConj(cur)));
    const dRot = 2 * Math.sqrt(K_ROT * 0.05);
    const wrench = [0, 1, 2].map((i) => k[i] * (xDes[i] - x[i]) - 2 * Math.sqrt(k[i] * 2) * xdot[i])
      .concat([0, 1, 2].map((i) => K_ROT * eRot[i] - dRot * omega[i]));
    const tau = matVec(JT, wrench).map((v, j) => v + data.qfrc_bias[j] + model.dof_damping[j] * qv[j]);
    // dynamically consistent null-space projection of a posture torque toward home
    mj.mj_fullM(model, data, mbuf);
    const Mv = mbuf.GetView(), M = [...Array(nv)].map((_, i) => Array.from(Mv.slice(i * nv, i * nv + nv)));
    const MinvJT = transpose(J.map((row) => solve(M, row)));              // nv x 6 (M is symmetric)
    const A = matMul(J, MinvJT);
    const Lam = transpose([0, 1, 2, 3, 4, 5].map((c) => solve(A, [0, 1, 2, 3, 4, 5].map((r) => (r === c ? 1 : 0)))));
    const Jbar = matMul(MinvJT, Lam);                                      // nv x 6
    const post = q.map((v, j) => K_NULL * (home[j] - v) - 2 * Math.sqrt(K_NULL) * qv[j]);
    const JbarTpost = matVec(transpose(Jbar), post);
    const nullPost = post.map((v, j) => v - J.reduce((s, row, r) => s + row[j] * JbarTpost[r], 0));
    return tau.map((v, j) => Math.min(Math.max(v + nullPost[j], model.actuator_ctrlrange[2 * j]), model.actuator_ctrlrange[2 * j + 1]));
  }

  function contactForce() {
    const f = [0, 0, 0];
    for (const c of sim.contacts()) {
      let sign = 0;
      if (c.geom1 === pegGeom && block.has(c.geom2)) sign = 1;
      else if (c.geom2 === pegGeom && block.has(c.geom1)) sign = -1;
      if (!sign) continue;
      for (let i = 0; i < 3; i++) f[i] += sign * (c.force[0] * c.frame[i] + c.force[1] * c.frame[3 + i] + c.force[2] * c.frame[6 + i]);
    }
    return Math.hypot(...f);
  }

  const outcome = (e) => (e.inserted != null ? (e.tilt < 2 ? "inserted" : "forced in, tilted") : (e.tilt < 2 ? "stalled on the rim" : "jammed, tilted"));

  const apply = (tau) => { for (let j = 0; j < nv; j++) data.ctrl[j] = tau[j]; };
  sim.controller = () => {
    mj.mj_forward(model, data);
    if (!ep) { apply(impedance(ep0Target(), [2000, 2000, 2000])); return; }
    if (ep.done) { apply(impedance(ep.last, ep.k)); return; }
    const t = data.time - ep.t0, x = tipPos();
    let target, k;
    if (t < 1.5) { const sm = minJerk(t / 1.2); target = ep.start.map((v, i) => v + (ep.above[i] - v) * sm); k = [2000, 2000, 2000]; }
    else if (ep.mode === "stiff") { ep.z = Math.max(ep.z - 0.02 * h0, 0.002); target = [ep.xy[0], ep.xy[1], ep.z]; k = [20000, 20000, 20000]; }
    else {
      ep.z = Math.max(ep.z - 0.02 * h0, x[2] - DELTA, 0.002);
      const onRim = x[2] > top[2] - 0.001;
      if (ep.mode === "search" && onRim && ep.z <= x[2] - DELTA + 1e-6 && ep.stalled == null) ep.stalled = t;
      if (ep.mode === "search" && ep.stalled != null && ep.dropped == null) {
        if (onRim) {
          const r = PITCH * ep.theta / (2 * Math.PI);
          ep.theta += SPEED * h0 / Math.max(r, 0.001);
          ep.xy = [ep.est[0] + r * Math.cos(ep.theta), ep.est[1] + r * Math.sin(ep.theta)];
        } else ep.dropped = t;
      }
      target = [ep.xy[0], ep.xy[1], ep.z]; k = [2000, 2000, 1000];
    }
    ep.last = target; ep.k = k;
    apply(impedance(target, k));
  };
  let idleTarget = null;
  const ep0Target = () => (idleTarget || (idleTarget = tipPos()));

  const plot = h("div");
  const fplot = new Plot(plot, { mode: "time", window: 12, xlabel: "time since start (s)", ylabel: "contact force (N)", height: 130, traces: [{ label: "peg-block contact force (N)" }] });
  const outs = { phase: readout("phase"), force: readout("contact force (N)"), peak: readout("peak force (N)"), tilt: readout("largest tilt (deg)"), depth: readout("tip height above hole floor (mm)"), outcome: readout("outcome") };

  // Measurements after each step: the same bookkeeping as the script.
  sim.recorders.add(() => {
    if (!ep || ep.done) return;
    const t = data.time - ep.t0, x = tipPos();
    const f = contactForce();
    ep.peak = Math.max(ep.peak, f); ep.force = f;
    ep.tilt = Math.max(ep.tilt, Math.acos(Math.min(1, -data.site_xmat[9 * tip + 8])) * 180 / Math.PI);
    if (ep.inserted == null && x[2] < 0.012) ep.inserted = t;
    if ((ep.inserted != null && t > ep.inserted + 1.0) || t > ep.limit) { ep.done = true; ep.result = outcome(ep); view.pause(); }
    ep.blockMax = Math.max(ep.blockMax || 0, f);                    // plot each 20-step block's maximum
    if (Math.round(t / h0) % 20 === 0) { fplot.push(t, [ep.blockMax]); ep.blockMax = 0; }
  });

  function insert() {
    view.reset();
    idleTarget = null;
    fplot.clear();
    const a = opt.angle * Math.PI / 180, e = opt.error / 1000;
    const est = [top[0] + e * Math.cos(a), top[1] + e * Math.sin(a)];
    const start = tipPos();
    ep = { mode: opt.mode, est, xy: est.slice(), start, above: [est[0], est[1], top[2] + 0.03], z: top[2] + 0.03, theta: 0,
      t0: data.time, peak: 0, force: 0, tilt: 0, inserted: null, stalled: null, dropped: null, done: false, result: "running",
      limit: opt.mode === "search" ? 30 : 10, last: start, k: [2000, 2000, 2000] };
    view.play();
  }

  let alive = true;
  const tick = () => {
    if (!alive) return;
    if (ep) {
      const t = data.time - ep.t0;
      outs.phase.set(ep.done ? "done" : t < 1.5 ? "move above the estimate" : ep.stalled != null && ep.dropped == null ? "spiral search" : "descend");
      outs.force.set(fmt(ep.force, 1)); outs.peak.set(fmt(ep.peak, 1)); outs.tilt.set(fmt(ep.tilt, 1));
      outs.depth.set((1000 * (tipPos()[2] - 0.004) + 0).toFixed(1).replace(/^-0\.0$/, "0.0")); outs.outcome.set(ep.result);
      fplot.draw();
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  body.append(h("div", { class: "toolbar" }, button("Insert", insert, "btn btn--primary")),
    h("div", { class: "controls" },
      select({ label: "controller", options: [["stiff 20 kN/m", "stiff"], ["compliant (5 N push limit)", "compliant"], ["compliant + spiral search", "search"]], value: opt.mode, onChange: (v) => { opt.mode = v; } }),
      slider({ label: "hole position error", unit: "mm", min: 0, max: 12, step: 0.5, value: opt.error, digits: 1, onInput: (v) => { opt.error = v; } }),
      slider({ label: "error direction", unit: "deg", min: 0, max: 315, step: 45, value: opt.angle, digits: 0, onInput: (v) => { opt.angle = v; } })),
    h("div", { class: "readouts" }, Object.values(outs)), plot,
    h("p", { class: "widget__note", html: "The clearance is 2 mm per side. The episode stops 1 s after the tip passes 12 mm above the hole floor, or after 10 s (30 s with search). Use 4x to shorten waits." }));

  return { destroy() { alive = false; [jp, jr, mbuf].forEach((b) => b.delete()); fplot.dispose(); view.destroy(); } };
}
