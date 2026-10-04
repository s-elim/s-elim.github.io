// cloth: a flexcomp cloth dropped over a ball (Showcase). The scene of examples/showcase_cloth.py: vertices
// 0.03 m apart with radius 6 mm, edges held by equality constraints, a ball of radius 8 cm on a floor. The
// course viewer draws geoms, not flexes, so this lab draws the cloth itself from flex_elem and
// flexvert_xpos. Readouts count the cloth's contacts and the vertices that are inside the floor or the ball:
// MuJoCo keeps at most mjMAXCONPAIR = 50 contacts per flex, and a larger cloth sinks.
//
// Config: {"title": "...", "height": 300}

import * as THREE from "three";
import { h, frame, select, button, readout, createSimView, fmt } from "./ui.js";

const R_VERT = 0.006, R_BALL = 0.08, SPACING = 0.03;
const xmlFor = (n) => `<mujoco model="cloth">
  <option timestep="0.002" solver="CG" tolerance="1e-6" integrator="implicitfast"/>
  <visual><headlight diffuse=".6 .6 .6"/></visual>
  <worldbody>
    <light pos="0.3 -0.4 1.2" dir="-0.2 0.3 -1"/>
    <geom name="floor" type="plane" size="1 1 0.05" rgba=".86 .88 .86 1"/>
    <geom name="ball" type="sphere" size="${R_BALL}" pos="0 0 ${R_BALL}" rgba=".85 .33 .1 1"/>
    <flexcomp name="cloth" type="grid" count="${n} ${n} 1" spacing="${SPACING} ${SPACING} ${SPACING}" pos="0 0 0.3"
              radius="${R_VERT}" dim="2" mass="0.1" rgba="0 0 0 0">
      <contact condim="3" solref="0.01 1" selfcollide="none"/>
      <edge equality="true" damping="0.001"/>
    </flexcomp>
  </worldbody>
</mujoco>`;

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Cloth over a ball", kind: "Lab" });
  let n = 14;
  const view = await createSimView(body, { xml: xmlFor(n), height: config.height || 300, toolbar: false,
    camera: { azimuth: 60, elevation: 28, distance: 0.75, target: [0, 0, 0.07] } });
  const outs = { contacts: readout("cloth contacts: floor, ball"), inside: readout("vertices inside the floor or ball"), deep: readout("deepest penetration") };
  let mesh = null;

  function buildMesh() {
    const { model } = view.sim;
    if (mesh) { view.viewer.overlayGroup.remove(mesh); mesh.geometry.dispose(); }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(new Float32Array(3 * model.nflexvert), 3));
    geo.setIndex(Array.from(model.flex_elem.slice(0, 3 * model.flex_elemnum[0])));
    mesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ color: 0x2f6db3, side: THREE.DoubleSide }));
    mesh.frustumCulled = false;
    view.viewer.overlayGroup.add(mesh);
  }

  async function drop() {
    await view.replaceModel(xmlFor(n), { isXml: true });
    buildMesh();
    view.reset();
    view.play();
  }

  let alive = true;
  const tick = () => {
    if (!alive) return;
    const { model, data, mj } = view.sim;
    if (mesh && model.nflexvert) {
      const pos = mesh.geometry.attributes.position;
      pos.array.set(data.flexvert_xpos.subarray ? data.flexvert_xpos.subarray(0, 3 * model.nflexvert) : Array.from(data.flexvert_xpos).slice(0, 3 * model.nflexvert));
      pos.needsUpdate = true;
      mesh.geometry.computeVertexNormals();
      const ball = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM.value, "ball");
      let floorC = 0, ballC = 0;
      if (data.ncon > 0) {
        const contacts = data.contact;                    // a copy (Lesson 3.4): delete it and its elements
        for (let i = 0; i < data.ncon; i++) {
          const c = contacts.get(i);
          if (c.geom1 === ball || c.geom2 === ball) ballC++; else floorC++;
          c.delete();
        }
        contacts.delete();
      }
      let inside = 0, deep = 0;
      const v = data.flexvert_xpos;
      for (let i = 0; i < model.nflexvert; i++) {
        const x = v[3 * i], y = v[3 * i + 1], z = v[3 * i + 2];
        const intoFloor = R_VERT - z, intoBall = R_BALL + R_VERT - Math.hypot(x, y, z - R_BALL);
        if (intoFloor > 0 || intoBall > 0) inside++;
        deep = Math.max(deep, intoFloor, intoBall);
      }
      outs.contacts.set(`${floorC}, ${ballC} (total ${floorC + ballC})`);
      outs.inside.set(`${inside} of ${model.nflexvert}`);
      outs.deep.set(`${fmt(1000 * deep, 1)} mm`);
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  body.append(
    h("div", { class: "toolbar" }, button("Drop the cloth", drop, "btn btn--primary"), button("Pause / play", () => view.toggle())),
    h("div", { class: "controls" },
      select({ label: "cloth size", options: [["6 x 6 vertices (0.15 m)", "6"], ["10 x 10 (0.27 m)", "10"], ["14 x 14 (0.39 m)", "14"], ["20 x 20 (0.57 m)", "20"]], value: String(n), onChange: (v) => { n = Number(v); } })),
    h("div", { class: "readouts" }, Object.values(outs)),
    h("p", { class: "widget__note", html: "The size applies at the next drop. A vertex counts as inside when its centre is closer to the floor or the ball than its 6 mm radius." }));
  await drop();

  return { destroy() { alive = false; if (mesh) { view.viewer.overlayGroup.remove(mesh); mesh.geometry.dispose(); } view.destroy(); } };
}
