// Small DOM helpers shared by every lab, plus SimView: a Sim, a Viewer and the
// standard transport controls wired to the page's animation loop.

import { loadModel, compileXml, getMujoco } from "../runtime.js";
import { Sim } from "../sim.js";
import { register } from "../loop.js";
import { protectMath, restoreMath } from "../mdcore.js";

/** Typeset $...$ and $$...$$ in an HTML string from a widget config (quiz text,
 *  debug cases). KaTeX is already loaded by the page renderer before any widget mounts. */
export function mathHtml(s) {
  const katex = window.katex;
  if (!katex || typeof s !== "string" || !s.includes("$")) return s;
  const { text, math } = protectMath(s);
  return restoreMath(text, math, (tex, display) =>
    katex.renderToString(tex, { displayMode: display, throwOnError: false, strict: "ignore" }));
}

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = mathHtml(v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

/** Standard widget frame: header with kind and title, body. */
export function frame(el, { title = "", kind = "Lab" } = {}) {
  el.innerHTML = "";
  const body = h("div", { class: "widget__body" });
  const head = h("div", { class: "widget__head" },
    h("span", { class: "widget__kind" }, kind),
    h("h3", { class: "widget__title" }, title),
    h("span", { class: "spacer" }));
  const box = h("div", { class: "widget" }, head, body);
  el.appendChild(box);
  return { box, head, body };
}

export function fmt(v, digits = 3) {
  if (v == null || Number.isNaN(v)) return "nan";
  if (!Number.isFinite(v)) return v > 0 ? "inf" : "-inf";
  const a = Math.abs(v);
  if (a !== 0 && (a < 1e-3 || a >= 1e5)) return v.toExponential(2);
  return v.toFixed(digits);
}

/** A labelled range slider. onInput(value) fires on every change. */
export function slider({ label, min, max, step = (max - min) / 100, value, unit = "", digits = 3, onInput }) {
  const id = `s${Math.random().toString(36).slice(2, 9)}`;
  const out = h("output", { for: id }, fmt(value, digits));
  const input = h("input", { type: "range", id, min, max, step, value });
  input.addEventListener("input", () => {
    const v = parseFloat(input.value);
    out.textContent = fmt(v, digits);
    onInput?.(v);
  });
  const row = h("div", { class: "control" }, h("label", { for: id }, label + (unit ? ` (${unit})` : "")), input, out);
  row.set = (v) => { input.value = v; out.textContent = fmt(v, digits); };
  row.get = () => parseFloat(input.value);
  return row;
}

export function select({ label, options, value, onChange }) {
  const id = `s${Math.random().toString(36).slice(2, 9)}`;
  const sel = h("select", { id }, options.map(([text, v]) => h("option", { value: v, selected: String(v) === String(value) ? true : null }, text)));
  sel.addEventListener("change", () => onChange?.(sel.value));
  const row = h("div", { class: "control" }, h("label", { for: id }, label), sel);
  row.get = () => sel.value;
  return row;
}

export function button(label, onClick, cls = "btn") {
  return h("button", { type: "button", class: cls, onclick: onClick }, label);
}

export function readout(label) {
  const b = h("b", {}, "-");
  const el = h("div", { class: "readout" }, h("span", {}, label), b);
  el.set = (text) => { b.textContent = text; };
  return el;
}

const ICONS = {
  play: '<svg viewBox="0 0 16 16"><path d="M4 2.5v11l9-5.5z"/></svg>',
  pause: '<svg viewBox="0 0 16 16"><path d="M3.5 2.5h3v11h-3zM9.5 2.5h3v11h-3z"/></svg>',
  step: '<svg viewBox="0 0 16 16"><path d="M3 2.5v11l7-5.5zM11 2.5h2v11h-2z"/></svg>',
  reset: '<svg viewBox="0 0 16 16"><path d="M8 3a5 5 0 1 1-4.6 3H1.5L4.3 3l2.8 3H5.2A3.4 3.4 0 1 0 8 4.6z"/></svg>',
};

/**
 * Create a simulation view: compile the model, build Sim + Viewer, register
 * with the animation loop, and draw transport controls.
 *
 * opts: { model | xml, key, height, camera, overlays, toolbar (true), speeds,
 *         hud (true), onTick(sim), onReset(sim), autoplay }
 */
export async function createSimView(container, opts = {}) {
  const loading = h("div", { class: "widget__loading" }, "Loading MuJoCo 3.14.0 (WebAssembly)...");
  container.appendChild(loading);
  const [{ Viewer }, mj] = await Promise.all([import("../viewer.js"), getMujoco()]);
  const model = opts.xml ? await compileXml(opts.xml) : await loadModel(opts.model);
  const sim = new Sim(mj, model);
  if (opts.key != null) { sim.keyframe = opts.key; sim.reset(opts.key); }
  loading.remove();

  const vbox = h("div", { class: "viewer", style: { "--viewer-h": `${opts.height || 300}px` } });
  const hud = h("div", { class: "viewer__hud" });
  const hint = h("div", { class: "viewer__hint" }, "drag: orbit, right-drag: pan, ctrl+drag: push a body");
  const warn = h("div", { class: "viewer__warn", hidden: true });
  container.appendChild(vbox);
  const viewer = new Viewer(vbox, sim, { overlays: opts.overlays, camera: opts.camera, forceScale: opts.forceScale });
  vbox.append(hud, hint, warn);
  if (opts.hud === false) hud.hidden = true;

  const view = { sim, viewer, mj, container, vbox };
  const listen = (target) => target.on((s, event, detail) => {
    if (event === "warning") {
      warn.hidden = false;
      const reset = detail.kind === "badqacc" ? " MuJoCo reset the state automatically." : "";
      warn.textContent = `MuJoCo warning at t = ${fmt(detail.time)} s: ${detail.kind} (count ${detail.count}).${reset}`;
    }
    if (event === "reset") { warn.hidden = true; opts.onReset?.(s); }
  });
  listen(sim);

  let playBtn = null;
  const toolbar = h("div", { class: "toolbar" });
  if (opts.toolbar !== false) {
    playBtn = h("button", { type: "button", class: "btn btn--primary", html: ICONS.play + "Play", title: "Play or pause (Space)" });
    playBtn.onclick = () => view.toggle();
    const stepBtn = h("button", { type: "button", class: "btn", html: ICONS.step + "Step", title: "One timestep (.)" });
    stepBtn.onclick = () => view.stepOnce();
    const resetBtn = h("button", { type: "button", class: "btn", html: ICONS.reset + "Reset", title: "Reset (r)" });
    resetBtn.onclick = () => view.reset();
    const speeds = opts.speeds || [0.1, 0.25, 1, 4];
    const seg = h("div", { class: "seg", role: "group", "aria-label": "Simulation speed" });
    speeds.forEach((sp) => {
      const b = h("button", { type: "button", class: sp === 1 ? "is-on" : "" }, `${sp}x`);
      b.onclick = () => { view.speed = sp; view.sim.speed = sp; seg.querySelectorAll("button").forEach((x) => x.classList.toggle("is-on", x === b)); };
      seg.appendChild(b);
    });
    toolbar.append(playBtn, stepBtn, resetBtn, seg);
    container.appendChild(toolbar);
  }
  view.toolbar = toolbar;
  view.speed = 1;

  const syncPlay = () => {
    if (playBtn) playBtn.innerHTML = (view.sim.paused ? ICONS.play + "Play" : ICONS.pause + "Pause");
  };
  view.syncPlay = syncPlay;
  view.toggle = () => { view.sim.toggle(); syncPlay(); };
  view.play = () => { view.sim.play(); syncPlay(); };
  view.pause = () => { view.sim.pause(); syncPlay(); };
  view.stepOnce = () => { view.sim.pause(); syncPlay(); view.sim.step(1); opts.onTick?.(view.sim, 1); };
  view.reset = () => { view.sim.reset(); viewer.trail = []; opts.onTick?.(view.sim, 0); };

  const tick = (dt) => {
    const s = view.sim;
    const n = s.advance(dt);
    opts.onTick?.(s, n);
    viewer.update();
    viewer.render();
    if (!hud.hidden) {
      const lag = s.lag ? "  (slower than real time)" : "";
      hud.textContent = `t = ${s.time.toFixed(3)} s   dt = ${+(s.timestep * 1000).toFixed(3)} ms   ncon = ${s.data.ncon}${lag}`;
    }
  };
  const unregister = register(vbox, tick, { toggle: view.toggle, step: view.stepOnce, reset: view.reset });
  if (opts.autoplay) view.play();

  view.destroy = () => {
    unregister();
    viewer.dispose();
    view.sim.dispose();
  };
  /** Swap in a new model (library name, or MJCF text with isXml), keeping play state and speed. */
  view.replaceModel = async (xmlOrName, { isXml = false, camera = null } = {}) => {
    const next = isXml ? await compileXml(xmlOrName) : await loadModel(xmlOrName);
    const wasPaused = view.sim.paused;
    const newSim = new Sim(mj, next);
    newSim.speed = view.speed;
    newSim.controller = view.sim.controller;
    view.sim.dispose();
    view.sim = newSim;
    listen(newSim);
    warn.hidden = true;
    viewer.setSim(newSim, camera || opts.camera);
    if (!wasPaused) newSim.play();
    syncPlay();
    return newSim;
  };
  return view;
}

/** Overlay toggles bound to a viewer. */
export function overlayToggles(viewer, which = ["frames", "joints", "contacts", "forces", "com", "sites", "cameras"]) {
  const labels = { frames: "body frames", joints: "joint axes", contacts: "contacts", forces: "contact forces", com: "centres of mass", sites: "sites", cameras: "cameras", shadows: "shadows" };
  return h("div", { class: "toggles" }, which.map((k) => {
    const cb = h("input", { type: "checkbox", checked: viewer.overlays[k] ? true : null });
    cb.addEventListener("change", () => { viewer.overlays[k] = cb.checked; });
    return h("label", {}, cb, labels[k] || k);
  }));
}
