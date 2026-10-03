// frames: a rotation explorer in MuJoCo's conventions.
//
// Euler angles (any MuJoCo sequence, intrinsic lower case or extrinsic upper case)
// or axis-angle in; rotation matrix, quaternion, its double -q, rotation vector and
// the rotated frame out. Every quaternion is computed twice: by the formulas in the
// lesson (in JavaScript) and by MuJoCo's own mju_euler2Quat / mju_axisAngle2Quat
// (WebAssembly), and the angle between the two is displayed.
//
// Config: {"mode": "euler" | "axisangle", "seq": "xyz", "euler": [deg, deg, deg]}

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { h, frame, slider, select, fmt } from "./ui.js";
import { getMujoco } from "../runtime.js";
import { register } from "../loop.js";

const D2R = Math.PI / 180;

// ---- quaternion algebra, (w, x, y, z), the same as mjcourse/spatial.py ----
export function qmul(a, b) {
  return [
    a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3],
    a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
    a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1],
    a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0],
  ];
}
export function axisAngle(axis, angle) {
  const n = Math.hypot(...axis) || 1;
  const s = Math.sin(angle / 2);
  return [Math.cos(angle / 2), (s * axis[0]) / n, (s * axis[1]) / n, (s * axis[2]) / n];
}
export function eulerToQuat(e, seq) {
  const axes = { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1] };
  let q = [1, 0, 0, 0];
  for (let i = 0; i < 3; i++) {
    const c = seq[i];
    const step = axisAngle(axes[c.toLowerCase()], e[i]);
    q = c === c.toLowerCase() ? qmul(q, step) : qmul(step, q);   // intrinsic: post, extrinsic: pre
  }
  return q;
}
export function quatToMat(q) {
  const [w, x, y, z] = q;
  return [
    [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
    [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
    [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
  ];
}
export function geodesic(q1, q2) {
  const rel = qmul([q1[0], -q1[1], -q1[2], -q1[3]], q2);
  return 2 * Math.atan2(Math.hypot(rel[1], rel[2], rel[3]), Math.abs(rel[0]));
}

function axesGroup(len, width, opacity = 1) {
  const g = new THREE.Group();
  const colors = [0xd62728, 0x2ca02c, 0x1f77b4];
  const dirs = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  dirs.forEach((d, i) => {
    const a = new THREE.ArrowHelper(new THREE.Vector3(...d), new THREE.Vector3(), len, colors[i], 0.15 * len, 0.08 * len);
    a.line.material.linewidth = width;
    if (opacity < 1) { a.line.material.transparent = a.cone.material.transparent = true; a.line.material.opacity = a.cone.material.opacity = opacity; }
    g.add(a);
  });
  return g;
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Rotations in MuJoCo's conventions", kind: "Lab" });
  const mj = await getMujoco();
  const qbuf = new mj.DoubleBuffer(4);

  const view = h("div", { class: "viewer", style: { "--viewer-h": `${config.height || 260}px` } });
  body.appendChild(view);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  view.appendChild(renderer.domElement);
  renderer.domElement.className = "viewer-canvas";
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue("--viewer-bg").trim() || "#e9ece8");
  const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 50);
  camera.up.set(0, 0, 1);
  camera.position.set(2.6, -2.0, 1.6);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0, 0);
  scene.add(axesGroup(1.0, 1, 0.25));                       // world frame, faint
  const ghosts = [axesGroup(0.7, 1, 0.35), axesGroup(0.7, 1, 0.35)];
  ghosts.forEach((g) => scene.add(g));
  const body3 = axesGroup(1.2, 3);                          // the rotated frame
  scene.add(body3);
  const box = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.3, 0.12), new THREE.MeshNormalMaterial({ transparent: true, opacity: 0.55 }));
  body3.add(box);
  const axisArrow = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(), 1.4, 0x9467bd);
  scene.add(axisArrow);

  let mode = config.mode || "euler";
  let seq = config.seq || "xyz";
  const e = (config.euler || [30, 45, 0]).map((v) => v * D2R);
  const aa = { axis: [0, 0, 1], angle: 60 * D2R };

  const out = h("div", { class: "readouts" });
  const mkOut = (label) => { const r = h("div", { class: "readout" }, h("span", {}, label), h("b", {}, "-")); out.appendChild(r); return r.querySelector("b"); };
  const oQ = mkOut("quaternion (w, x, y, z)"), oNQ = mkOut("same rotation: -q"), oRV = mkOut("rotation vector (rad)"),
    oAng = mkOut("angle (deg)"), oChk = mkOut("vs MuJoCo (rad)"), oGim = mkOut("gimbal check");
  const matBox = h("div", { class: "matrix", style: { gridTemplateColumns: "repeat(3, auto)" } });

  const controlsBox = h("div", { class: "controls" });
  const rebuild = () => {
    controlsBox.replaceChildren();
    controlsBox.appendChild(select({ label: "input", value: mode, options: [["Euler angles", "euler"], ["axis and angle", "axisangle"]], onChange: (v) => { mode = v; rebuild(); update(); } }));
    if (mode === "euler") {
      controlsBox.appendChild(select({ label: "sequence (lower = intrinsic, upper = extrinsic)", value: seq,
        options: ["xyz", "XYZ", "zyx", "ZYX", "zxz", "ZXZ", "xyx"].map((s) => [s, s]), onChange: (v) => { seq = v; update(); } }));
      [0, 1, 2].forEach((i) => controlsBox.appendChild(slider({ label: `angle ${i + 1} (about ${seq[i]})`, unit: "deg", min: -180, max: 180, step: 1, value: Math.round(e[i] / D2R), digits: 0, onInput: (v) => { e[i] = v * D2R; update(); } })));
    } else {
      ["x", "y", "z"].forEach((c, i) => controlsBox.appendChild(slider({ label: `axis ${c}`, min: -1, max: 1, step: 0.01, value: aa.axis[i], digits: 2, onInput: (v) => { aa.axis[i] = v; update(); } })));
      controlsBox.appendChild(slider({ label: "angle", unit: "deg", min: -360, max: 360, step: 1, value: Math.round(aa.angle / D2R), digits: 0, onInput: (v) => { aa.angle = v * D2R; update(); } }));
    }
  };

  const setFrom = (obj, q) => obj.quaternion.set(q[1], q[2], q[3], q[0]);  // three.js order is (x, y, z, w)

  const update = () => {
    let q, ref;
    if (mode === "euler") {
      q = eulerToQuat(e, seq);
      mj.mju_euler2Quat(qbuf, [e[0], e[1], e[2]], seq);
      ref = Array.from(qbuf.GetView());
      // Partial rotations: after the first and after the second elementary rotation.
      const q1 = eulerToQuat([e[0], 0, 0], seq), q2 = eulerToQuat([e[0], e[1], 0], seq);
      setFrom(ghosts[0], q1); setFrom(ghosts[1], q2);
      ghosts.forEach((g) => { g.visible = true; });
      axisArrow.visible = false;
      const first = seq[0].toLowerCase(), last = seq[2].toLowerCase();
      const proper = first === last;                         // e.g. zxz: lock at middle = 0 or 180
      const lock = proper ? Math.abs(Math.sin(e[1])) < 0.02 : Math.abs(Math.cos(e[1])) < 0.02;
      oGim.textContent = lock ? `LOCK: angles 1 and 3 act about the same axis` : `ok (lock at angle 2 = ${proper ? "0 or 180" : "+-90"} deg)`;
    } else {
      q = axisAngle(aa.axis, aa.angle);
      const n = Math.hypot(...aa.axis) || 1;
      mj.mju_axisAngle2Quat(qbuf, aa.axis.map((v) => v / n), aa.angle);
      ref = Array.from(qbuf.GetView());
      ghosts.forEach((g) => { g.visible = false; });
      axisArrow.visible = true;
      axisArrow.setDirection(new THREE.Vector3(...aa.axis.map((v) => v / n)));
      oGim.textContent = "axis-angle has no gimbal lock";
    }
    setFrom(body3, q);
    const R = quatToMat(q);
    matBox.replaceChildren(...R.flat().map((v) => h("span", {}, fmt(Math.abs(v) < 1e-12 ? 0 : v, 3))));
    oQ.textContent = q.map((v) => fmt(v, 3)).join(", ");
    oNQ.textContent = q.map((v) => fmt(-v, 3)).join(", ");
    const s = Math.hypot(q[1], q[2], q[3]);
    const qq = q[0] < 0 ? q.map((v) => -v) : q;
    const ang = 2 * Math.atan2(s, Math.abs(q[0]));
    oRV.textContent = s < 1e-12 ? "0, 0, 0" : [1, 2, 3].map((k) => fmt((ang * qq[k]) / s, 3)).join(", ");
    oAng.textContent = fmt(ang / D2R, 2);
    oChk.textContent = fmt(geodesic(q, ref), 2);
  };

  rebuild();
  body.append(controlsBox, h("div", { class: "toolbar" }, h("span", { class: "chip" }, "rotation matrix (columns: body x, y, z in world)"), matBox), out,
    h("p", { class: "widget__note", html: config.note || "Faint arrows: the world frame. Thin arrows (Euler mode): the frame after the first and after the second elementary rotation. Thick arrows and the box: the final frame. 'vs MuJoCo' is the angle between this page's quaternion and the one MuJoCo's own function returns." }));
  update();

  const unregister = register(view, () => {
    const w = view.clientWidth, hgt = view.clientHeight;
    if (w && hgt) { renderer.setSize(w, hgt, false); camera.aspect = w / hgt; camera.updateProjectionMatrix(); }
    controls.update();
    renderer.render(scene, camera);
  });
  return { destroy() { unregister(); controls.dispose(); renderer.dispose(); qbuf.delete(); } };
}
