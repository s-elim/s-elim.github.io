// cradle: a Newton's cradle with a choice of contact model and gap (Showcase). The same five balls as
// examples/showcase_newtons_cradle.py (0.26 kg, radius 2 cm, 0.2 m pendulums, frictionless contacts, 0.1 ms
// step). Readouts: each ball's velocity along the row 30 ms after the first impact, as a fraction of the
// incoming speed, and the mechanical energy left.
//
// Config: {"title": "...", "height": 280}

import { h, frame, select, button, readout, createSimView, fmt } from "./ui.js";

const R = 0.02, LENGTH = 0.2, N = 5, MASS = 0.26;
const SETTINGS = { soft: "0.02 1", damped: "0.02 0.1", stiff: "-1e7 -10" };

function xmlFor(solref, gap) {
  const balls = Array.from({ length: N }, (_, i) => `
    <body name="b${i}" pos="${(i * (2 * R + gap)).toFixed(6)} 0 0.3">
      <joint type="hinge" axis="0 1 0"/>
      <geom type="capsule" fromto="0 0 0 0 0 ${-LENGTH + R}" size="0.0015" mass="0" contype="0" conaffinity="0" rgba=".55 .55 .55 1"/>
      <geom name="g${i}" type="sphere" pos="0 0 ${-LENGTH}" size="${R}" mass="${MASS}" condim="1" solref="${solref}" rgba=".72 .75 .8 1"/>
    </body>`).join("");
  return `<mujoco model="cradle"><option timestep="0.0001"><flag energy="enable"/></option>
  <visual><headlight diffuse=".7 .7 .7"/></visual>
  <worldbody>
    <light pos="0.1 -0.6 0.8" dir="0 1 -1"/>
    <geom type="box" size="0.14 0.01 0.006" pos="${2 * (2 * R + gap)} 0 0.306" rgba=".25 .25 .28 1" contype="0" conaffinity="0"/>
    ${balls}
  </worldbody></mujoco>`;
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Newton's cradle", kind: "Lab" });
  const opt = { contact: "stiff", gap: 0.001, lifted: 1 };
  const view = await createSimView(body, { xml: xmlFor(SETTINGS[opt.contact], opt.gap), height: config.height || 280, toolbar: false,
    camera: { azimuth: 90, elevation: 4, distance: 0.75, target: [0.09, 0, 0.17] } });
  const outs = { v: readout("velocities 30 ms after impact (fraction of incoming)"), e: readout("mechanical energy left") };
  let ep = null;

  async function release() {
    const xml = xmlFor(SETTINGS[opt.contact], opt.gap);
    const sim = await view.replaceModel(xml, { isXml: true });
    const { mj, model, data } = sim;
    mj.mj_resetData(model, data);
    mj.mj_forward(model, data);
    const eRest = data.energy[0] + data.energy[1];
    for (let i = 0; i < opt.lifted; i++) data.qpos[i] = 30 * Math.PI / 180;      // toward -x
    mj.mj_forward(model, data);
    const first = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM.value, `g${opt.lifted - 1}`), second = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM.value, `g${opt.lifted}`);
    ep = { e0: data.energy[0] + data.energy[1] - eRest, eRest, hit: null, done: false,
      incoming: Math.sqrt(2 * 9.81 * LENGTH * (1 - Math.cos(30 * Math.PI / 180))) };
    outs.v.set("waiting for the impact"); outs.e.set("1.000");
    sim.controller = (s) => {
      const d = s.data;
      if (ep.hit === null) {
        if (d.ncon > 0) {
          const contacts = d.contact;                     // a copy (Lesson 3.4): delete it and its elements
          for (let i = 0; i < d.ncon && ep.hit === null; i++) {
            const c = contacts.get(i);
            if ((c.geom1 === first && c.geom2 === second) || (c.geom1 === second && c.geom2 === first)) ep.hit = d.time;
            c.delete();
          }
          contacts.delete();
        }
      } else if (!ep.done && d.time >= ep.hit + 0.03) {
        ep.done = true;
        outs.v.set(Array.from(d.qvel, (q) => (-q * LENGTH / ep.incoming).toFixed(3)).join("  "));
      }
    };
    view.play();
  }

  let alive = true;
  const tick = () => {
    if (!alive) return;
    const d = view.sim.data;
    if (ep && ep.e0) outs.e.set(fmt((d.energy[0] + d.energy[1] - ep.eRest) / ep.e0, 3));
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  body.append(
    h("div", { class: "toolbar" }, button("Release", release, "btn btn--primary"), button("Pause / play", () => view.toggle())),
    h("div", { class: "controls" },
      select({ label: "contact", options: [["stiff spring, solref (-1e7, -10)", "stiff"], ["default soft, solref (0.02, 1)", "soft"], ["less damping, solref (0.02, 0.1)", "damped"]], value: opt.contact, onChange: (v) => { opt.contact = v; } }),
      select({ label: "gap between balls", options: [["1 mm", "0.001"], ["0.1 mm", "0.0001"], ["touching", "0"]], value: "0.001", onChange: (v) => { opt.gap = Number(v); } }),
      select({ label: "balls lifted", options: [["one", "1"], ["two", "2"]], value: "1", onChange: (v) => { opt.lifted = Number(v); } })),
    h("div", { class: "readouts" }, Object.values(outs)),
    h("p", { class: "widget__note", html: "Settings apply at the next <b>Release</b>. Velocities are listed from the lifted end; 1.000 means a ball leaves with the full incoming speed." }));
  await release();

  return { destroy() { alive = false; view.destroy(); } };
}
