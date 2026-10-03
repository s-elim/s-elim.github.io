// playground: edit MJCF, compile it with MuJoCo 3.14.0 in the browser, run it,
// change physics parameters live, and inspect state, contacts, forces and sensors.
//
// Used two ways: full page at #/playground, and compact inside lessons via
//   ```lab playground
//   {"model": "pendulum", "height": 260, "compact": true}
//   ```
// Compilation errors are MuJoCo's own compiler messages, line numbers included.

import { h, frame, slider, select, button, createSimView, overlayToggles, fmt } from "./ui.js";
import { modelSource, getMujoco, flag } from "../runtime.js";
import { liveTables } from "./inspect-tables.js";
import { CODEMIRROR_JS, CODEMIRROR_CSS, CODEMIRROR_XML, loadScript, loadStyle } from "../vendor.js";

export const LIBRARY = [
  ["ball_drop", "Two falling balls"], ["pendulum", "Pendulum"], ["double_pendulum", "Double pendulum"],
  ["cartpole", "Cart-pole"], ["arm2", "Two-link arm"], ["arm7", "7-DOF arm"], ["arm7_gripper", "7-DOF arm + gripper"],
  ["gantry_gripper", "Gantry gripper + cube"], ["cube_table", "Contact lab"], ["incline", "Incline"],
  ["hand3", "Three-finger hand"], ["point_mass", "Point mass arena"], ["reach", "Reach scene"],
  ["push", "Push scene"], ["pick_place", "Pick-and-place scene"], ["peg_insert", "Peg insertion"],
  ["articulated", "Drawer and door"], ["bimanual", "Bimanual cell"],
];

