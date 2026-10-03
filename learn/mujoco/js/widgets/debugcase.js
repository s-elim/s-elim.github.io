// debug: one deliberately broken example, presented as
// SYMPTOM -> DIAGNOSIS -> ROOT CAUSE -> FIX -> GENERAL LESSON.
//
// Body (JSON): {"title": "...", "model": "broken/fall_through.xml" (optional),
//   "symptom": "...", "diagnosis": "...", "cause": "...", "fix": "...", "lesson": "...",
//   "fixed": "fall_through_fixed.xml" (optional)}
// The steps after the symptom stay folded until the learner opens them, so the
// case can be attempted first.

import { h } from "./ui.js";
import { modelSource } from "../runtime.js";

export async function mount(el, raw) {
  let c;
  try { c = JSON.parse(raw); } catch (e) {
    el.innerHTML = `<div class="widget__error">debug block: ${e.message}</div>`;
    return null;
  }
  const step = (label, html) => h("div", { class: "debugcase__step" }, h("b", {}, label), h("div", { html }));
  const body = h("div", { class: "debugcase__body" }, step("Symptom", c.symptom));
  const actions = h("div", { class: "toolbar" });
  if (c.model) {
    actions.appendChild(h("button", { type: "button", class: "btn btn--primary", onclick: async () => {
      const xml = await modelSource(c.model);
      try { sessionStorage.setItem("mjcourse:playground-xml", xml); } catch (e) { /* ignore */ }
      location.hash = "#/playground?from=debug";
    } }, "Open the broken model in the playground"));
  }
  body.appendChild(actions);
  const hidden = h("details", {},
    h("summary", { class: "btn btn--small", style: { display: "inline-flex", margin: ".4rem 0" } }, "Show diagnosis and fix"),
    step("Diagnosis", c.diagnosis),
    step("Root cause", c.cause),
    step("Fix", c.fix),
    step("General lesson", c.lesson));
  body.appendChild(hidden);
  const details = h("details", { class: "debugcase", open: true },
    h("summary", {}, h("span", { class: "tag" }, "Broken"), c.title),
    body);
  el.innerHTML = "";
  el.appendChild(details);
  return { destroy() {} };
}
