// pipeline: mj_forward one stage at a time, in the page (Lesson 20.1). The experiment of
// examples/l20_1_pipeline.py: pick_place is simulated for 0.5 s, every float array of mjData that is not an
// input is filled with NaN, and the public stage functions run in mj_forward's order; after each one the lab
// lists the fields it filled. The last row compares the resulting qacc with a fresh mj_forward.
//
// Config: {"title": "...", "height": 260}

import { h, frame, button, readout, createSimView, fmt } from "./ui.js";

const INPUTS = new Set(["qpos", "qvel", "act", "ctrl", "qfrc_applied", "xfrc_applied", "mocap_pos", "mocap_quat", "userdata",
  "qacc_warmstart", "plugin_state", "history", "eq_active"]);
const STAGES = ["mj_fwdPosition", "mj_sensorPos", "mj_fwdVelocity", "mj_sensorVel", "mj_fwdActuation", "mj_fwdAcceleration", "mj_fwdConstraint", "mj_sensorAcc"];

/** Float64 views of every non-input mjData array (fresh each time: the arena moves). */
function floatFields(data) {
  const out = {};
  const names = new Set();
  for (let p = data; p && p !== Object.prototype; p = Object.getPrototypeOf(p)) Object.getOwnPropertyNames(p).forEach((n) => names.add(n));
  for (const name of names) {
    if (name.startsWith("_") || INPUTS.has(name) || name === "constructor") continue;
    let v;
    try { v = data[name]; } catch { continue; }
    if (v instanceof Float64Array && v.length) out[name] = v;
  }
  return out;
}
const allFinite = (v) => { for (let i = 0; i < v.length; i++) if (!Number.isFinite(v[i])) return false; return true; };
const countFinite = (v) => { let n = 0; for (let i = 0; i < v.length; i++) if (Number.isFinite(v[i])) n++; return n; };

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "mj_forward, one stage at a time", kind: "Lab" });
  const view = await createSimView(body, { model: "pick_place", key: 0, height: config.height || 260, toolbar: false,
    camera: { azimuth: -140, elevation: 25, distance: 1.6, target: [0.45, 0, 0.25] } });
  const { mj, model, data } = view.sim;
  const missing = STAGES.filter((s) => typeof mj[s] !== "function");
  const rows = h("div", { class: "pipeline" });
  const outs = { state: readout("state"), check: readout("qacc against mj_forward") };
  let next = 0, written = new Set(), reference = null;

  function settle() {
    view.sim.reset(0);
    while (data.time < 0.5) mj.mj_step(model, data);
    mj.mj_forward(model, data);
    reference = Float64Array.from(data.qacc);
    outs.state.set(`t = ${fmt(data.time, 3)} s, ncon ${data.ncon}, nefc ${data.nefc}`);
  }
  function poison() {
    settle();
    for (const v of Object.values(floatFields(data))) v.fill(NaN);
    written = new Set(); next = 0;
    rows.querySelectorAll(".pipeline__out").forEach((o) => { o.textContent = ""; });
    outs.check.set("-");
    rows.querySelectorAll("button").forEach((b, i) => { b.disabled = i !== 0; });
  }
  function runStage(i) {
    if (i !== next) return;
    mj[STAGES[i]](model, data);
    const fields = floatFields(data), done = [], partial = [];
    for (const [n, v] of Object.entries(fields)) {
      if (allFinite(v)) { if (!written.has(n)) done.push(n); }
      else { const c = countFinite(v); if (c) partial.push(`${n} (${c} of ${v.length})`); }
    }
    done.sort().forEach((n) => written.add(n));
    rows.querySelectorAll(".pipeline__out")[i].textContent = (done.length ? done.join(", ") : "nothing complete") + (partial.length ? `; partly: ${partial.join(", ")}` : "");
    next = i + 1;
    rows.querySelectorAll("button").forEach((b, k) => { b.disabled = k !== next; });
    if (next === STAGES.length) {
      let diff = 0;
      for (let k = 0; k < model.nv; k++) diff = Math.max(diff, Math.abs(data.qacc[k] - reference[k]));
      outs.check.set(`max difference ${diff.toExponential(1)}`);
    }
  }

  STAGES.forEach((s, i) => rows.append(h("div", { class: "pipeline__row" },
    h("button", { type: "button", class: "btn", disabled: true, onclick: () => runStage(i) }, s), h("span", { class: "pipeline__out" }))));
  body.append(
    h("div", { class: "toolbar" }, button("Fill mjData with NaN", poison, "btn btn--primary"),
      button("Run every stage", () => { if (next === 0 && !written.size) poison(); for (let i = next; i < STAGES.length; i++) runStage(i); })),
    missing.length ? h("p", { class: "widget__error" }, `These functions are missing from the bindings: ${missing.join(", ")}`) : rows,
    h("div", { class: "readouts" }, Object.values(outs)),
    h("p", { class: "widget__note", html: "Inputs (qpos, qvel, act, ctrl, applied forces, mocap, qacc_warmstart) are left alone. sensordata is one array written by three stages, so it shows as partly written until the last." }));
  settle();

  return { destroy() { view.destroy(); } };
}
