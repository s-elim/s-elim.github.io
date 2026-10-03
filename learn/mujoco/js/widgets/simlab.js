// simlab: the general-purpose lab. A lesson describes an experiment in JSON and
// this module turns it into a running MuJoCo simulation with sliders, a
// controller, plots and readouts.
//
// Config (all fields optional except model):
// {
//   "title": "...", "model": "pendulum", "key": 0, "height": 300, "autoplay": false,
//   "camera": {"azimuth": -90, "elevation": 10, "distance": 2, "target": [0,0,1]},
//   "overlays": {"frames": true, "contacts": true},
//   "toggles": ["frames", "contacts", "forces"],          overlay checkboxes to show
//   "setup": "data.qpos[0] = 1.0",                         JS run after load and after every reset
//   "controls": [
//     {"label": "damping", "unit": "N m s/rad", "set": "model.dof_damping[0]", "min": 0, "max": 1, "value": 0},
//     {"label": "Kp", "param": "kp", "min": 0, "max": 100, "value": 10},       stored as ctx.kp
//     {"label": "initial angle", "set": "data.qpos[0]", "init": true, ...},     re-applied after reset
//     {"type": "select", "label": "integrator", "set": "model.opt.integrator",
//      "options": [["Euler", 0], ["RK4", 1]], "value": 0, "reset": true},
//     {"type": "button", "label": "Kick", "run": "data.qvel[0] += 2"}
//   ],
//   "controller": "data.ctrl[0] = -ctx.kp * data.qpos[0]",  JS run before every mj_step
//   "plots": [{"ylabel": "angle (rad)", "window": 10, "traces": [{"label": "q (rad)", "expr": "data.qpos[0]"}]}],
//   "readouts": [{"label": "energy (J)", "expr": "lib.energy().total", "digits": 4}],
//   "trail": "tip",                                       site whose path is drawn
//   "stopAt": 0.6,                                        pause automatically at this sim time (s)
//   "note": "Shown under the lab."
// }
//
// Expressions see: model, data, sim, mj, ctx (slider params), lib (helpers below).
// They come from the course's own lesson files, never from page visitors.

import { h, frame, slider, select, button, readout, createSimView, overlayToggles, fmt } from "./ui.js";
import { Plot } from "../plot.js";
import { idOf, nameOf } from "../runtime.js";
import { symEig } from "../linalg.js";

const ARGS = ["model", "data", "sim", "mj", "ctx", "lib"];

export function compileExpr(expr) {
  return new Function(...ARGS, `"use strict"; return (${expr});`);
}
export function compileStmt(stmt) {
  return new Function(...ARGS, `"use strict"; ${stmt};`);
}
export function compileSetter(target) {
  return new Function(...ARGS, "value", `"use strict"; ${target} = value;`);
}

