// inspector: what lives in mjModel, what lives in mjData, and which arrays one
// call to mj_step, mj_forward or mj_resetData writes.
//
// Config: {"model": "pendulum", "key": 0, "tabs": ["state", "bodies", "sizes"], "height": 240}

import { h, frame, button, createSimView } from "./ui.js";
import { liveTables } from "./inspect-tables.js";

const PIPE = [
  ["MJCF", "XML text you write"],
  ["mjSpec", "parsed, editable model"],
  ["mjModel", "compiled, constant during simulation"],
  ["mjData", "state + everything computed from it"],
  ["mj_step", "advances mjData by one timestep"],
];

export async function mount(el, config) {
  const { body } = frame(el, { title: config.title || "mjModel and mjData, live", kind: "Inspector" });
  const pipe = h("div", { class: "toolbar", style: { gap: ".25rem", fontFamily: "var(--mono)", fontSize: ".72rem" } });
  PIPE.forEach(([name, what], i) => {
    pipe.appendChild(h("span", { class: "chip", title: what }, name));
    if (i < PIPE.length - 1) pipe.appendChild(h("span", { "aria-hidden": "true" }, "→"));
  });
  body.appendChild(pipe);

  let tables = null;
  const view = await createSimView(body, {
    model: config.model || "pendulum", key: config.key, height: config.height || 220,
    camera: config.camera, overlays: config.overlays,
    onTick: (s) => tables?.update(s),
  });
  const log = h("p", { class: "widget__note" }, "Run one call and watch which cells change colour: highlighted cells were written by that call.");
  const sim = () => view.sim;
  const once = (label, fn) => button(label, () => {
    view.pause();
    fn();
    tables.update(sim(), true);
    log.textContent = `${label}: time is now ${sim().time.toFixed(4)} s.`;
  }, "btn btn--small");
  body.appendChild(h("div", { class: "toolbar" },
    once("mj_step", () => sim().step(1)),
    once("mj_forward", () => sim().forward()),
    once("mj_resetData", () => sim().reset(-1)),
    once("qpos[0] += 0.1 (no forward)", () => { sim().data.qpos[0] += 0.1; }),
  ));
  body.appendChild(log);
  tables = liveTables(body, config.tabs || ["state", "bodies", "ctrl", "sensors", "contacts", "sizes"]);
  tables.update(sim(), true);
  return { destroy() { view.destroy(); } };
}
