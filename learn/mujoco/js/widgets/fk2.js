// fk2: the planar two-link arm (arm2.xml) drawn in its own x-z plane, with the
// hand calculation beside MuJoCo's numbers for the same pose.
//
// Layers: joint frames, the two Jacobian columns as tip-velocity arrows, the
// velocity manipulability ellipse {J qdot : |qdot| = 1}, and the reachable
// workspace sampled over the joint ranges.
//
// Config: {"title": "...", "q": [0.6, -1.2], "height": 300,
//          "layers": ["frames", "jacobian", "ellipse", "workspace"],   initially visible
//          "table": "fk" | "jacobian"}                                  which comparison to print
//
// MuJoCo supplies site_xpos and mj_jacSite; the widget calls mj_kinematics and
// mj_comPos first, because a Jacobian needs both (Lesson 6.1).

import { h, frame, slider, fmt } from "./ui.js";
import { getMujoco, loadModel, idOf } from "../runtime.js";

const L1 = 0.5, L2 = 0.4;                   // arm2.xml link lengths (m)
const SHOULDER = [0, 1.0];                  // shoulder axis in world (x, z)
const ARROW_SCALE = 0.4;                    // drawn metres per (m/s per rad/s)
const C = { x: "#D55E00", z: "#0072B2", col1: "#009E73", col2: "#CC79A7", ellipse: "#E69F00" };   // Okabe-Ito