async function makeEditor(host, text, onRun) {
  try {
    await Promise.all([loadStyle(CODEMIRROR_CSS), loadScript(CODEMIRROR_JS)]);
    await loadScript(CODEMIRROR_XML);
    const cm = window.CodeMirror(host, {
      value: text, mode: "xml", lineNumbers: true, lineWrapping: false, tabSize: 2, indentUnit: 2,
      extraKeys: { "Ctrl-Enter": () => onRun(), "Cmd-Enter": () => onRun() },
    });
    return { get: () => cm.getValue(), set: (v) => cm.setValue(v), cm, refresh: () => cm.refresh() };
  } catch (e) {
    const ta = h("textarea", { class: "fallback", spellcheck: "false" });
    ta.value = text;
    ta.addEventListener("keydown", (ev) => { if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") onRun(); });
    host.appendChild(ta);
    return { get: () => ta.value, set: (v) => { ta.value = v; }, refresh() {} };
  }
}

export async function mount(el, config = {}, ctx = {}) {
  const full = Boolean(config.full);
  let initial = config.xml || null;
  if (!initial && full) {
    try { initial = sessionStorage.getItem("mjcourse:playground-xml"); } catch (e) { /* ignore */ }
  }
  const startModel = config.model || "pendulum";
  if (!initial) initial = await modelSource(startModel);

  // Layout
  let root, left, right, head;
  if (full) {
    el.innerHTML = "";
    head = h("div", { class: "pg__head" }, h("h1", {}, "Playground"));
    left = h("div", { class: "pg__left" });
    right = h("div", { class: "pg__right" });
    root = h("div", { class: "pg" }, head, left, right);
    el.appendChild(root);
  } else {
    const f = frame(el, { title: config.title || "Edit the model, then Run (Ctrl+Enter)", kind: "Playground" });
    root = f.body;
    head = h("div", { class: "toolbar" });
    left = h("div", { style: { display: "flex", flexDirection: "column", gap: "8px" } });
    right = h("div", { style: { display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px" } });
    root.append(head, left, right);
  }

  const consoleEl = h("div", { class: "pg__console", role: "log", "aria-live": "polite" });
  const say = (msg, cls = "") => {
    const line = h("div", { class: cls }, `[${new Date().toLocaleTimeString()}] ${msg}`);
    consoleEl.appendChild(line);
    consoleEl.scrollTop = consoleEl.scrollHeight;
  };

  const editorHost = h("div", { class: "pg__editor", style: full ? {} : { height: `${config.editorHeight || 220}px` } });
  left.appendChild(editorHost);
  left.appendChild(consoleEl);

  const viewHost = h("div", { class: full ? "pg__view" : "" });
  right.appendChild(viewHost);
  const mj = await getMujoco();
  say(`MuJoCo ${mj.mj_versionString()} (WebAssembly) ready.`, "ok");

  let view = null;
  let tables = null;
  const run = async () => {
    const xml = editor.get();
    try {
      if (!view) {
        view = await createSimView(viewHost, { xml, height: full ? undefined : (config.height || 260), onTick: (s) => { tables?.update(s); paramsSync?.(); } });
      } else {
        await view.replaceModel(xml, { isXml: true });
      }
      const m = view.sim.model;
      say(`Compiled: nq=${m.nq} nv=${m.nv} nu=${m.nu} nbody=${m.nbody} ngeom=${m.ngeom} timestep=${m.opt.timestep}`, "ok");
      buildParams();
      tables?.update(view.sim, true);
      if (full) {
        try { sessionStorage.setItem("mjcourse:playground-xml", xml); } catch (e) { /* ignore */ }
      }
    } catch (err) {
      say(`Compile error: ${err.message}`, "err");
    }
  };
  const editor = await makeEditor(editorHost, initial, run);

  // Header: library picker and run
  const picker = select({
    label: "Load", value: "", options: [["(library model)", ""], ...LIBRARY.map(([v, t]) => [t, v])],
    onChange: async (v) => { if (!v) return; editor.set(await modelSource(v)); run(); },
  });
  picker.style.gridTemplateColumns = "auto 1fr";
  const runBtn = button("Run (Ctrl+Enter)", run, "btn btn--primary");
  const dlBtn = button("Download XML", () => {
    const blob = new Blob([editor.get()], { type: "application/xml" });
    const a = h("a", { href: URL.createObjectURL(blob), download: "model.xml" });
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
  head.append(runBtn, dlBtn, picker);

  // Parameter inspector: edits mjModel fields of the compiled model in place.
  const paramsBox = h("div", { class: "controls" });
  let paramsSync = null;
  const buildParams = () => {
    const s = view.sim;
    const m = s.model;
    paramsBox.replaceChildren();
    const sliders = [];
    const add = (spec) => { const r = slider(spec); paramsBox.appendChild(r); sliders.push(r); return r; };
    add({ label: "timestep", unit: "s", min: 0.0002, max: 0.02, step: 0.0002, value: m.opt.timestep, digits: 4, onInput: (v) => { s.model.opt.timestep = v; } });
    add({ label: "gravity z", unit: "m/s^2", min: -20, max: 5, step: 0.01, value: m.opt.gravity[2], digits: 2, onInput: (v) => { s.model.opt.gravity[2] = v; } });
    paramsBox.appendChild(select({ label: "integrator", value: m.opt.integrator,
      options: [["Euler (semi-implicit)", 0], ["RK4", 1], ["implicit", 2], ["implicitfast", 3], ["discrete", 4]],
      onChange: (v) => { s.model.opt.integrator = +v; say(`integrator set to ${v}`); } }));
    if (m.ngeom) {
      add({ label: "friction scale (all geoms)", min: 0, max: 3, step: 0.01, value: 1, digits: 2, onInput: (v) => {
        if (!s._fric0) s._fric0 = Float64Array.from(s.model.geom_friction);
        for (let i = 0; i < s.model.ngeom; i++) s.model.geom_friction[3 * i] = s._fric0[3 * i] * v;
      } });
    }
    if (m.nv) {
      add({ label: "added damping (every DOF)", unit: "N s/m or N m s/rad", min: 0, max: 2, step: 0.01, value: 0, digits: 2, onInput: (v) => {
        if (!s._damp0) s._damp0 = Float64Array.from(s.model.dof_damping);
        for (let i = 0; i < s.model.nv; i++) s.model.dof_damping[i] = s._damp0[i] + v;
      } });
    }
    if (m.nbody > 1) {
      add({ label: "mass scale (all bodies)", min: 0.1, max: 5, step: 0.01, value: 1, digits: 2, onInput: (v) => {
        if (!s._mass0) { s._mass0 = Float64Array.from(s.model.body_mass); s._inert0 = Float64Array.from(s.model.body_inertia); }
        for (let b = 0; b < s.model.nbody; b++) {
          s.model.body_mass[b] = s._mass0[b] * v;
          for (let k = 0; k < 3; k++) s.model.body_inertia[3 * b + k] = s._inert0[3 * b + k] * v;
        }
        // body_mass and body_inertia feed quantities MuJoCo precomputes at compile time
        // (for example body_subtreemass, dof_invweight0); mj_setConst refreshes them.
        s.mj.mj_setConst(s.model, s.data);
      } });
    }
    for (let a = 0; a < m.nu; a++) {
      const lim = flag(m, "actuator", a, "ctrllimited");
      const lo = lim ? m.actuator_ctrlrange[2 * a] : -1, hi = lim ? m.actuator_ctrlrange[2 * a + 1] : 1;
      const name = s.mj.mj_id2name(m, s.mj.mjtObj.mjOBJ_ACTUATOR.value, a) || `actuator ${a}`;
      add({ label: `ctrl: ${name}`, min: lo, max: hi, step: (hi - lo) / 200, value: s.data.ctrl[a], digits: 3, onInput: (v) => { s.data.ctrl[a] = v; } });
    }
    paramsSync = null;
  };

  const paramsTitle = h("div", { class: "labdock__title" }, "Parameters (edit mjModel live)");
  const inspectTitle = h("div", { class: "labdock__title" }, "Inspector (live mjData)");
  const inspectBox = h("div", { class: full ? "pg__inspect" : "" });

  await run();
  if (!view) {
    say("The starting model failed to compile; edit it and press Run.", "err");
    return { destroy() {} };
  }
  viewHost.appendChild(overlayToggles(view.viewer, ["frames", "joints", "contacts", "forces", "com", "sites", "cameras", "shadows"]));
  inspectBox.append(paramsTitle, paramsBox, inspectTitle);
  right.appendChild(inspectBox);
  tables = liveTables(inspectBox, ["state", "ctrl", "contacts", "sensors", "bodies", "sizes"]);
  tables.update(view.sim, true);
  if (full) setTimeout(() => editor.refresh(), 50);

  return { destroy() { view?.destroy(); } };
}