export function makeLib(view) {
  let jac = null, mbuf = null;
  const lib = {
    sitePos(name) { const s = view.sim; const i = idOf(s.mj, s.model, "mjOBJ_SITE", name); return [s.data.site_xpos[3 * i], s.data.site_xpos[3 * i + 1], s.data.site_xpos[3 * i + 2]]; },
    bodyPos(name) { const s = view.sim; const i = idOf(s.mj, s.model, "mjOBJ_BODY", name); return [s.data.xpos[3 * i], s.data.xpos[3 * i + 1], s.data.xpos[3 * i + 2]]; },
    bodyId(name) { const s = view.sim; return idOf(s.mj, s.model, "mjOBJ_BODY", name); },
    jointId(name) { const s = view.sim; return idOf(s.mj, s.model, "mjOBJ_JOINT", name); },
    qpos(name) { const s = view.sim; const j = lib.jointId(name); return s.data.qpos[s.model.jnt_qposadr[j]]; },
    energy() { return view.sim.energy(); },
    /** Sum of contact normal forces (N), optionally only those touching `geomName`. */
    normalForce(geomName = null) {
      const s = view.sim;
      const g = geomName ? idOf(s.mj, s.model, "mjOBJ_GEOM", geomName) : -1;
      return s.contacts().reduce((acc, c) => (g < 0 || c.geom1 === g || c.geom2 === g ? acc + c.force[0] : acc), 0);
    },
    /** Site Jacobian as rows [3 translational, 3 rotational] x the first `cols` dofs (default nv). */
    jacobian(siteName, cols = null) {
      const s = view.sim;
      const nv = s.model.nv;
      if (!jac || jac.nv !== nv) { lib.dispose(); jac = { nv, p: new s.mj.DoubleBuffer(3 * nv), r: new s.mj.DoubleBuffer(3 * nv) }; }
      s.mj.mj_jacSite(s.model, s.data, jac.p, jac.r, idOf(s.mj, s.model, "mjOBJ_SITE", siteName));
      const P = Array.from(jac.p.GetView()), R = Array.from(jac.r.GetView());   // copy before the heap can move
      const n = cols ?? nv;
      return [0, 1, 2].map((i) => P.slice(i * nv, i * nv + n)).concat([0, 1, 2].map((i) => R.slice(i * nv, i * nv + n)));
    },
    /** Singular values of a site Jacobian, largest first; rows "pos" uses translation only. */
    jacobianSV(siteName, { cols = null, rows = "full" } = {}) {
      let J = lib.jacobian(siteName, cols);
      if (rows === "pos") J = J.slice(0, 3);
      const A = J.map((a) => J.map((b) => a.reduce((acc, v, k) => acc + v * b[k], 0)));   // J J^T
      return symEig(A).values.map((e) => Math.sqrt(Math.max(e, 0))).sort((x, y) => y - x);
    },
    /** "geomA / geomB" for each active contact (unnamed geoms show their body). */
    contactPairs() {
      const s = view.sim;
      const label = (g) => nameOf(s.mj, s.model, "mjOBJ_GEOM", g) || nameOf(s.mj, s.model, "mjOBJ_BODY", s.model.geom_bodyid[g]);
      return s.contacts().map((c) => `${label(c.geom1)} / ${label(c.geom2)}`);
    },
    /** Dense mass matrix (rows) for the current qpos: runs mj_forward first so that every
     *  readout evaluated after it in the same tick sees one consistent state. */
    massMatrix() {
      const s = view.sim;
      const nv = s.model.nv;
      if (!mbuf || mbuf.n !== nv * nv) { mbuf?.b.delete(); mbuf = { n: nv * nv, b: new s.mj.DoubleBuffer(nv * nv) }; }
      s.mj.mj_forward(s.model, s.data);
      s.mj.mj_fullM(s.model, s.data, mbuf.b);
      const v = Array.from(mbuf.b.GetView());
      return Array.from({ length: nv }, (_, i) => v.slice(i * nv, i * nv + nv));
    },
    dispose() {
      if (jac) { jac.p.delete(); jac.r.delete(); jac = null; }
      if (mbuf) { mbuf.b.delete(); mbuf = null; }
    },
    norm(v) { return Math.hypot(...v); },
    deg: (rad) => rad * 180 / Math.PI,
    rad: (deg) => deg * Math.PI / 180,
  };
  return lib;
}

