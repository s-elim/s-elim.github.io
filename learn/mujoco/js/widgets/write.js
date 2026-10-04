// write: arm7 writes "MuJoCo" on a board under operational-space or Jacobian-transpose control (Showcase).
// The reference, letters and controllers are those of examples/showcase_robot_writes.py: 6 cm letters from a
// stroke font, minimum-jerk segments at a chosen average speed, the pen lifted 3 cm between strokes; OSC with
// bandwidth 30 rad/s and null-space posture, or J^T (400 e + 40 edot) with gravity compensation. The ink is
// the tool's actual path while the pen is down, so tracking error is visible in the letters.
//
// Config: {"title": "...", "height": 320}

import * as THREE from "three";
import { h, frame, select, button, readout, createSimView, fmt } from "./ui.js";
import { idOf } from "../runtime.js";
import { solve, transpose, matVec, norm } from "../linalg.js";

const HEIGHT = 0.06, LIFT = 0.03, WN = 30, K_NULL = 20;
const circle = (cx, cy, r, a0, a1, n) => Array.from({ length: n }, (_, i) => { const a = (a0 + (a1 - a0) * i / (n - 1)) * Math.PI / 180; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; });
const FONT = {
  M: [[[0, 0], [0, 1.5], [0.5, 0.6], [1, 1.5], [1, 0]]],
  u: [[[0, 1], [0, 0.3], [0.3, 0], [0.7, 0], [1, 0.3]], [[1, 1], [1, 0]]],
  J: [[[0.3, 1.5], [1, 1.5]], [[0.7, 1.5], [0.7, 0.35], [0.45, 0], [0.15, 0], [0, 0.3]]],
  o: [circle(0.5, 0.5, 0.5, 90, 450, 17)],
  C: [circle(0.75, 0.75, 0.75, 45, 315, 17)],
};
const ADVANCE = { M: 1.4, u: 1.35, J: 1.3, o: 1.3, C: 1.35 };

