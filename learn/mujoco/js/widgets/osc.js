// osc: task-space control of arm7's tool (reach.xml) along a circle of radius 10 cm at
// 0.5 Hz, mirroring examples/l8_3_task_space.py. Three controllers:
//   Jacobian transpose   tau = J^T (Kp e + Kd edot) + c + b qdot        (Kp 400 N/m, Kd 40 N s/m)
//   resolved rate        qdot_ref = J+ (v* + 20 e_ref), joint PD to q_ref + c + b qdot
//   operational space    tau = J^T Lambda (a* + wn^2 e + 2 wn edot - Jdot qdot) + c + b qdot + N^T tau_posture
// The controller's model can have its link masses scaled by s: M_ctrl = A + s (M - A), c_ctrl = s c.
//
// Config: {"title": "...", "height": 300}

import { h, frame, select, slider, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";
import { idOf } from "../runtime.js";
import { solve, transpose, matVec, norm } from "../linalg.js";

const RADIUS = 0.1, FREQ = 0.5, DURATION = 6, SKIP = 2, WN = 30, K_NULL = 20;

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Tracking a circle in task space", kind: "Lab" });
  const view = await createSimView(body, {
    model: "reach", key: 1, height: config.height || 300, toolbar: false,
    camera: config.camera || { azimuth: -20, elevation: 15, distance: 1.9, target: [0.45, -0.05, 0.45] },
  });
  const sim = view.sim;
  const { mj, model, data } = sim;
  const nv = model.nv, hstep = model.opt.timestep;
  const site = idOf(mj, model, "mjOBJ_SITE", "ee"), body7 = model.site_bodyid[site];
  const elbow = idOf(mj, model, "mjOBJ_BODY", "link4");
  const scratch = new mj.MjData(model), kin = new mj.MjData(model);
  const mbuf = new mj.DoubleBuffer(nv * nv), jp = new mj.DoubleBuffer(3 * nv), jd = new mj.DoubleBuffer(3 * nv);
  const home = Array.from(data.qpos);
  const arm = Array.from(model.dof_armature), damp = Array.from(model.dof_damping);
  const lim = Array.from({ length: nv }, (_, j) => model.actuator_ctrlrange[2 * j + 1]);
  mj.mj_forward(model, data);
  const x0 = Array.from(data.site_xpos.slice(3 * site, 3 * site + 3));
  const center = [x0[0], x0[1] - RADIUS, x0[2]];
  const w = 2 * Math.PI * FREQ;
  const circle = (t) => {
    const c = Math.cos(w * t), s = Math.sin(w * t);
    return [[center[0], center[1] + RADIUS * c, center[2] + RADIUS * s], [0, -RADIUS * w * s, RADIUS * w * c], [0, -RADIUS * w * w * c, -RADIUS * w * w * s]];
  };
  const rows3 = (buf) => { const v = Array.from(buf.GetView()); return [0, 1, 2].map((i) => v.slice(i * nv, i * nv + nv)); };
  function massBias(q, qd, scale) {
    for (let j = 0; j < nv; j++) { scratch.qpos[j] = q[j]; scratch.qvel[j] = qd[j]; }
    mj.mj_forward(model, scratch);
    mj.mj_fullM(model, scratch, mbuf);
    const v = Array.from(mbuf.GetView());
    const M = Array.from({ length: nv }, (_, i) => v.slice(i * nv, i * nv + nv).map((m, k) => (i === k ? arm[i] + scale * (m - arm[i]) : scale * m)));
    return [M, Array.from(scratch.qfrc_bias).map((c) => scale * c)];
  }
  const mHome = massBias(home, new Array(nv).fill(0), 1)[0].map((r, i) => r[i]);
  const kpj = mHome.map((m) => m * 400), kdj = mHome.map((m) => 2 * m * 20);
  const opt = { kind: "osc", posture: true, scale: 1 };
  const st = { running: false, sum: 0, n: 0, peak: 0, elbowMin: Infinity, qref: home.slice() };

  sim.controller = (s) => {
    if (!st.running) return;
    const t = s.data.time;
    mj.mj_forward(model, s.data);                       // kinematics of the current state
    const q = Array.from(s.data.qpos), qd = Array.from(s.data.qvel);
    const x = Array.from(s.data.site_xpos.slice(3 * site, 3 * site + 3));
    const [xd, vd, ad] = circle(t);
    for (let i = 0; i < 3; i++) s.data.mocap_pos[i] = xd[i];
    if (t >= SKIP + hstep / 2) {
      const err = norm(xd.map((v, i) => v - x[i]));
      st.sum += err * err; st.n += 1; st.peak = Math.max(st.peak, err);
    }
    st.elbowMin = Math.min(st.elbowMin, s.data.xpos[3 * elbow + 2]);
    if (t >= DURATION - hstep / 2) { st.running = false; s.pause(); return; }
    mj.mj_jacSite(model, s.data, jp, null, site);
    const J = rows3(jp), JT = transpose(J);
    const v = matVec(J, qd);
    const e = xd.map((p, i) => p - x[i]), ed = vd.map((p, i) => p - v[i]);
    const [M, c] = massBias(q, qd, opt.scale);
    let tau;
    if (opt.kind === "jt") {
      const F = e.map((x_, i) => 400 * x_ + 40 * ed[i]);
      tau = matVec(JT, F).map((u, j) => u + c[j] + damp[j] * qd[j]);
    } else if (opt.kind === "rr") {
      const A = J.map((r, i) => J.map((r2, k) => r.reduce((acc, a, m) => acc + a * r2[m], 0) + (i === k ? 1e-4 : 0)));
      for (let j = 0; j < nv; j++) kin.qpos[j] = st.qref[j];
      mj.mj_kinematics(model, kin);
      const xr = Array.from(kin.site_xpos.slice(3 * site, 3 * site + 3));
      const y = solve(A, vd.map((p, i) => p + 20 * (xd[i] - xr[i])));
      let qdr = matVec(JT, y);
      if (opt.posture) {
        const z = home.map((hq, j) => 2 * (hq - st.qref[j]));
        const pinvJz = matVec(JT, solve(A, matVec(J, z)));      // pinv J z
        qdr = qdr.map((u, j) => u + z[j] - pinvJz[j]);
      }
      st.qref = st.qref.map((r, j) => r + hstep * qdr[j]);
      tau = q.map((qq, j) => kpj[j] * (st.qref[j] - qq) + kdj[j] * (qdr[j] - qd[j]) + c[j] + damp[j] * qd[j]);
    } else {
      mj.mj_jacDot(model, s.data, jd, null, x, body7);      // inputs are plain arrays; outputs need DoubleBuffers
      const Jd = rows3(jd);
      const MinvJT = transpose([0, 1, 2].map((i) => solve(M, J[i])));        // M^-1 J^T (7 x 3)
      const JMJ = J.map((r) => [0, 1, 2].map((k) => r.reduce((acc, a, m) => acc + a * MinvJT[m][k], 0)));
      const Lam = transpose([0, 1, 2].map((k) => solve(JMJ, [0, 1, 2].map((i) => (i === k ? 1 : 0)))));
      const acc = ad.map((a, i) => a + WN * WN * e[i] + 2 * WN * ed[i] - Jd[i].reduce((s2, jv, m) => s2 + jv * qd[m], 0));
      const F = matVec(Lam, acc);
      tau = matVec(JT, F).map((u, j) => u + c[j] + damp[j] * qd[j]);
      if (opt.posture) {
        const Jbar = MinvJT.map((r) => [0, 1, 2].map((k) => r.reduce((s2, a, m) => s2 + a * Lam[m][k], 0)));   // 7 x 3
        const t0 = q.map((qq, j) => K_NULL * (home[j] - qq) - 2 * Math.sqrt(K_NULL) * qd[j]);
        const JbarT_t0 = [0, 1, 2].map((k) => Jbar.reduce((s2, r, j) => s2 + r[k] * t0[j], 0));
        const corr = matVec(JT, JbarT_t0);
        tau = tau.map((u, j) => u + t0[j] - corr[j]);
      }
    }
    for (let j = 0; j < nv; j++) s.data.ctrl[j] = Math.min(Math.max(tau[j], -lim[j]), lim[j]);
  };

  const errPlot = h("div"), elbowPlot = h("div");
  const plotE = new Plot(errPlot, { mode: "time", window: DURATION, xlabel: "time (s)", ylabel: "position error (mm)", height: 130, traces: [{ label: "error (mm)" }] });
  const plotH = new Plot(elbowPlot, { mode: "time", window: DURATION, xlabel: "time (s)", ylabel: "elbow height (m)", height: 110, traces: [{ label: "elbow (link4) height (m)" }] });
  const outs = { t: readout("time (s)"), rms: readout("RMS error after 2 s (mm)"), peak: readout("peak error after 2 s (mm)"), elbow: readout("lowest elbow height (m)") };
  let alive = true;
  const tick = () => {
    if (!alive) return;
    if (st.running) {
      const x = Array.from(data.site_xpos.slice(3 * site, 3 * site + 3));
      plotE.push(data.time, [1000 * norm(circle(data.time)[0].map((v, i) => v - x[i]))]); plotE.draw();
      plotH.push(data.time, [data.xpos[3 * elbow + 2]]); plotH.draw();
    }
    outs.t.set(fmt(data.time, 2));
    outs.rms.set(st.n ? fmt(1000 * Math.sqrt(st.sum / st.n), 3) : "-");
    outs.peak.set(st.n ? fmt(1000 * st.peak, 3) : "-");
    outs.elbow.set(Number.isFinite(st.elbowMin) ? fmt(st.elbowMin, 3) : "-");
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  const run = () => {
    sim.reset();
    Object.assign(st, { running: true, sum: 0, n: 0, peak: 0, elbowMin: Infinity, qref: home.slice() });
    plotE.clear(); plotH.clear();
    sim.play();
  };
  body.append(h("div", { class: "toolbar" }, button("Run 6 s", run, "btn btn--primary")),
    h("div", { class: "controls" },
      select({ label: "controller", options: [["operational space", "osc"], ["resolved rate (differential IK + joint PD)", "rr"], ["Jacobian transpose", "jt"]], value: "osc",
        onChange: (v) => { opt.kind = v; } }),
      select({ label: "null-space posture term", options: [["on", "on"], ["off", "off"]], value: "on", onChange: (v) => { opt.posture = v === "on"; } }),
      slider({ label: "controller model: link masses × s", min: 0.5, max: 1.5, step: 0.05, value: 1, digits: 2, onInput: (v) => { opt.scale = v; } })),
    h("div", { class: "readouts" }, Object.values(outs)), errPlot, elbowPlot,
    h("p", { class: "widget__note", html: "The green sphere is the target moving along the circle. The posture term acts in the null space of the resolved-rate and operational-space controllers; the Jacobian-transpose controller, as in the lesson's script, has none." }));

  return { destroy() { alive = false; plotE.dispose(); plotH.dispose(); [mbuf, jp, jd].forEach((b) => b.delete()); scratch.delete(); kin.delete(); view.destroy(); } };
}