export async function mount(el, config) {
  const { body } = frame(el, { title: config.title || "", kind: config.kind || "Lab" });
  const ctx = {};
  let view = null;
  const lib = {};
  const apply = [];      // functions re-applied after reset (init controls, setup)
  const plots = [];
  const outs = [];

  view = await createSimView(body, {
    model: config.model, xml: config.xml, key: config.key, height: config.height,
    camera: config.camera, overlays: config.overlays, autoplay: config.autoplay, forceScale: config.forceScale,
    onReset: () => { apply.forEach((fn) => fn()); view?.sim.forward(); plots.forEach((p) => p.plot.clear()); },
    onTick: (s) => {
      if (config.stopAt != null && s.time >= config.stopAt && !s.paused) view?.pause();
      for (const p of plots) {
        const vals = p.fns.map((fn) => { try { return fn(s.model, s.data, s, s.mj, ctx, lib); } catch (e) { return NaN; } });
        p.plot.push(s.time, vals);
        p.plot.draw();
      }
      for (const o of outs) {
        let v;
        try { v = o.fn(s.model, s.data, s, s.mj, ctx, lib); } catch (e) { v = NaN; }
        o.el.set(typeof v === "number" ? fmt(v, o.digits ?? 3) : String(v));
      }
    },
  });
  Object.assign(lib, makeLib(view));
  const call = (fn, value) => { const s = view.sim; return fn(s.model, s.data, s, s.mj, ctx, lib, value); };

  if (config.toggles) body.appendChild(overlayToggles(view.viewer, config.toggles));
  if (config.trail) view.viewer.setTrail(idOf(view.mj, view.sim.model, "mjOBJ_SITE", config.trail));

  const controls = h("div", { class: "controls" });
  for (const c of config.controls || []) {
    if (c.type === "button") {
      const fn = compileStmt(c.run);
      // Consecutive buttons share one toolbar row.
      let bar = controls.lastElementChild;
      if (!bar || !bar.classList.contains("toolbar")) bar = controls.appendChild(h("div", { class: "toolbar" }));
      bar.appendChild(button(c.label, () => { call(fn); view.sim.forward(); }));
      continue;
    }
    // "set": an assignable expression; "apply": statements that read `value`
    // (for changes that need a follow-up call, such as mj_setConst after a mass change).
    const setter = c.set ? compileSetter(c.set) : c.apply ? new Function(...ARGS, "value", `"use strict"; ${c.apply};`) : null;
    const setValue = (v) => {
      const val = typeof c.value === "number" || c.type !== "select" ? Number(v) : v;
      if (c.param) ctx[c.param] = val;
      if (setter) call(setter, val);
      if (c.reset) view.reset(); else view.sim.forward();
    };
    const widget = c.type === "select"
      ? select({ label: c.label, options: c.options, value: c.value, onChange: (v) => setValue(isNaN(+v) ? v : +v) })
      : slider({ label: c.label, unit: c.unit, min: c.min, max: c.max, step: c.step, value: c.value, digits: c.digits ?? 3, onInput: setValue });
    controls.appendChild(widget);
    // Initial application (without reset).
    if (c.param) ctx[c.param] = c.value;
    if (setter) call(setter, c.value);
    if (c.init && setter) apply.push(() => call(setter, widget.get ? (c.type === "select" ? +widget.get() : widget.get()) : c.value));
  }
  if (config.controls?.length) body.appendChild(controls);

  if (config.setup) {
    const fn = compileStmt(config.setup);
    apply.unshift(() => call(fn));
  }
  apply.forEach((fn) => fn());
  view.sim.forward();

  if (config.controller) {
    const fn = compileStmt(config.controller);
    view.sim.controller = (s) => fn(s.model, s.data, s, s.mj, ctx, lib);
  }

  if (config.readouts?.length) {
    const box = h("div", { class: "readouts" });
    for (const r of config.readouts) {
      const el2 = readout(r.label);
      outs.push({ el: el2, fn: compileExpr(r.expr), digits: r.digits });
      box.appendChild(el2);
    }
    body.appendChild(box);
  }
  for (const p of config.plots || []) {
    const holder = h("div");
    body.appendChild(holder);
    const plot = new Plot(holder, { mode: "time", window: p.window || 5, ylabel: p.ylabel, xlabel: p.xlabel || "time (s)", ymin: p.ymin, ymax: p.ymax, refLines: p.refLines, height: p.height || 140, traces: p.traces.map((t) => ({ label: t.label, dash: t.dash })) });
    plots.push({ plot, fns: p.traces.map((t) => compileExpr(t.expr)) });
  }
  if (config.note) body.appendChild(h("p", { class: "widget__note", html: config.note }));

  return {
    view,
    destroy() { plots.forEach((p) => p.plot.dispose()); lib.dispose(); view.destroy(); },
  };
}
