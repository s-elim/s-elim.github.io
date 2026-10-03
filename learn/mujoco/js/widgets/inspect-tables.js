// Tables of live MuJoCo state, shared by the inspector lab and the playground.
//
// Each tab reads straight from mjData / mjModel every frame. Rows that changed
// since the previous frame are highlighted, which is the quickest way to see
// which arrays a given operation writes.

import { h, fmt } from "./ui.js";
import { nameOf, flag } from "../runtime.js";

const JNT_TYPES = ["free", "ball", "slide", "hinge"];
const QPOS_WIDTH = [7, 4, 1, 1];
const DOF_WIDTH = [6, 3, 1, 1];

function table(headers, rows) {
  return h("table", {},
    h("thead", {}, h("tr", {}, headers.map((x) => h("th", {}, x)))),
    h("tbody", {}, rows.map((r) => h("tr", {}, r.map((c, i) => {
      const td = h("td", {}, typeof c === "number" ? fmt(c, 4) : c);
      return td;
    })))));
}

/** Joint-level view of qpos / qvel / qacc with names and joint types. */
export function stateRows(sim) {
  const { mj, model, data } = sim;
  const rows = [];
  for (let j = 0; j < model.njnt; j++) {
    const t = model.jnt_type[j];
    const qa = model.jnt_qposadr[j], da = model.jnt_dofadr[j];
    const name = nameOf(mj, model, "mjOBJ_JOINT", j) || `joint ${j}`;
    for (let k = 0; k < QPOS_WIDTH[t]; k++) {
      const dof = k < DOF_WIDTH[t] ? da + k : null;
      rows.push([
        k === 0 ? `${name} (${JNT_TYPES[t]})` : "",
        `qpos[${qa + k}]`, data.qpos[qa + k],
        dof == null ? "" : `qvel[${dof}]`, dof == null ? "" : data.qvel[dof],
        dof == null ? "" : data.qacc[dof],
      ]);
    }
  }
  return { headers: ["joint", "index", "qpos", "index", "qvel", "qacc"], rows };
}

export function actuatorRows(sim) {
  const { mj, model, data } = sim;
  const rows = [];
  for (let a = 0; a < model.nu; a++) {
    const lim = flag(model, "actuator", a, "ctrllimited") ? `[${fmt(model.actuator_ctrlrange[2 * a], 2)}, ${fmt(model.actuator_ctrlrange[2 * a + 1], 2)}]` : "unlimited";
    rows.push([nameOf(mj, model, "mjOBJ_ACTUATOR", a) || `actuator ${a}`, data.ctrl[a], lim, data.actuator_force[a]]);
  }
  return { headers: ["actuator", "ctrl", "ctrlrange", "actuator_force"], rows };
}

export function sensorRows(sim) {
  const { mj, model, data } = sim;
  const rows = [];
  for (let s = 0; s < model.nsensor; s++) {
    const adr = model.sensor_adr[s], dim = model.sensor_dim[s];
    const vals = Array.from(data.sensordata.subarray(adr, adr + dim)).map((v) => fmt(v, 4)).join(", ");
    rows.push([nameOf(mj, model, "mjOBJ_SENSOR", s) || `sensor ${s}`, `sensordata[${adr}:${adr + dim}]`, vals]);
  }
  return { headers: ["sensor", "slice", "value"], rows };
}

export function contactRows(sim) {
  const { mj, model } = sim;
  const rows = sim.contacts().map((c, i) => [
    i,
    nameOf(mj, model, "mjOBJ_GEOM", c.geom1) || `geom ${c.geom1}`,
    nameOf(mj, model, "mjOBJ_GEOM", c.geom2) || `geom ${c.geom2}`,
    c.dist, c.force[0], Math.hypot(c.force[1], c.force[2]), c.dim, c.active ? "yes" : "no",
  ]);
  return { headers: ["#", "geom1", "geom2", "dist (m)", "normal (N)", "|friction| (N)", "condim", "active"], rows };
}

export function bodyRows(sim) {
  const { mj, model, data } = sim;
  const rows = [];
  for (let b = 0; b < model.nbody; b++) {
    rows.push([nameOf(mj, model, "mjOBJ_BODY", b) || (b === 0 ? "world" : `body ${b}`), model.body_mass[b],
      data.xpos[3 * b], data.xpos[3 * b + 1], data.xpos[3 * b + 2],
      data.xquat[4 * b], data.xquat[4 * b + 1], data.xquat[4 * b + 2], data.xquat[4 * b + 3]]);
  }
  return { headers: ["body", "mass (kg)", "x", "y", "z", "qw", "qx", "qy", "qz"], rows };
}

export function sizeRows(sim) {
  const { model } = sim;
  const keys = ["nq", "nv", "nu", "na", "nbody", "njnt", "ngeom", "nsite", "ncam", "nsensor", "ntendon", "neq", "nkey", "nmocap"];
  return { headers: ["size", "value", "meaning"], rows: keys.map((k) => [k, model[k], SIZE_MEANING[k] || ""]) };
}

const SIZE_MEANING = {
  nq: "position coordinates (qpos)", nv: "degrees of freedom (qvel, qacc)", nu: "control inputs (ctrl)",
  na: "actuator activations (act)", nbody: "bodies, including world", njnt: "joints", ngeom: "geoms",
  nsite: "sites", ncam: "cameras", nsensor: "sensors", ntendon: "tendons", neq: "equality constraints",
  nkey: "keyframes", nmocap: "mocap bodies",
};

export const TABS = {
  state: ["State (qpos, qvel, qacc)", stateRows],
  ctrl: ["Actuators", actuatorRows],
  contacts: ["Contacts", contactRows],
  sensors: ["Sensors", sensorRows],
  bodies: ["Bodies (xpos, xquat)", bodyRows],
  sizes: ["Model sizes", sizeRows],
};

/**
 * A tabbed live table. Call .update(sim) every frame; it re-renders at most
 * every `every` frames and marks cells that changed.
 */
export function liveTables(container, tabs = Object.keys(TABS), { every = 6 } = {}) {
  let current = tabs[0];
  const bar = h("div", { class: "tabs", role: "tablist" });
  const box = h("div", { class: "arrays" });
  const buttons = tabs.map((t) => {
    const b = h("button", { type: "button", role: "tab", class: t === current ? "is-on" : "" }, TABS[t][0]);
    b.onclick = () => { current = t; buttons.forEach((x) => x.classList.toggle("is-on", x === b)); prev = null; frame = 0; };
    bar.appendChild(b);
    return b;
  });
  container.append(bar, box);
  let prev = null;
  let frame = 0;
  return {
    update(sim, force = false) {
      if (!force && frame++ % every) return;
      const { headers, rows } = TABS[current][1](sim);
      const t = table(headers, rows);
      if (prev && prev.length === rows.length) {
        const trs = t.querySelectorAll("tbody tr");
        rows.forEach((r, i) => r.forEach((c, k) => {
          if (typeof c === "number" && typeof prev[i][k] === "number" && Math.abs(c - prev[i][k]) > 1e-12) trs[i].children[k].classList.add("changed");
        }));
      }
      prev = rows;
      box.replaceChildren(rows.length ? t : h("p", { class: "widget__note", style: { padding: ".5rem" } }, "Nothing to show for this model."));
    },
  };
}
