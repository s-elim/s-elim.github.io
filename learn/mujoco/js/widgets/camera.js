// camera: what a model camera sees, and where the pinhole model says things should be.
// The image comes from the course viewer's renderCamera (three.js, same fovy, aspect and
// pose as MuJoCo's camera; RGB, metric depth along the optical axis, or geom ids). Each
// cube's centre is projected with K and the extrinsics under the chosen projection model
// and compared with the centroid of the cube's segmentation mask. In depth mode the red
// cube's mask pixels are back-projected to a point cloud in the world frame.
//
// Config: {"title": "...", "height": 260, "mode": "rgb" | "depth" | "seg"}

import { h, frame, select, readout, createSimView, fmt } from "./ui.js";
import { idOf, nameOf } from "../runtime.js";

const CUBES = [["red_cube", "#d62728"], ["green_cube", "#2ca02c"], ["blue_cube", "#1f77b4"]];
const SIZES = { "320x240": [320, 240], "240x240": [240, 240], "160x120": [160, 120] };

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "A camera, its image and the pinhole model", kind: "Lab" });
  const view = await createSimView(body, {
    model: "pick_place", key: 1, height: config.height || 260, overlays: { cameras: true },
    camera: config.camera || { azimuth: -150, elevation: 28, distance: 2.4, target: [0.5, 0, 0.2] },
  });
  const sim = view.sim;
  const { mj, model, data } = sim;
  const cams = [...Array(model.ncam)].map((_, i) => [nameOf(mj, model, "mjOBJ_CAMERA", i), String(i)]);
  const cubeGeoms = CUBES.map(([n]) => idOf(mj, model, "mjOBJ_GEOM", n));
  const cubeBodies = CUBES.map(([n]) => idOf(mj, model, "mjOBJ_BODY", n));
  const opt = { cam: 0, size: "320x240", mode: config.mode || "rgb", model: "correct" };

  const canvas = h("canvas", { class: "camera-image", style: { width: "100%", maxWidth: "640px", imageRendering: "pixelated", display: "block", margin: "8px auto" } });
  const ctx = canvas.getContext("2d");
  const outs = {
    k: readout("K: f, cx, cy (px)"), fov: readout("field of view x, y (deg)"),
    red: readout("red: projected vs mask centroid (px)"), green: readout("green (px)"), blue: readout("blue (px)"),
    cloud: readout("red point cloud: centroid minus true centre (mm)"),
  };

  /** Intrinsics for a fovy camera at the chosen image size. */
  function intrinsics(cam, W, H) {
    const fovy = model.cam_fovy[cam] * Math.PI / 180;
    const f = 0.5 * H / Math.tan(fovy / 2);
    return { fx: f, fy: f, cx: W / 2, cy: H / 2 };
  }

  /** World point -> pixel under the selected projection model. */
  function project(cam, W, H, p) {
    const K = intrinsics(cam, W, H);
    if (opt.model === "hfov") { K.fx = K.fy = 0.5 * W / Math.tan(model.cam_fovy[cam] * Math.PI / 360); }
    const R = Array.from(data.cam_xmat.slice(9 * cam, 9 * cam + 9)), t = Array.from(data.cam_xpos.slice(3 * cam, 3 * cam + 3));
    const d = [p[0] - t[0], p[1] - t[1], p[2] - t[2]];
    // camera-frame coordinates: columns of R are the camera axes in the world (MuJoCo convention)
    let x = R[0] * d[0] + R[3] * d[1] + R[6] * d[2];
    let y = R[1] * d[0] + R[4] * d[1] + R[7] * d[2];
    let z = R[2] * d[0] + R[5] * d[1] + R[8] * d[2];
    if (opt.model === "notranspose") {
      x = R[0] * d[0] + R[1] * d[1] + R[2] * d[2];
      y = R[3] * d[0] + R[4] * d[1] + R[5] * d[2];
      z = R[6] * d[0] + R[7] * d[1] + R[8] * d[2];
    }
    if (opt.model !== "noflip") { y = -y; z = -z; }                 // to OpenCV: x right, y down, z forward
    return [K.cx + K.fx * x / z, K.cy + K.fy * y / z, z];
  }

  let busy = false, frameCount = 0;
  function update() {
    if (busy) return;
    busy = true;
    view.viewer.update();                                          // mesh poses from the current state
    const cam = Number(opt.cam), [W, H] = SIZES[opt.size];
    canvas.width = W; canvas.height = H;
    const seg = view.viewer.renderCamera(cam, { width: W, height: H, mode: "seg" });
    const depth = view.viewer.renderCamera(cam, { width: W, height: H, mode: "depth" });
    let img;
    if (opt.mode === "rgb") img = new ImageData(view.viewer.renderCamera(cam, { width: W, height: H, mode: "rgb" }), W, H);
    else {
      img = new ImageData(W, H);
      let lo = Infinity, hi = 0;
      if (opt.mode === "depth") for (const v of depth) if (Number.isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
      for (let i = 0; i < W * H; i++) {
        let r = 0, g = 0, b = 0;
        if (opt.mode === "depth") {
          if (Number.isFinite(depth[i])) { const s = 1 - (depth[i] - lo) / Math.max(hi - lo, 1e-9); r = 40 + 200 * s; g = 60 + 180 * s; b = 120 + 100 * s; }
        } else if (seg[i] >= 0) {
          const k = cubeGeoms.indexOf(seg[i]);
          if (k >= 0) [r, g, b] = [[214, 39, 40], [44, 160, 44], [31, 119, 180]][k];
          else { const hsh = (seg[i] * 2654435761) >>> 0; r = 90 + (hsh & 63); g = 90 + ((hsh >> 6) & 63); b = 90 + ((hsh >> 12) & 63); }
        }
        img.data.set([r, g, b, 255], 4 * i);
      }
    }
    ctx.putImageData(img, 0, 0);

    const K = intrinsics(cam, W, H);
    outs.k.set(`${fmt(K.fx, 1)}, ${fmt(K.cx, 1)}, ${fmt(K.cy, 1)}`);
    outs.fov.set(`${fmt(2 * Math.atan(W / 2 / K.fx) * 180 / Math.PI, 1)}, ${fmt(model.cam_fovy[cam], 1)}`);
    const keys = ["red", "green", "blue"];
    CUBES.forEach(([, colour], k) => {
      let su = 0, sv = 0, n = 0;
      for (let i = 0; i < W * H; i++) if (seg[i] === cubeGeoms[k]) { su += (i % W) + 0.5; sv += Math.floor(i / W) + 0.5; n++; }
      const c = Array.from(data.xpos.slice(3 * cubeBodies[k], 3 * cubeBodies[k] + 3));
      const [u, v, z] = project(cam, W, H, c);
      const visible = z > 0 && u >= 0 && u < W && v >= 0 && v < H;
      ctx.strokeStyle = colour; ctx.lineWidth = 1;
      if (visible) {                                               // projected centre: cross
        ctx.beginPath(); ctx.moveTo(u - 5, v); ctx.lineTo(u + 5, v); ctx.moveTo(u, v - 5); ctx.lineTo(u, v + 5); ctx.stroke();
      }
      if (n) {                                                     // mask centroid: circle
        const mu = su / n, mv = sv / n;
        ctx.strokeStyle = "#ffffff"; ctx.beginPath(); ctx.arc(mu, mv, 3, 0, 2 * Math.PI); ctx.stroke();
        outs[keys[k]].set(visible ? `${fmt(Math.hypot(u - mu, v - mv), 2)} (${n} px)` : "projects outside the image");
      } else outs[keys[k]].set(visible ? "projected, but no mask (occluded?)" : "not visible");
    });

    // Point cloud of the red cube from depth (always with the correct model).
    const R = Array.from(data.cam_xmat.slice(9 * cam, 9 * cam + 9)), t = Array.from(data.cam_xpos.slice(3 * cam, 3 * cam + 3));
    let sx = 0, sy = 0, sz = 0, m = 0;
    for (let i = 0; i < W * H; i++) {
      if (seg[i] !== cubeGeoms[0] || !Number.isFinite(depth[i])) continue;
      const u = (i % W) + 0.5, v = Math.floor(i / W) + 0.5, z = depth[i];
      const xc = (u - K.cx) * z / K.fx, yc = (v - K.cy) * z / K.fy;          // OpenCV camera frame
      const pm = [xc, -yc, -z];                                               // MuJoCo camera frame
      sx += t[0] + R[0] * pm[0] + R[1] * pm[1] + R[2] * pm[2];
      sy += t[1] + R[3] * pm[0] + R[4] * pm[1] + R[5] * pm[2];
      sz += t[2] + R[6] * pm[0] + R[7] * pm[1] + R[8] * pm[2];
      m++;
    }
    const c = Array.from(data.xpos.slice(3 * cubeBodies[0], 3 * cubeBodies[0] + 3));
    outs.cloud.set(m ? `${[sx / m - c[0], sy / m - c[1], sz / m - c[2]].map((v) => fmt(1000 * v, 1)).join(", ")} (${m} points)` : "red cube not visible");
    busy = false;
  }

  sim.recorders.add(() => { if (++frameCount % 50 === 0) requestAnimationFrame(update); });
  const rerender = () => requestAnimationFrame(update);
  view.toolbar.after(h("div", { class: "controls" },
    select({ label: "camera", options: cams, value: "0", onChange: (v) => { opt.cam = v; rerender(); } }),
    select({ label: "image size", options: Object.keys(SIZES).map((k) => [k.replace("x", " x "), k]), value: opt.size, onChange: (v) => { opt.size = v; rerender(); } }),
    select({ label: "image", options: [["RGB", "rgb"], ["depth", "depth"], ["segmentation", "seg"]], value: opt.mode, onChange: (v) => { opt.mode = v; rerender(); } }),
    select({ label: "projection model", options: [["correct", "correct"], ["fovy taken as horizontal", "hfov"], ["MuJoCo axes as OpenCV axes", "noflip"], ["cam_xmat not transposed", "notranspose"]], value: "correct", onChange: (v) => { opt.model = v; rerender(); } })),
  canvas, h("div", { class: "readouts" }, Object.values(outs)),
  h("p", { class: "widget__note", html: "Crosses: cube centres projected with the selected model. White circles: centroids of the cubes' segmentation masks. Move a cube with ctrl+drag in the 3-D view (press Play first) and the image updates. This image is the course's three.js re-rendering of MuJoCo's camera; the lesson's script measures the same quantities with <code>mujoco.Renderer</code>." }));
  rerender();
  const off = sim.on((s, event) => { if (event === "reset") rerender(); });

  return { destroy() { off(); view.destroy(); } };
}
