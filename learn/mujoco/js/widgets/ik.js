// ik: damped-least-squares inverse kinematics for arm7 (reach.xml), run in the page.
//
// One iteration is the update of mjcourse.kinematics.solve_ik:
//   dq = J^T (J J^T + lambda^2 I)^-1 e  (+ N k (q_mid - q) with the posture term),
// clipped to 0.2 rad in norm and clamped to the joint ranges. The arm is posed
// kinematically: the simulation never steps, so gravity plays no part.
//
// Config: {"title": "...", "height": 320, "mode": "pose" | "position", "damping": 0.01}

import { h, frame, slider, select, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";
import { idOf } from "../runtime.js";
import { symEig, solve, transpose, matVec, norm, quatFromMat, quatMul, quatConj, quatToRotvec } from "../linalg.js";

const STEP_LIMIT = 0.2, TOL_POS = 1e-4, TOL_ROT = 1e-3, MAX_ITERS = 300;

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Inverse kinematics, one iteration at a time", kind: "Lab" });
  const view = await createSimView(body, {
    model: "reach", key: 1, height: config.height || 320, toolbar: false, hud: false,
    camera: config.camera || { azimuth: -55, elevation: 22, distance: 2.1, target: [0.25, 0, 0.45] },
  });
  const sim = view.sim;
  // Kinematic posing only: keyboard shortcuts must not start the physics.
  sim.play = () => {}; sim.toggle = () => {}; sim.step = () => {};
  const { mj, model, data } = sim;
  const nv = model.nv;
  const site = idOf(mj, model, "mjOBJ_SITE", "ee");
  const jp = new mj.DoubleBuffer(3 * nv), jr = new mj.DoubleBuffer(3 * nv);
  const lo = [], hi = [];
  for (let j = 0; j < nv; j++) { lo.push(model.jnt_range[2 * j]); hi.push(model.jnt_range[2 * j + 1]); }
  const mid = lo.map((v, j) => (v + hi[j]) / 2);
  const home = Array.from(data.qpos);
  const eeQuat = () => quatFromMat(Array.from(data.site_xmat.slice(9 * site, 9 * site + 9)));
  const eePos = () => Array.from(data.site_xpos.slice(3 * site, 3 * site + 3));

  const target = { pos: eePos().map((v, i) => v + [0.1, 0.15, -0.1][i]), quat: eeQuat() };
  const opt = { mode: config.mode || "pose", lambda: config.damping ?? 0.01, posture: "off" };
  let iter = 0, running = false, last = null, status = "ready", maxStep = 0;

  function setTarget() {
    for (let i = 0; i < 3; i++) data.mocap_pos[i] = target.pos[i];
    mj.mj_forward(model, data);
  }

  /** One damped-least-squares iteration. Returns errors measured before the update. */
  function iterate() {
    mj.mj_kinematics(model, data);
    mj.mj_comPos(model, data);
    mj.mj_jacSite(model, data, jp, jr, site);
    const P = Array.from(jp.GetView()), R = Array.from(jr.GetView());
    const rows = (M) => [0, 1, 2].map((i) => M.slice(i * nv, i * nv + nv));
    const p = eePos();
    const ePos = target.pos.map((v, i) => v - p[i]);
    let J = rows(P), e = ePos, rotErr = 0;
    if (opt.mode === "pose") {
      const eRot = quatToRotvec(quatMul(target.quat, quatConj(eeQuat())));
      J = J.concat(rows(R));
      e = ePos.concat(eRot);
      rotErr = norm(eRot);
    }
    const posErr = norm(ePos);
    const JT = transpose(J);
    const m = J.length;
    const A = J.map((ri, i) => J.map((rj, k) => ri.reduce((s, v, c) => s + v * rj[c], 0) + (i === k ? opt.lambda ** 2 : 0)));
    const converged = posErr < TOL_POS && rotErr < TOL_ROT;
    const sv = symEig(A.map((r, i) => r.map((v, k) => v - (i === k ? opt.lambda ** 2 : 0)))).values
      .map((x) => Math.sqrt(Math.max(x, 0))).sort((a, b) => a - b);
    const q = Array.from(data.qpos);
    let step = 0;
    if (!converged) {
      let dq = matVec(JT, solve(A, e));
      if (opt.posture !== "off") {
        const z = q.map((v, j) => 0.1 * (mid[j] - v));
        let N;
        if (opt.posture === "damped") {                              // I - J^T A^-1 J
          const AinvJ = transpose(transpose(J).map((col) => solve(A, col)));
          N = JT.map((rj, j) => q.map((_, k) => (j === k ? 1 : 0) - rj.reduce((s, v, i) => s + v * AinvJ[i][k], 0)));
        } else {                                                     // I - V_r V_r^T from J^T J
          const { values, vectors } = symEig(JT.map((ri) => JT.map((rk) => ri.reduce((s, v, i) => s + v * rk[i], 0))));
          const top = Math.max(...values);
          N = q.map((_, j) => q.map((_, k) => (j === k ? 1 : 0)));
          values.forEach((lam, idx) => {
            if (lam > 1e-12 * top) for (let j = 0; j < nv; j++) for (let k = 0; k < nv; k++) N[j][k] -= vectors[idx][j] * vectors[idx][k];
          });
        }
        const nz = matVec(N, z);
        dq = dq.map((v, j) => v + nz[j]);
      }
      step = norm(dq);
      maxStep = Math.max(maxStep, step);
      if (step > STEP_LIMIT) dq = dq.map((v) => (v * STEP_LIMIT) / step);
      for (let j = 0; j < nv; j++) data.qpos[j] = Math.min(Math.max(q[j] + dq[j], lo[j]), hi[j]);
      mj.mj_forward(model, data);
    }
    const qa = Array.from(data.qpos);
    const atLimit = qa.filter((v, j) => v - lo[j] < 1e-9 || hi[j] - v < 1e-9).length;
    last = { posErr, rotErr, sigmaMin: sv[0], atLimit, step, converged, m };
    return last;
  }

  // ---- controls
  const toolbar = h("div", { class: "toolbar" });
  const plotHolder = h("div");
  const outs = { iter: readout("iteration"), pos: readout("position error (mm)"), rot: readout("orientation error (deg)"),
    sigma: readout("smallest singular value"), lim: readout("joints at a limit"), step: readout("largest unclipped step (rad)"), status: readout("status") };
  const plot = new Plot(plotHolder, { mode: "time", window: MAX_ITERS, xlabel: "iteration", ylabel: "log10 error",
    height: 140, traces: [{ label: "position (log10 mm)" }, { label: "orientation (log10 deg)", dash: true }] });

  function show() {
    outs.iter.set(String(iter));
    if (last) {
      outs.pos.set(fmt(1000 * last.posErr, 3)); outs.rot.set(opt.mode === "pose" ? fmt(last.rotErr * 180 / Math.PI, 3) : "-");
      outs.sigma.set(fmt(last.sigmaMin, 4)); outs.lim.set(String(last.atLimit)); outs.step.set(fmt(maxStep, 3));
    }
    outs.status.set(status);
  }
  // Iterations are counted as in solve_ik: the k-th error evaluation is iteration k.
  function oneStep() {
    if (last?.converged || iter >= MAX_ITERS) { running = false; return; }
    iter += 1;
    const r = iterate();
    plot.push(iter, [Math.log10(Math.max(1000 * r.posErr, 1e-4)), opt.mode === "pose" ? Math.log10(Math.max(r.rotErr * 180 / Math.PI, 1e-4)) : NaN]);
    plot.draw();
    if (r.converged) { status = `converged in ${iter} iterations`; running = false; }
    else if (iter >= MAX_ITERS) { status = r.atLimit ? `stopped: ${r.atLimit} joint(s) at a limit` : "stopped: iteration limit"; running = false; }
    show();
  }
  function frameLoop() {
    if (!running) return;
    oneStep();
    if (running) requestAnimationFrame(frameLoop);
  }
  function restart(q) {
    running = false; iter = 0; last = null; status = "ready"; maxStep = 0; plot.clear();
    if (q) { q.forEach((v, j) => { data.qpos[j] = v; }); mj.mj_forward(model, data); }
    show();
  }
  const solveBtn = button("Solve", () => { if (last?.converged) restart(null); status = "solving"; running = true; requestAnimationFrame(frameLoop); }, "btn btn--primary");
  toolbar.append(solveBtn,
    button("One iteration", () => { running = false; oneStep(); }),
    button("Arm to home", () => restart(home)),
    button("Random start", () => restart(lo.map((l, j) => l + Math.random() * (hi[j] - l)))),
    button("Near-singular test", () => {
      [0, 0.001, 0, 0.001, 0, 0.001, 0].forEach((v, j) => { data.qpos[j] = v; });   // 1 mrad short of straight up
      mj.mj_forward(model, data);
      target.pos = eePos().map((v, i) => (i === 2 ? v - 0.03 : v));                  // 3 cm straight down
      opt.mode = "position";
      taskRow.querySelector("select").value = "position";
      sliders.forEach((sl, i) => sl.set(target.pos[i]));
      setTarget(); restart(null);
    }),
    button("Random reachable target", () => {
      const saved = Array.from(data.qpos);
      lo.forEach((l, j) => { data.qpos[j] = l + Math.random() * (hi[j] - l); });
      mj.mj_kinematics(model, data);
      target.pos = eePos(); target.quat = eeQuat();
      saved.forEach((v, j) => { data.qpos[j] = v; });
      sliders.forEach((s, i) => s.set(target.pos[i]));
      setTarget(); restart(null);
    }));
  const sliders = ["x", "y", "z"].map((ax, i) => slider({ label: `target ${ax}`, unit: "m", min: i === 2 ? 0 : -0.9, max: i === 2 ? 1.4 : 0.9, step: 0.001,
    value: target.pos[i], digits: 3, onInput: (v) => { target.pos[i] = v; setTarget(); restart(null); } }));
  const taskRow = select({ label: "task", options: [["position and orientation (6-D)", "pose"], ["position only (3-D)", "position"]], value: opt.mode,
    onChange: (v) => { opt.mode = v; restart(null); } });
  const controls = h("div", { class: "controls" },
    taskRow,
    slider({ label: "damping log10(λ)", min: -6, max: 0, step: 0.1, value: Math.log10(opt.lambda), digits: 1,
      onInput: (v) => { opt.lambda = 10 ** v; restart(null); } }),
    select({ label: "posture term", options: [["off", "off"], ["to mid-range, exact projector", "exact"], ["to mid-range, damped projector", "damped"]], value: "off",
      onChange: (v) => { opt.posture = v; restart(null); } }),
    ...sliders);
  const box = h("div", { class: "readouts" }, Object.values(outs));
  body.append(toolbar, controls, box, plotHolder,
    h("p", { class: "widget__note", html: "The orientation target is the tool's orientation at the home pose (pointing down) until you draw a random reachable target, which sets both. Tolerances: 0.1 mm and 0.057 degrees; at most 300 iterations." }));
  sim.on((s, event) => { if (event === "reset") { setTarget(); restart(null); } });   // the "r" shortcut
  setTarget();
  show();

  return {
    destroy() { running = false; plot.dispose(); jp.delete(); jr.delete(); view.destroy(); },
  };
}