/** Singular values (largest first) of a 2x2 matrix and the direction of the major axis of J J^T. */
function svd2(J) {
  const a = J[0][0] ** 2 + J[0][1] ** 2, d = J[1][0] ** 2 + J[1][1] ** 2, b = J[0][0] * J[1][0] + J[0][1] * J[1][1];
  const mean = (a + d) / 2, rad = Math.hypot((a - d) / 2, b);
  return { sigma: [Math.sqrt(mean + rad), Math.sqrt(Math.max(mean - rad, 0))], angle: 0.5 * Math.atan2(2 * b, a - d) };
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Two-link forward kinematics", kind: "Lab" });
  const mj = await getMujoco();
  const model = await loadModel("arm2");
  const data = new mj.MjData(model);
  const site = idOf(mj, model, "mjOBJ_SITE", "ee");
  const jacp = new mj.DoubleBuffer(3 * model.nv);
  const range = [0, 1].map((j) => [model.jnt_range[2 * j], model.jnt_range[2 * j + 1]]);
  const q = (config.q || [0.6, -1.2]).slice();
  const layers = new Set(config.layers || ["frames", "jacobian", "ellipse"]);

  const canvas = h("canvas", { class: "fk2__canvas", style: { width: "100%", height: `${config.height || 300}px`, display: "block", background: "var(--viewer-bg)", borderRadius: "8px" } });
  const controls = h("div", { class: "controls" });
  const sliders = [0, 1].map((j) => slider({
    label: j ? "elbow q2" : "shoulder q1", unit: "rad", min: range[j][0], max: range[j][1], step: 0.005, value: q[j], digits: 3,
    onInput: (v) => { q[j] = v; update(); },
  }));
  sliders.forEach((s) => controls.appendChild(s));
  const toggles = h("div", { class: "toggles" }, ["frames", "jacobian", "ellipse", "workspace"].map((k) => {
    const cb = h("input", { type: "checkbox", checked: layers.has(k) ? true : null });
    cb.addEventListener("change", () => { cb.checked ? layers.add(k) : layers.delete(k); draw(); });
    return h("label", {}, cb, { frames: "joint frames", jacobian: "Jacobian columns", ellipse: "manipulability ellipse", workspace: "workspace" }[k]);
  }));
  const table = h("table", { class: "fk2__table" });
  body.append(canvas, toggles, controls, h("div", { class: "arrays" }, table));

  // Workspace: tip positions over a grid of joint angles inside the ranges.
  const workspace = [];
  for (let i = 0; i <= 70; i++) {
    for (let k = 0; k <= 70; k++) {
      const a = range[0][0] + (range[0][1] - range[0][0]) * i / 70;
      const b = range[1][0] + (range[1][1] - range[1][0]) * k / 70;
      workspace.push([L1 * Math.cos(a) + L2 * Math.cos(a + b), L1 * Math.sin(a) + L2 * Math.sin(a + b)]);
    }
  }

  let state = null;
  function compute() {
    data.qpos[0] = q[0];
    data.qpos[1] = q[1];
    mj.mj_kinematics(model, data);
    mj.mj_comPos(model, data);
    mj.mj_jacSite(model, data, jacp, null, site);
    const J = Array.from(jacp.GetView());           // 3 x nv, row-major; rows x, y, z
    const nv = model.nv;
    const s1 = Math.sin(q[0]), c1 = Math.cos(q[0]), s12 = Math.sin(q[0] + q[1]), c12 = Math.cos(q[0] + q[1]);
    const hand = { x: L1 * c1 + L2 * c12, z: L1 * s1 + L2 * s12 };
    const Jh = [[-L1 * s1 - L2 * s12, -L2 * s12], [L1 * c1 + L2 * c12, L2 * c12]];
    const Jm = [[J[0], J[1]], [J[2 * nv], J[2 * nv + 1]]];
    const mjTip = { x: data.site_xpos[3 * site] - SHOULDER[0], z: data.site_xpos[3 * site + 2] - SHOULDER[1] };
    const elbow = { x: L1 * c1, z: L1 * s1 };
    const sv = svd2(Jh);
    const det = Jh[0][0] * Jh[1][1] - Jh[0][1] * Jh[1][0];
    const detM = Jm[0][0] * Jm[1][1] - Jm[0][1] * Jm[1][0];
    state = { hand, mjTip, elbow, Jh, Jm, sigma: sv.sigma, sigmaM: svd2(Jm).sigma, angle: sv.angle, det, detM };
  }

  function fill() {
    const s = state;
    const row = (cells, head = false) => h("tr", {}, cells.map((c) => h(head ? "th" : "td", {}, c)));
    table.replaceChildren();
    if ((config.table || "fk") === "fk") {
      table.append(
        row(["", "x (m)", "z (m)"], true),
        row(["hand formula", fmt(s.hand.x, 6), fmt(s.hand.z, 6)]),
        row(["MuJoCo site_xpos", fmt(s.mjTip.x, 6), fmt(s.mjTip.z, 6)]),
        row(["difference", fmt(s.hand.x - s.mjTip.x, 2), fmt(s.hand.z - s.mjTip.z, 2)]));
    } else {
      const f = (v) => fmt(v, 5);
      table.append(
        row(["", "hand", "mj_jacSite"], true),
        row(["∂x/∂q1", f(s.Jh[0][0]), f(s.Jm[0][0])]),
        row(["∂x/∂q2", f(s.Jh[0][1]), f(s.Jm[0][1])]),
        row(["∂z/∂q1", f(s.Jh[1][0]), f(s.Jm[1][0])]),
        row(["∂z/∂q2", f(s.Jh[1][1]), f(s.Jm[1][1])]),
        row(["det J", f(L1 * L2 * Math.sin(q[1])), f(s.detM)]),
        row(["σ1, σ2", `${fmt(s.sigma[0], 4)}, ${fmt(s.sigma[1], 4)}`, `${fmt(s.sigmaM[0], 4)}, ${fmt(s.sigmaM[1], 4)}`]));
    }
  }

  function draw() {
    const s = state;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = canvas.clientWidth, hgt = canvas.clientHeight;
    if (!w) return;
    canvas.width = w * dpr;
    canvas.height = hgt * dpr;
    const g = canvas.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, hgt);
    const css = getComputedStyle(canvas);
    const ink = css.getPropertyValue("--ink").trim() || "#16211f";
    const ink2 = css.getPropertyValue("--ink-2").trim() || "#4c5b57";
    const ink3 = css.getPropertyValue("--ink-3").trim() || "#78877f";
    const scale = Math.min(w, hgt) / 2.15;
    const P = (x, z) => [w / 2 + x * scale, hgt / 2 - z * scale];   // shoulder at the centre

    if (layers.has("workspace")) {
      g.fillStyle = ink3;
      g.globalAlpha = 0.25;
      for (const [x, z] of workspace) { const [u, v] = P(x, z); g.fillRect(u - 0.8, v - 0.8, 1.6, 1.6); }
      g.globalAlpha = 1;
    }
    // Ground line and pedestal for orientation (the floor is 1 m below the shoulder).
    g.strokeStyle = ink3; g.lineWidth = 1;
    g.beginPath(); g.moveTo(...P(-1.05, -1.0)); g.lineTo(...P(1.05, -1.0)); g.stroke();
    g.lineWidth = 6; g.strokeStyle = ink3; g.globalAlpha = 0.5;
    g.beginPath(); g.moveTo(...P(0, -1.0)); g.lineTo(...P(0, -0.03)); g.stroke(); g.globalAlpha = 1;

    const line = (a, b, color, width) => { g.strokeStyle = color; g.lineWidth = width; g.lineCap = "round"; g.beginPath(); g.moveTo(...P(a.x, a.z)); g.lineTo(...P(b.x, b.z)); g.stroke(); };
    const arrow = (from, vx, vz, color, label) => {
      const to = { x: from.x + vx * ARROW_SCALE, z: from.z + vz * ARROW_SCALE };
      line(from, to, color, 2.5);
      const [u, v] = P(to.x, to.z), [u0, v0] = P(from.x, from.z);
      const ang = Math.atan2(v - v0, u - u0);
      g.fillStyle = color; g.beginPath(); g.moveTo(u, v);
      g.lineTo(u - 9 * Math.cos(ang - 0.4), v - 9 * Math.sin(ang - 0.4));
      g.lineTo(u - 9 * Math.cos(ang + 0.4), v - 9 * Math.sin(ang + 0.4)); g.closePath(); g.fill();
      if (label) { g.font = "12px var(--mono), monospace"; g.fillText(label, u + 6, v - 6); }
    };
    const origin = { x: 0, z: 0 };
    line(origin, s.elbow, ink2, 7);
    line(s.elbow, s.hand, ink2, 5);
    for (const p of [origin, s.elbow]) { const [u, v] = P(p.x, p.z); g.fillStyle = ink; g.beginPath(); g.arc(u, v, 5, 0, 2 * Math.PI); g.fill(); }

    if (layers.has("frames")) {
      // Each frame's x axis points along its link; z is x rotated by +90 degrees in the drawing plane.
      const frames = [[origin, q[0]], [s.elbow, q[0] + q[1]], [s.hand, q[0] + q[1]]];
      for (const [p, th] of frames) {
        const ax = 0.12;
        line(p, { x: p.x + ax * Math.cos(th), z: p.z + ax * Math.sin(th) }, C.x, 2);
        line(p, { x: p.x - ax * Math.sin(th), z: p.z + ax * Math.cos(th) }, C.z, 2);
      }
    }
    if (layers.has("ellipse")) {
      const [u, v] = P(s.hand.x, s.hand.z);
      g.strokeStyle = C.ellipse; g.lineWidth = 2; g.setLineDash([5, 4]);
      g.beginPath();
      g.ellipse(u, v, Math.max(s.sigma[0] * ARROW_SCALE * scale, 0.5), Math.max(s.sigma[1] * ARROW_SCALE * scale, 0.5), -s.angle, 0, 2 * Math.PI);
      g.stroke(); g.setLineDash([]);
    }
    if (layers.has("jacobian")) {
      arrow(s.hand, s.Jh[0][0], s.Jh[1][0], C.col1, "∂p/∂q1");
      arrow(s.hand, s.Jh[0][1], s.Jh[1][1], C.col2, "∂p/∂q2");
    }
    const [u, v] = P(s.hand.x, s.hand.z);
    g.fillStyle = ink; g.beginPath(); g.arc(u, v, 5, 0, 2 * Math.PI); g.fill();
    g.fillStyle = ink3; g.font = "11px var(--mono), monospace";
    g.fillText(`arrows and ellipse: ${ARROW_SCALE} m per (m/s per rad/s)`, 10, 16);
  }

  function update() { compute(); fill(); draw(); }
  const ro = new ResizeObserver(() => draw());
  ro.observe(canvas);
  update();

  return {
    destroy() { ro.disconnect(); jacp.delete(); data.delete(); model.delete(); },
  };
}