function strokes(word, origin) {
  const scale = HEIGHT / 1.5, width = [...word].reduce((s, c) => s + ADVANCE[c], 0) * scale, out = [];
  let cursor = 0;
  for (const c of word) {
    for (const st of FONT[c]) out.push(st.map(([u, v]) => [origin[0], origin[1] + (cursor + u) * scale - width / 2, origin[2] + (v - 0.75) * scale]));
    cursor += ADVANCE[c];
  }
  return out;
}
const sub = (a, b) => a.map((v, i) => v - b[i]), dist = (a, b) => norm(sub(a, b));
function minJerk(a, b, duration, h, down, out) {
  const n = Math.max(Math.round(duration / h), 1);
  for (let k = 0; k < n; k++) {
    const s = k / n, p = 10 * s ** 3 - 15 * s ** 4 + 6 * s ** 5;
    const dp = (30 * s ** 2 - 60 * s ** 3 + 30 * s ** 4) / duration, ddp = (60 * s - 180 * s ** 2 + 120 * s ** 3) / duration ** 2;
    out.push([a.map((v, i) => v + (b[i] - v) * p), a.map((v, i) => (b[i] - v) * dp), a.map((v, i) => (b[i] - v) * ddp), down]);
  }
}
function reference(word, start, boardX, speed, h) {
  let pos = start.slice();
  const out = [];
  for (const st of strokes(word, [boardX, start[1], start[2]])) {
    const lifted = [st[0][0] - LIFT, st[0][1], st[0][2]];
    minJerk(pos, lifted, Math.max(dist(lifted, pos) / (2 * speed), 0.15), h, false, out);
    minJerk(lifted, st[0], Math.max(dist(st[0], lifted) / (2 * speed), 0.15), h, false, out);
    for (let i = 1; i < st.length; i++) minJerk(st[i - 1], st[i], Math.max(dist(st[i], st[i - 1]) / speed, 0.05), h, true, out);
    pos = [st[st.length - 1][0] - LIFT, st[st.length - 1][1], st[st.length - 1][2]];
    minJerk(st[st.length - 1], pos, 0.15, h, false, out);
  }
  return out;
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "A robot that writes", kind: "Lab" });
  const view = await createSimView(body, { model: "arm7", height: config.height || 320, toolbar: false,
    camera: { azimuth: 0, elevation: -10, distance: 0.75, target: [0.56, 0, 0.33] } });
  const sim = view.sim, { mj, model, data } = sim;
  const nv = model.nv, hstep = model.opt.timestep;
  sim.keyframe = idOf(mj, model, "mjOBJ_KEY", "home");
  sim.reset(sim.keyframe);
  const site = idOf(mj, model, "mjOBJ_SITE", "ee"), body7 = model.site_bodyid[site];
  const scratch = new mj.MjData(model);
  const mbuf = new mj.DoubleBuffer(nv * nv), jp = new mj.DoubleBuffer(3 * nv), jd = new mj.DoubleBuffer(3 * nv);
  const home = Array.from(data.qpos), damp = Array.from(model.dof_damping);
  const lim = Array.from({ length: nv }, (_, j) => model.actuator_ctrlrange[2 * j + 1]);
  mj.mj_forward(model, data);
  const start = Array.from(data.site_xpos.slice(3 * site, 3 * site + 3)), boardX = start[0] + LIFT;
  const opt = { kind: "osc", speed: 0.1 };
  let ref = [], k = 0, stats = { sum: 0, n: 0, peak: 0 }, prevInk = null;

  // board and ink
  const board = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 0.5), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.55, side: THREE.DoubleSide }));
  board.position.set(boardX + 0.004, start[1], start[2]);
  board.rotation.y = Math.PI / 2;
  const inkGeo = new THREE.BufferGeometry(), ink = new THREE.LineSegments(inkGeo, new THREE.LineBasicMaterial({ color: 0x0b3d91 }));
  ink.frustumCulled = false;
  view.viewer.overlayGroup.add(board, ink);
  let inkPts = [];

  const rows3 = (buf) => { const v = Array.from(buf.GetView()); return [0, 1, 2].map((i) => v.slice(i * nv, i * nv + nv)); };
  function massBias(q, qd) {
    for (let j = 0; j < nv; j++) { scratch.qpos[j] = q[j]; scratch.qvel[j] = qd[j]; }
    mj.mj_forward(model, scratch);
    mj.mj_fullM(model, scratch, mbuf);
    const v = Array.from(mbuf.GetView());
    return [Array.from({ length: nv }, (_, i) => v.slice(i * nv, i * nv + nv)), Array.from(scratch.qfrc_bias)];
  }

  sim.controller = (s) => {
    if (!ref.length) return;
    mj.mj_forward(model, s.data);
    const q = Array.from(s.data.qpos), qd = Array.from(s.data.qvel);
    const x = Array.from(s.data.site_xpos.slice(3 * site, 3 * site + 3));
    if (k >= ref.length) { ref = []; s.pause(); view.syncPlay(); return; }
    const [xd, vd, ad, down] = ref[k++];
    if (down) {                                           // the error at this step, as the script measures it
      const err = dist(xd, x);
      stats.sum += err * err; stats.n += 1; stats.peak = Math.max(stats.peak, err);
      if (prevInk) inkPts.push(...prevInk, ...x);
      prevInk = x;
    } else prevInk = null;
    mj.mj_jacSite(model, s.data, jp, null, site);
    const J = rows3(jp), JT = transpose(J), v = matVec(J, qd);
    const e = xd.map((p, i) => p - x[i]), ed = vd.map((p, i) => p - v[i]);
    const [M, c] = massBias(q, qd);
    let tau;
    if (opt.kind === "jt") {
      tau = matVec(JT, e.map((x_, i) => 400 * x_ + 40 * ed[i])).map((u, j) => u + c[j] + damp[j] * qd[j]);
    } else {
      mj.mj_jacDot(model, s.data, jd, null, x, body7);
      const Jd = rows3(jd);
      const MinvJT = transpose([0, 1, 2].map((i) => solve(M, J[i])));
      const JMJ = J.map((r) => [0, 1, 2].map((kk) => r.reduce((acc, a, m) => acc + a * MinvJT[m][kk], 0)));
      const Lam = transpose([0, 1, 2].map((kk) => solve(JMJ, [0, 1, 2].map((i) => (i === kk ? 1 : 0)))));
      const acc = ad.map((a, i) => a + WN * WN * e[i] + 2 * WN * ed[i] - Jd[i].reduce((s2, jv, m) => s2 + jv * qd[m], 0));
      tau = matVec(JT, matVec(Lam, acc)).map((u, j) => u + c[j] + damp[j] * qd[j]);
      const Jbar = MinvJT.map((r) => [0, 1, 2].map((kk) => r.reduce((s2, a, m) => s2 + a * Lam[m][kk], 0)));
      const t0 = q.map((qq, j) => K_NULL * (home[j] - qq) - 2 * Math.sqrt(K_NULL) * qd[j]);
      const corr = matVec(JT, [0, 1, 2].map((kk) => Jbar.reduce((s2, r, j) => s2 + r[kk] * t0[j], 0)));
      tau = tau.map((u, j) => u + t0[j] - corr[j]);
    }
    for (let j = 0; j < nv; j++) s.data.ctrl[j] = Math.min(Math.max(tau[j], -lim[j]), lim[j]);
  };

  const outs = { rms: readout("pen-down RMS error"), peak: readout("largest error"), time: readout("time") };
  let alive = true;
  const tick = () => {
    if (!alive) return;
    inkGeo.setAttribute("position", new THREE.Float32BufferAttribute(inkPts, 3));
    if (stats.n) { outs.rms.set(`${fmt(1000 * Math.sqrt(stats.sum / stats.n), 2)} mm`); outs.peak.set(`${fmt(1000 * stats.peak, 2)} mm`); }
    outs.time.set(`${fmt(data.time, 1)} s`);
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  function writeWord() {
    view.reset();
    mj.mj_forward(model, data);
    ref = reference("MuJoCo", start, boardX, opt.speed, hstep);
    k = 0; stats = { sum: 0, n: 0, peak: 0 }; prevInk = null; inkPts = [];
    outs.rms.set("-"); outs.peak.set("-");
    view.play();
  }

  body.append(
    h("div", { class: "toolbar" }, button("Write", writeWord, "btn btn--primary"), button("Pause / play", () => view.toggle())),
    h("div", { class: "controls" },
      select({ label: "controller", options: [["operational space (30 rad/s)", "osc"], ["Jacobian transpose (400 N/m, 40 N s/m)", "jt"]], value: "osc", onChange: (v) => { opt.kind = v; } }),
      select({ label: "average writing speed", options: [["5 cm/s", "0.05"], ["10 cm/s", "0.1"], ["20 cm/s", "0.2"], ["40 cm/s", "0.4"]], value: "0.1", onChange: (v) => { opt.speed = Number(v); } })),
    h("div", { class: "readouts" }, Object.values(outs)),
    h("p", { class: "widget__note", html: "Settings apply at the next <b>Write</b>. The ink is where the tool actually went while the pen was down; the board is drawn, not simulated." }));
  writeWord();

  return { destroy() { alive = false; view.viewer.overlayGroup.remove(board, ink); inkGeo.dispose(); board.geometry.dispose(); [mbuf, jp, jd].forEach((b) => b.delete()); scratch.delete(); view.destroy(); } };
}
