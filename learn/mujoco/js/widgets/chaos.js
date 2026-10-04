// chaos: two double pendulums on one pivot, the second released eps rad away from the first (Showcase).
// The plot shows log10 of the gap between their joint angles and the growth predicted by the largest
// Lyapunov exponent measured in examples/showcase_chaos.py (2.65 per second, RK4 at 1 ms). Tip trails show
// the moment the twins part. The integrator applies to both: with Euler the pendulums lose energy and the
// motion itself changes, not only its details.
//
// Config: {"title": "...", "height": 300}

import * as THREE from "three";
import { h, frame, slider, select, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";

const LAMBDA = 2.65;                       // per second, from examples/showcase_chaos.py

function arm(prefix, rgba1, rgba2) {
  return `
    <body name="${prefix}1" pos="0 0 1">
      <joint name="${prefix}j1"/>
      <inertial pos="0 0 -0.3" mass="1.0" diaginertia="1e-4 1e-4 1e-4"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.012" rgba="${rgba1}"/>
      <geom type="sphere" pos="0 0 -0.3" size="0.03" rgba="${rgba1}"/>
      <body name="${prefix}2" pos="0 0 -0.3">
        <joint name="${prefix}j2"/>
        <inertial pos="0 0 -0.3" mass="1.0" diaginertia="1e-4 1e-4 1e-4"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.012" rgba="${rgba2}"/>
        <geom type="sphere" pos="0 0 -0.3" size="0.03" rgba="${rgba2}"/>
        <site name="${prefix}tip" pos="0 0 -0.3" size="0.005"/>
      </body>
    </body>`;
}
const XML = `
<mujoco model="chaos_twins">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.001" integrator="RK4">
    <flag energy="enable"/>
  </option>
  <visual><headlight diffuse=".6 .6 .6"/></visual>
  <default>
    <joint type="hinge" axis="0 1 0" damping="0"/>
    <geom contype="0" conaffinity="0"/>
  </default>
  <worldbody>
    <light pos="0 -1 2" dir="0 1 -2"/>
    <geom type="box" size="0.03 0.03 0.03" pos="0 0.02 1" rgba=".3 .3 .3 1"/>
    ${arm("a", ".85 .33 .1 1", ".85 .33 .1 1")}
    ${arm("b", ".0 .45 .70 .75", ".0 .45 .70 .75")}
  </worldbody>
</mujoco>`;

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Twins, 1e-9 rad apart", kind: "Lab" });
  const view = await createSimView(body, { xml: XML, height: config.height || 300, toolbar: false,
    camera: { azimuth: 90, elevation: 0, distance: 2.1, target: [0, 0, 0.75] } });
  const sim = view.sim, { mj, model, data } = sim;
  const tipA = mj.mj_name2id(model, mj.mjtObj.mjOBJ_SITE.value, "atip"), tipB = mj.mj_name2id(model, mj.mjtObj.mjOBJ_SITE.value, "btip");
  const opt = { exponent: -9, integrator: "RK4,0.001" };
  let e0 = 0, parted = null;

  const lines = [0xd55e00, 0x0072b2].map((color) => {
    const geo = new THREE.BufferGeometry(), line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.7 }));
    line.frustumCulled = false; view.viewer.overlayGroup.add(line);
    return { geo, line, pts: [] };
  });

  const plotEl = h("div");
  const plot = new Plot(plotEl, { mode: "time", window: 14, xlabel: "time (s)", ylabel: "log10 gap (rad)", height: 150, ymin: -13, ymax: 1,
    traces: [{ label: "log10 of the largest joint-angle gap" }, { label: "predicted: log10 eps + 2.65 t / ln 10", dash: true }] });
  const outs = { gap: readout("joint-angle gap (rad)"), parted: readout("gap passed 0.1 rad at"), pred: readout("predicted ln(0.1/eps) / lambda"), energy: readout("energy change") };

  const wrap = (x) => Math.atan2(Math.sin(x), Math.cos(x));
  function release() {
    const [name, dt] = opt.integrator.split(",");
    model.opt.integrator = { Euler: mj.mjtIntegrator.mjINT_EULER.value, RK4: mj.mjtIntegrator.mjINT_RK4.value }[name];
    model.opt.timestep = Number(dt);
    mj.mj_resetData(model, data);
    const eps = 10 ** opt.exponent;
    data.qpos.set([2.0, 0.5, 2.0 + eps, 0.5]);
    mj.mj_forward(model, data);
    e0 = data.energy[0] + data.energy[1];
    parted = null;
    lines.forEach((l) => { l.pts = []; l.geo.setAttribute("position", new THREE.Float32BufferAttribute([], 3)); });
    plot.clear();
    outs.pred.set(`${fmt(Math.log(0.1 / eps) / LAMBDA, 2)} s`);
    outs.parted.set("-");
    view.play();
  }

  let alive = true, lastT = -1;
  const tick = () => {
    if (!alive) return;
    if (data.time !== lastT) {
      lastT = data.time;
      const gap = Math.max(Math.abs(wrap(data.qpos[2] - data.qpos[0])), Math.abs(wrap(data.qpos[3] - data.qpos[1])));
      const lg = Math.log10(Math.max(gap, 1e-16));
      plot.push(data.time, [lg, opt.exponent + LAMBDA * data.time / Math.LN10]); plot.draw();
      if (parted === null && gap > 0.1) { parted = data.time; outs.parted.set(`${fmt(parted, 2)} s`); }
      outs.gap.set(gap.toExponential(2));
      outs.energy.set(`${fmt(100 * ((data.energy[0] + data.energy[1]) - e0) / Math.abs(e0), 3)} %`);
      [tipA, tipB].forEach((s, i) => {
        const l = lines[i];
        l.pts.push(data.site_xpos[3 * s], data.site_xpos[3 * s + 1], data.site_xpos[3 * s + 2]);
        if (l.pts.length > 3 * 900) l.pts.splice(0, 3);
        l.geo.setAttribute("position", new THREE.Float32BufferAttribute(l.pts, 3));
      });
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  body.append(
    h("div", { class: "toolbar" }, button("Release the twins", release, "btn btn--primary"), button("Pause / play", () => view.toggle())),
    h("div", { class: "controls" },
      slider({ label: "initial gap, log10 (rad)", min: -12, max: -1, step: 1, value: opt.exponent, digits: 0, onInput: (v) => { opt.exponent = v; } }),
      select({ label: "integrator", options: [["RK4, 1 ms", "RK4,0.001"], ["RK4, 2 ms", "RK4,0.002"], ["Euler, 2 ms", "Euler,0.002"]], value: opt.integrator, onChange: (v) => { opt.integrator = v; } })),
    h("div", { class: "readouts" }, Object.values(outs)), plotEl,
    h("p", { class: "widget__note", html: "Changes apply at the next release. The orange pendulum starts at (2.0, 0.5) rad; the blue one is 10<sup>k</sup> rad further in its first joint. The dashed line is the growth predicted from the Lyapunov exponent measured in Python; the gap follows it until it is too large to grow." }));
  release();

  return { destroy() { alive = false; lines.forEach((l) => { view.viewer.overlayGroup.remove(l.line); l.geo.dispose(); }); plot.dispose(); view.destroy(); } };
}
