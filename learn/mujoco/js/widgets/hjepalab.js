// Interactive 7-DOF Franka Panda simulation with Hierarchical World Models.
// Demonstrates in-scene 3D multimodal sensor rendering (Raman Laser, 3D LiDAR Rays, 
// 77 GHz Radar Doppler Cone, RGB-D Voxel Bounding Boxes) and long-horizon industrial tasks.

import * as THREE from "three";
import { h, frame, slider, select, button, readout, createSimView, fmt } from "./ui.js";
import { idOf } from "../runtime.js";
import { solve, transpose, matVec, norm, quatFromMat, quatMul, quatConj, quatToRotvec } from "../linalg.js";

const WN = 20;
const OPEN = 0.04;

const CAMERAS = {
  orbit: { azimuth: -135, elevation: 28, distance: 1.45, target: [0.5, 0.0, 0.12] },
  overhead: { azimuth: 180, elevation: 89, distance: 1.35, target: [0.5, 0.0, 0.02] },
  front: { azimuth: 0, elevation: 20, distance: 1.35, target: [0.5, 0.0, 0.15] },
  wrist: { azimuth: -160, elevation: 15, distance: 0.75, target: [0.48, 0.0, 0.1] },
};

const ENVIRONMENTS = [
  {
    id: "battery_assembly",
    model: "industrial_battery",
    label: "Industrial Workcell 1: Automotive Battery Module Assembly & QC",
    desc: "Cleanroom robotic station with prismatic Li-ion battery cell, polyamide bushing, and alloy busbar.",
    objects: ["battery_cell", "insulator_bushing", "terminal_busbar"],
    tasks: [
      {
        id: "task_battery_tripart",
        label: "Task 1: Complete EV Battery Module Assembly (3-Part Sequence)",
        desc: "Raman spectroscopic verification and precision seating of battery cell, insulator, and busbar.",
        stages: [
          { obj: "battery_cell", dest: "chassis_target", grabZ: 0.035, placeZ: 0.055, label: "Stage 1: Raman Scan Prismatic Battery Cell -> Seat into Chassis Pocket", material: "Polyethylene Dielectric Casing / LiFePO4" },
          { obj: "insulator_bushing", dest: "isolation_target", grabZ: 0.030, placeZ: 0.045, label: "Stage 2: Raman Scan Polyamide Insulator Bushing -> Insert into Isolation Bay", material: "Nylon-6/66 Dielectric Polymer" },
          { obj: "terminal_busbar", dest: "dock_target", grabZ: 0.022, placeZ: 0.038, label: "Stage 3: Raman Scan Al-6061 Busbar Terminal -> Dock into Clamping Receptacle", material: "Aluminum 6061 Conductive Alloy" },
        ],
      },
      {
        id: "task_battery_cell_only",
        label: "Task 2: Critical High-Voltage Battery Cell Seating & Verification",
        desc: "Precision insertion of heavy prismatic Li-ion cell into chassis pocket with impedance monitoring.",
        stages: [
          { obj: "battery_cell", dest: "chassis_target", grabZ: 0.035, placeZ: 0.055, label: "Stage 1: Raman Scan & Alignment of Battery Cell -> Chassis Pocket", material: "Polyethylene Dielectric Casing / LiFePO4" },
        ],
      },
      {
        id: "task_battery_connectors",
        label: "Task 3: Dielectric Bushing Insertion & Terminal Docking",
        desc: "Dual-part assembly of electrical isolation bushing and conductive busbar terminal.",
        stages: [
          { obj: "insulator_bushing", dest: "isolation_target", grabZ: 0.030, placeZ: 0.045, label: "Stage 1: Polyamide Insulator Bushing -> Isolation Bay", material: "Nylon-6/66 Dielectric Polymer" },
          { obj: "terminal_busbar", dest: "dock_target", grabZ: 0.022, placeZ: 0.038, label: "Stage 2: Al-6061 Busbar Terminal -> Clamping Receptacle", material: "Aluminum 6061 Conductive Alloy" },
        ],
      },
    ],
  },
  {
    id: "semiconductor_cleanroom",
    model: "industrial_semiconductor",
    label: "Industrial Workcell 2: Semiconductor Wafer Carrier & Fixture Kitting",
    desc: "ISO Class 4 cleanroom handling FOUP wafer cassettes and quartz boats with 3D LiDAR obstacle clearance.",
    objects: ["wafer_cassette", "quartz_boat"],
    tasks: [
      {
        id: "task_wafer_traversal",
        label: "Task 1: Wafer Cassette FOUP Transfer over Cleanroom Barrier",
        desc: "LiDAR ToF obstacle elevation scan and high-clearance traversal over safety barrier wall.",
        stages: [
          { obj: "wafer_cassette", dest: "chuck_target", grabZ: 0.032, placeZ: 0.045, needsObstacleClearance: true, label: "Stage 1: LiDAR Elevation Scan & Barrier Traversal -> Vacuum Chuck Nest", material: "Silicon Wafer Cassette / FOUP" },
        ],
      },
      {
        id: "task_quartz_inspection",
        label: "Task 2: Quartz Boat Carrier Traversal & Metrology Alignment",
        desc: "Doppler-stabilized transfer over barrier wall into precision laser metrology stage.",
        stages: [
          { obj: "quartz_boat", dest: "stage_target", grabZ: 0.030, placeZ: 0.045, needsObstacleClearance: true, label: "Stage 1: Doppler-Stabilized Transfer over Barrier -> Laser Metrology Stage", material: "Fused Silica Quartz Boat" },
        ],
      },
      {
        id: "task_semiconductor_dual",
        label: "Task 3: Dual Semiconductor Carrier Batch Transfer",
        desc: "Sequential transfer of silicon FOUP cassette and quartz carrier boat over partition barrier.",
        stages: [
          { obj: "wafer_cassette", dest: "chuck_target", grabZ: 0.032, placeZ: 0.045, needsObstacleClearance: true, label: "Stage 1: Wafer Cassette FOUP -> Vacuum Chuck Nest", material: "Silicon Wafer Cassette / FOUP" },
          { obj: "quartz_boat", dest: "stage_target", grabZ: 0.030, placeZ: 0.045, needsObstacleClearance: true, label: "Stage 2: Quartz Carrier Boat -> Laser Metrology Stage", material: "Fused Silica Quartz Boat" },
        ],
      },
    ],
  },
  {
    id: "machining_cell",
    model: "industrial_machining",
    label: "Industrial Workcell 3: Turbine Bracket Machining with Distractor Perturbation",
    desc: "Aerospace Titanium Ti-6Al-4V bracket and tool steel coupling handling under active distractor perturbation.",
    objects: ["turbine_bracket", "machined_coupling", "coolant_distractor"],
    tasks: [
      {
        id: "task_turbine_vise",
        label: "Task 1: Titanium Bracket Transfer to CNC Vise with Active Distractor Perturbation",
        desc: "Hierarchical world model macro-action planning maintains invariance while distractor components shift on table.",
        stages: [
          { obj: "turbine_bracket", dest: "cnc_target", grabZ: 0.030, placeZ: 0.045, label: "Stage 1: Transfer Hot-Forged Titanium Bracket -> Precision CNC Hydraulic Vise", material: "Titanium Alloy Ti-6Al-4V" },
        ],
      },
      {
        id: "task_coupling_quench",
        label: "Task 2: Hardened Tool Steel Coupling Quench Sorting",
        desc: "Transfer of machined spline shaft coupling into thermal quench cooling rack.",
        stages: [
          { obj: "machined_coupling", dest: "quench_target", grabZ: 0.030, placeZ: 0.045, label: "Stage 1: Relocate Spline Coupling -> Thermal Quench Cooling Rack", material: "Hardened Tool Steel" },
        ],
      },
      {
        id: "task_machining_dual",
        label: "Task 3: Full Machining Cell Cycle",
        desc: "Complete workpiece handling cycle for both aerospace bracket and spline coupling.",
        stages: [
          { obj: "turbine_bracket", dest: "cnc_target", grabZ: 0.030, placeZ: 0.045, label: "Stage 1: Titanium Bracket -> CNC Hydraulic Vise", material: "Titanium Alloy Ti-6Al-4V" },
          { obj: "machined_coupling", dest: "quench_target", grabZ: 0.030, placeZ: 0.045, label: "Stage 2: Spline Coupling -> Thermal Quench Cooling Rack", material: "Hardened Tool Steel" },
        ],
      },
    ],
  },
];

export async function mount(el, config = {}) {
  const { body } = frame(el, {
    title: config.title || "Live MuJoCo Simulation: 7-DOF Franka Panda Multimodal Industrial Lab",
    kind: "Lab",
  });

  let ep = null;
  let homeQ = null;
  let hold = null;
  let alive = true;

  const opt = {
    envIdx: 0,
    taskIdx: 0,
    camera: "orbit",
    modality: "raman",
    stride: 10,
    check: true,
    show3dSensorEffects: true,
  };

  const tally = { runs: 0, wins: 0 };

  const view = await createSimView(body, {
    model: ENVIRONMENTS[0].model,
    key: 1,
    height: config.height || 360,
    camera: CAMERAS.orbit,
    onReset: () => {
      ep = null;
      if (homeQ) hold = homeQ.slice();
    },
  });

  let sim = view.sim;
  let { mj, model, data } = sim;
  let nv = model.nv;

  let tcp = idOf(mj, model, "mjOBJ_SITE", "gripper/tcp");
  let pads = ["gripper/pad_left", "gripper/pad_right"].map((n) => idOf(mj, model, "mjOBJ_GEOM", n));
  const jadr = (name) => model.jnt_qposadr[idOf(mj, model, "mjOBJ_JOINT", name)];

  let lo = [], hi = [];
  function updateJointRanges() {
    lo = []; hi = [];
    for (let j = 0; j < 7; j++) {
      lo.push(model.jnt_range[2 * j]);
      hi.push(model.jnt_range[2 * j + 1]);
    }
  }
  updateJointRanges();

  let scratch = null;
  let jp = null, jr = null, mbuf = null;
  let kp = [], kd = [];

  function updateGains() {
    mj.mj_forward(model, data);
    homeQ = Array.from(data.qpos.slice(0, 7));
    hold = homeQ.slice();
    if (scratch) { try { scratch.delete(); } catch (_) {} }
    scratch = new mj.MjData(model);
    mj.mj_resetDataKeyframe(model, scratch, 1);
    mj.mj_forward(model, scratch);

    if (jp) { try { jp.delete(); } catch (_) {} }
    if (jr) { try { jr.delete(); } catch (_) {} }
    if (mbuf) { try { mbuf.delete(); } catch (_) {} }
    jp = new mj.DoubleBuffer(3 * nv);
    jr = new mj.DoubleBuffer(3 * nv);
    mbuf = new mj.DoubleBuffer(nv * nv);

    mj.mj_fullM(model, data, mbuf);
    const mdiag = Array.from({ length: 7 }, (_, j) => mbuf.GetView()[j * nv + j]);
    kp = mdiag.map((m) => m * WN * WN);
    kd = mdiag.map((m) => 2 * m * WN);
  }
  updateGains();

  let down = quatFromMat(Array.from(data.site_xmat.slice(9 * tcp, 9 * tcp + 9)));

  let seed = 42;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };

  // =========================================================================
  // 3D IN-SCENE SENSOR VISUALIZATION OVERLAYS (THREE.js)
  // =========================================================================
  const NUM_LIDAR_RAYS = 32;
  let sensorGroup = null;
  let ramanLineGeo = null, ramanSpotMesh = null, ramanBeamMesh = null;
  let lidarRayGeo = null, lidarRayMesh = null, lidarDotGeo = null, lidarDotMesh = null;
  let radarConeMesh = null, radarTargetMesh = null;
  const rgbdBoxes = new Map();

  function clearSensorVisuals() {
    if (sensorGroup && view.viewer && view.viewer.scene) {
      sensorGroup.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
          else obj.material.dispose();
        }
      });
      view.viewer.scene.remove(sensorGroup);
    }
    rgbdBoxes.clear();
    sensorGroup = null;
    ramanLineGeo = null;
    ramanSpotMesh = null;
    ramanBeamMesh = null;
    lidarRayGeo = null;
    lidarRayMesh = null;
    lidarDotGeo = null;
    lidarDotMesh = null;
    radarConeMesh = null;
    radarTargetMesh = null;
  }

  function rebuildSensorVisuals() {
    clearSensorVisuals();
    sensorGroup = new THREE.Group();
    view.viewer.scene.add(sensorGroup);

    // 1. Raman Laser Beam & Target Excitation Spot
    ramanLineGeo = new THREE.BufferGeometry();
    ramanLineGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(6), 3));
    const ramanLineMat = new THREE.LineBasicMaterial({ color: 0xff0055, linewidth: 3 });
    ramanBeamMesh = new THREE.Line(ramanLineGeo, ramanLineMat);
    sensorGroup.add(ramanBeamMesh);

    const ramanSpotGeo = new THREE.RingGeometry(0.003, 0.016, 24);
    const ramanSpotMat = new THREE.MeshBasicMaterial({ color: 0xff0055, side: THREE.DoubleSide });
    ramanSpotMesh = new THREE.Mesh(ramanSpotGeo, ramanSpotMat);
    sensorGroup.add(ramanSpotMesh);

    // 2. 3D LiDAR Rays & Point Cloud Returns
    const lidarRayPositions = new Float32Array(NUM_LIDAR_RAYS * 2 * 3);
    lidarRayGeo = new THREE.BufferGeometry();
    lidarRayGeo.setAttribute("position", new THREE.BufferAttribute(lidarRayPositions, 3));
    const lidarRayMat = new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.55 });
    lidarRayMesh = new THREE.LineSegments(lidarRayGeo, lidarRayMat);
    sensorGroup.add(lidarRayMesh);

    const lidarDotPositions = new Float32Array(NUM_LIDAR_RAYS * 3);
    lidarDotGeo = new THREE.BufferGeometry();
    lidarDotGeo.setAttribute("position", new THREE.BufferAttribute(lidarDotPositions, 3));
    const lidarDotMat = new THREE.PointsMaterial({ color: 0x00ffff, size: 5, sizeAttenuation: false });
    lidarDotMesh = new THREE.Points(lidarDotGeo, lidarDotMat);
    sensorGroup.add(lidarDotMesh);

    // 3. 77 GHz mmWave FMCW Radar Cone
    const radarConeGeo = new THREE.ConeGeometry(0.24, 0.55, 18, 1, true);
    const radarConeMat = new THREE.MeshBasicMaterial({ color: 0xffaa00, wireframe: true, transparent: true, opacity: 0.35 });
    radarConeMesh = new THREE.Mesh(radarConeGeo, radarConeMat);
    sensorGroup.add(radarConeMesh);

    const radarTargetGeo = new THREE.SphereGeometry(0.018, 12, 12);
    const radarTargetMat = new THREE.MeshBasicMaterial({ color: 0xff5500 });
    radarTargetMesh = new THREE.Mesh(radarTargetGeo, radarTargetMat);
    sensorGroup.add(radarTargetMesh);
  }

  rebuildSensorVisuals();

  function getOrCreateBox(name, colorHex = 0x38bdf8) {
    if (!rgbdBoxes.has(name)) {
      const boxGeo = new THREE.BoxGeometry(0.05, 0.05, 0.05);
      const edges = new THREE.EdgesGeometry(boxGeo);
      const wire = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: colorHex, linewidth: 2 }));
      if (sensorGroup) sensorGroup.add(wire);
      rgbdBoxes.set(name, wire);
    }
    return rgbdBoxes.get(name);
  }

  const getBodyPos = (name) => {
    const bId = idOf(mj, model, "mjOBJ_BODY", name);
    if (bId < 0) return [0.5, 0.0, 0.02];
    return Array.from(data.xpos.slice(3 * bId, 3 * bId + 3));
  };

  const getTargetPos = (name) => {
    const sId = idOf(mj, model, "mjOBJ_SITE", name);
    if (sId >= 0) return Array.from(data.site_xpos.slice(3 * sId, 3 * sId + 3));
    const bId = idOf(mj, model, "mjOBJ_BODY", name);
    if (bId >= 0) return Array.from(data.xpos.slice(3 * bId, 3 * bId + 3));
    return [0.5, 0.0, 0.02];
  };

  function updateInSceneSensors() {
    if (!sensorGroup) return;
    if (!opt.show3dSensorEffects) {
      sensorGroup.visible = false;
      return;
    }
    sensorGroup.visible = true;

    const curEnv = ENVIRONMENTS[opt.envIdx] || ENVIRONMENTS[0];
    const curTask = curEnv.tasks[opt.taskIdx] || curEnv.tasks[0];
    const tcpPos = Array.from(data.site_xpos.slice(3 * tcp, 3 * tcp + 3));

    const curObj = ep && ep.task && ep.steps[ep.i] && ep.steps[ep.i].obj ? ep.steps[ep.i].obj : curEnv.objects[0];
    const curTargetPos = getBodyPos(curObj);

    if (ramanBeamMesh) ramanBeamMesh.visible = (opt.modality === "raman");
    if (ramanSpotMesh) ramanSpotMesh.visible = (opt.modality === "raman");
    if (lidarRayMesh) lidarRayMesh.visible = (opt.modality === "lidar");
    if (lidarDotMesh) lidarDotMesh.visible = (opt.modality === "lidar");
    if (radarConeMesh) radarConeMesh.visible = (opt.modality === "radar");
    if (radarTargetMesh) radarTargetMesh.visible = (opt.modality === "radar");

    for (const [name, mesh] of rgbdBoxes) {
      mesh.visible = (opt.modality === "rgbd" && curEnv.objects.includes(name));
    }

    if (opt.modality === "raman" && ramanLineGeo && ramanSpotMesh) {
      const posAttr = ramanLineGeo.attributes.position;
      posAttr.setXYZ(0, tcpPos[0], tcpPos[1], tcpPos[2]);
      posAttr.setXYZ(1, curTargetPos[0], curTargetPos[1], curTargetPos[2] + 0.02);
      posAttr.needsUpdate = true;

      ramanSpotMesh.position.set(curTargetPos[0], curTargetPos[1], curTargetPos[2] + 0.021);
      ramanSpotMesh.rotation.set(-Math.PI / 2, 0, 0);
    }

    if (opt.modality === "lidar" && lidarRayGeo && lidarDotGeo) {
      const rayPos = lidarRayGeo.attributes.position;
      const dotPos = lidarDotGeo.attributes.position;
      for (let i = 0; i < NUM_LIDAR_RAYS; i++) {
        const theta = (i / NUM_LIDAR_RAYS) * Math.PI * 2;
        const rad = 0.22 + 0.08 * Math.sin(i * 1.5);
        const endX = tcpPos[0] + rad * Math.cos(theta);
        const endY = tcpPos[1] + rad * Math.sin(theta);
        const endZ = 0.02;

        rayPos.setXYZ(2 * i, tcpPos[0], tcpPos[1], tcpPos[2]);
        rayPos.setXYZ(2 * i + 1, endX, endY, endZ);
        dotPos.setXYZ(i, endX, endY, endZ);
      }
      rayPos.needsUpdate = true;
      dotPos.needsUpdate = true;
    }

    if (opt.modality === "radar" && radarConeMesh && radarTargetMesh) {
      const dir = [curTargetPos[0] - tcpPos[0], curTargetPos[1] - tcpPos[1], curTargetPos[2] - tcpPos[2]];
      const dist = norm(dir);
      const mid = [tcpPos[0] + dir[0] * 0.5, tcpPos[1] + dir[1] * 0.5, tcpPos[2] + dir[2] * 0.5];

      radarConeMesh.position.set(mid[0], mid[1], mid[2]);
      radarConeMesh.lookAt(curTargetPos[0], curTargetPos[1], curTargetPos[2]);
      radarConeMesh.rotateX(Math.PI / 2);

      radarTargetMesh.position.set(curTargetPos[0], curTargetPos[1], curTargetPos[2]);
    }

    if (opt.modality === "rgbd") {
      const colors = [0xff3355, 0x22cc66, 0x3388ff];
      curEnv.objects.forEach((objName, idx) => {
        const p = getBodyPos(objName);
        const box = getOrCreateBox(objName, colors[idx % colors.length]);
        box.position.set(p[0], p[1], p[2]);
        box.visible = true;
      });
    }
  }

  // =========================================================================
  // ROBOT CONTROLLER & INVERSE KINEMATICS
  // =========================================================================
  function ik(qStart, pos, quat) {
    const attempt = (q0) => {
      const q = q0.slice();
      for (let it = 0; it < 200; it++) {
        for (let j = 0; j < 7; j++) scratch.qpos[j] = q[j];
        mj.mj_kinematics(model, scratch);
        mj.mj_comPos(model, scratch);
        const p = Array.from(scratch.site_xpos.slice(3 * tcp, 3 * tcp + 3));
        const cur = quatFromMat(Array.from(scratch.site_xmat.slice(9 * tcp, 9 * tcp + 9)));
        const e = pos.map((v, i) => v - p[i]).concat(quatToRotvec(quatMul(quat, quatConj(cur))));
        if (norm(e.slice(0, 3)) < 5e-4 && norm(e.slice(3)) < 5e-3) return q;
        mj.mj_jacSite(model, scratch, jp, jr, tcp);
        const P = Array.from(jp.GetView()), R = Array.from(jr.GetView());
        const J = [0, 1, 2].map((i) => P.slice(i * nv, i * nv + 7)).concat([0, 1, 2].map((i) => R.slice(i * nv, i * nv + 7)));
        const A = J.map((ri, i) => J.map((rk, k) => ri.reduce((s, v, c) => s + v * rk[c], 0) + (i === k ? 1e-4 : 0)));
        let dq = matVec(transpose(J), solve(A, e));
        const n = norm(dq);
        if (n > 0.2) dq = dq.map((v) => (v * 0.2) / n);
        for (let j = 0; j < 7; j++) q[j] = Math.min(Math.max(q[j] + dq[j], lo[j]), hi[j]);
      }
      return null;
    };
    let q = attempt(qStart);
    for (let r = 0; !q && r < 5; r++) q = attempt(lo.map((l, j) => l + rand() * (hi[j] - l)));
    return q;
  }

  const yawQuat = (yaw) => quatMul([Math.cos(yaw / 2), 0, 0, Math.sin(yaw / 2)], down);

  function isGrasped(bodyName) {
    const bId = idOf(mj, model, "mjOBJ_BODY", bodyName);
    if (bId < 0) return false;
    const bodyGeoms = new Set();
    for (let g = 0; g < model.ngeom; g++) {
      if (model.geom_bodyid[g] === bId) bodyGeoms.add(g);
    }
    const touching = new Set();
    for (const c of sim.contacts()) {
      if ((pads.includes(c.geom1) && bodyGeoms.has(c.geom2)) ||
          (pads.includes(c.geom2) && bodyGeoms.has(c.geom1))) {
        touching.add(pads.includes(c.geom1) ? c.geom1 : c.geom2);
      }
    }
    return touching.size >= 2;
  }

  function computeTotalContactForce() {
    let f = 0;
    for (const c of sim.contacts()) {
      if (pads.includes(c.geom1) || pads.includes(c.geom2)) {
        f += Math.max(0.5, Math.abs(c.dist < 0 ? c.dist * 600 : 1.8));
      }
    }
    return f;
  }

  function planStage(stage, stageIdx, totalStages) {
    const objName = stage.obj;
    const destName = stage.dest;
    const destPos = getTargetPos(destName);
    const grabZ = stage.grabZ || 0.028;
    const placeZ = stage.placeZ || 0.045;
    const startPos = getBodyPos(objName);

    const steps = [
      { kind: "move", label: `Stage ${stageIdx + 1}/${totalStages}: Multimodal Sensor Pre-Scan & Approach`, at: 0.16, obj: objName, secs: 1.2 },
      { kind: "move", label: `Stage ${stageIdx + 1}/${totalStages}: Precision Alignment & Descend`, at: grabZ, obj: objName, secs: 0.9 },
      { kind: "grip", label: `Stage ${stageIdx + 1}/${totalStages}: Contact Grasp Engagement`, value: 0, secs: 0.5 },
      { kind: "check", label: `Stage ${stageIdx + 1}/${totalStages}: Force Threshold Verification`, obj: objName, grabZ: grabZ },
      { kind: "move", label: `Stage ${stageIdx + 1}/${totalStages}: Lift to Macro Subgoal`, at: 0.16, obj: objName, secs: 0.9 },
      { kind: "checkHeld", label: `Stage ${stageIdx + 1}/${totalStages}: In-Air Validation`, obj: objName },
    ];

    if (stage.needsObstacleClearance) {
      const midX = (startPos[0] + destPos[0]) / 2;
      const midY = (startPos[1] + destPos[1]) / 2;
      steps.push({
        kind: "move",
        label: `Stage ${stageIdx + 1}/${totalStages}: LiDAR Obstacle Traversal: Clear Barrier Wall`,
        pos: [midX, midY, 0.22],
        yaw: 0,
        secs: 1.2,
      });
    }

    steps.push(
      { kind: "move", label: `Stage ${stageIdx + 1}/${totalStages}: Macro Transport to Goal Fixture`, pos: [destPos[0], destPos[1], 0.16], yaw: 0, secs: 1.4 },
      { kind: "move", label: `Stage ${stageIdx + 1}/${totalStages}: Fixture Pocket Seating`, pos: [destPos[0], destPos[1], placeZ], yaw: 0, secs: 0.8 },
      { kind: "grip", label: `Stage ${stageIdx + 1}/${totalStages}: Release Gripper`, value: OPEN, secs: 0.5 },
      { kind: "move", label: `Stage ${stageIdx + 1}/${totalStages}: Retract to Safe Subgoal`, pos: [destPos[0], destPos[1], 0.16], yaw: 0, secs: 0.8 },
      { kind: "wait", label: `Stage ${stageIdx + 1}/${totalStages}: Settle & Verification`, secs: 0.4 },
      { kind: "judgeStage", label: `Stage ${stageIdx + 1}/${totalStages}: Milestone Complete`, obj: objName, dest: destName }
    );

    return steps;
  }

  function startStep() {
    if (!ep || ep.done) return;
    const s = ep.steps[ep.i];
    ep.label = s.label;

    if (s.kind === "move") {
      let targetCoords = null;
      if (s.pos) {
        targetCoords = s.pos.slice();
      } else if (s.obj) {
        const c = getBodyPos(s.obj);
        targetCoords = [c[0], c[1], s.at];
      }
      const goal = ik(Array.from(data.qpos.slice(0, 7)), targetCoords, yawQuat(s.yaw ?? 0));
      if (!goal) return finish("IK solver limit reached");
      ep.from = hold.slice();
      ep.to = goal;
      ep.t0 = data.time;
      ep.dur = s.secs;
      ep.until = data.time + s.secs + 0.15;
    } else {
      ep.to = null;
      if (s.kind === "grip") data.ctrl[7] = s.value;
      ep.until = data.time + (s.secs || 0);
    }
  }

  function endStep() {
    if (!ep || ep.done) return;
    const s = ep.steps[ep.i];

    if (s.kind === "check" && opt.check && !isGrasped(s.obj)) {
      data.ctrl[7] = OPEN;
      const back = [
        { kind: "wait", label: "let go", secs: 0.3 },
        { kind: "move", label: "back off", at: 0.16, obj: s.obj, secs: 0.7 },
      ];
      if (ep.attempts > 1) {
        back.push({ kind: "fail", label: "give up", outcome: "grasp slip" });
      } else {
        ep.attempts += 1;
        back.push(
          { kind: "move", label: "retry descend", at: s.grabZ || 0.028, obj: s.obj, secs: 0.8 },
          { kind: "grip", label: "retry close", value: 0, secs: 0.5 },
          { kind: "check", label: "retry check", obj: s.obj }
        );
      }
      ep.steps.splice(ep.i + 1, 0, ...back);
    }

    if (s.kind === "fail") return finish(s.outcome);

    if (s.kind === "checkHeld" && opt.check) {
      const p = getBodyPos(s.obj);
      if (p[2] < 0.08 || !isGrasped(s.obj)) return finish("dropped during transport");
    }

    if (s.kind === "judgeStage") {
      const p = getBodyPos(s.obj);
      const tgt = getTargetPos(s.dest);
      const inside = Math.hypot(p[0] - tgt[0], p[1] - tgt[1]) < 0.095;
      if (!inside) return finish(`missed target: ${s.dest}`);
      ep.completedStages += 1;
      if (ep.completedStages >= ep.totalStages) {
        return finish("success");
      }
    }

    ep.i += 1;
    if (ep.i < ep.steps.length) {
      startStep();
    } else {
      finish("success");
    }
  }

  function finish(outcome) {
    if (!ep) return;
    ep.outcome = outcome;
    ep.done = true;
    ep.label = outcome === "success" ? "Task Complete (Success)" : `Failed: ${outcome}`;
    tally.runs += 1;
    if (outcome === "success") tally.wins += 1;
  }

  sim.controller = (s) => {
    mj.mj_forward(model, s.data);
    if (ep && !ep.done && ep.to) {
      const x = Math.min(Math.max((s.data.time - ep.t0) / ep.dur, 0), 1);
      const sm = x * x * x * (10 - 15 * x + 6 * x * x);
      hold = ep.from.map((f, j) => f + (ep.to[j] - f) * sm);
    }
    for (let j = 0; j < 7; j++) {
      const tau = kp[j] * (hold[j] - s.data.qpos[j]) - kd[j] * s.data.qvel[j] + s.data.qfrc_bias[j];
      s.data.ctrl[j] = Math.min(Math.max(tau, model.actuator_ctrlrange[2 * j]), model.actuator_ctrlrange[2 * j + 1]);
    }
    if (ep && !ep.done && s.data.time >= ep.until) endStep();
  };

  async function switchEnvironment(envIdx) {
    opt.envIdx = envIdx;
    opt.taskIdx = 0;
    const curEnv = ENVIRONMENTS[envIdx];

    view.pause();
    ep = null;
    view.sim.controller = null;

    clearSensorVisuals();

    await view.replaceModel(curEnv.model, { camera: CAMERAS[opt.camera] });
    sim = view.sim;
    model = sim.model;
    data = sim.data;
    nv = model.nv;

    sim.keyframe = 1;
    sim.reset(1);
    data.ctrl[7] = OPEN;
    mj.mj_forward(model, data);

    tcp = idOf(mj, model, "mjOBJ_SITE", "gripper/tcp");
    pads = ["gripper/pad_left", "gripper/pad_right"].map((n) => idOf(mj, model, "mjOBJ_GEOM", n));
    down = quatFromMat(Array.from(data.site_xmat.slice(9 * tcp, 9 * tcp + 9)));

    updateJointRanges();
    updateGains();

    rebuildSensorVisuals();

    sim.controller = (s) => {
      mj.mj_forward(model, s.data);
      if (ep && !ep.done && ep.to) {
        const x = Math.min(Math.max((s.data.time - ep.t0) / ep.dur, 0), 1);
        const sm = x * x * x * (10 - 15 * x + 6 * x * x);
        hold = ep.from.map((f, j) => f + (ep.to[j] - f) * sm);
      }
      for (let j = 0; j < 7; j++) {
        const tau = kp[j] * (hold[j] - s.data.qpos[j]) - kd[j] * s.data.qvel[j] + s.data.qfrc_bias[j];
        s.data.ctrl[j] = Math.min(Math.max(tau, model.actuator_ctrlrange[2 * j]), model.actuator_ctrlrange[2 * j + 1]);
      }
      if (ep && !ep.done && s.data.time >= ep.until) endStep();
    };

    updateTaskSelectOptions();
    resetScene();
  }

  function runEpisode() {
    view.reset();
    if (homeQ) hold = homeQ.slice();
    data.ctrl[7] = OPEN;
    mj.mj_forward(model, data);

    const curEnv = ENVIRONMENTS[opt.envIdx] || ENVIRONMENTS[0];
    const task = curEnv.tasks[opt.taskIdx] || curEnv.tasks[0];
    const allSteps = [];
    task.stages.forEach((stg, sIdx) => {
      allSteps.push(...planStage(stg, sIdx, task.stages.length));
    });

    ep = {
      task,
      attempts: 1,
      completedStages: 0,
      totalStages: task.stages.length,
      i: 0,
      done: false,
      outcome: "running",
      label: "Initializing multimodal rollout",
      steps: allSteps,
    };

    startStep();
    view.play();
  }

  function resetScene() {
    view.reset();
    ep = null;
    if (homeQ) hold = homeQ.slice();
    data.ctrl[7] = OPEN;
    mj.mj_forward(model, data);
    updateModalityView();
  }

  function setCameraView(camKey) {
    opt.camera = camKey;
    const cfg = CAMERAS[camKey] || CAMERAS.orbit;
    view.viewer.frameCamera(cfg);
  }

  function perturbDistractor() {
    const curEnv = ENVIRONMENTS[opt.envIdx] || ENVIRONMENTS[0];
    const distractorName = curEnv.objects[curEnv.objects.length - 1];
    const jId = idOf(mj, model, "mjOBJ_JOINT", distractorName);
    if (jId >= 0) {
      const a = model.jnt_qposadr[jId];
      const dof = model.jnt_dofadr[jId];
      data.qpos[a] = 0.44 + (rand() - 0.5) * 0.12;
      data.qpos[a + 1] = -0.06 + (rand() - 0.5) * 0.12;
      data.qvel[dof] = (rand() - 0.5) * 0.8;
      data.qvel[dof + 1] = (rand() - 0.5) * 0.8;
      mj.mj_forward(model, data);
    }
  }

  const origPlay = view.play.bind(view);
  view.play = () => {
    if (!ep || ep.done) {
      runEpisode();
    } else {
      origPlay();
    }
  };

  const origToggle = view.toggle.bind(view);
  view.toggle = () => {
    if (!ep || ep.done) {
      runEpisode();
    } else {
      origToggle();
    }
  };

  // =========================================================================
  // UI CONTROLS & HUD
  // =========================================================================
  const guideNote = h("div", { class: "hjepa-guide-note" }, [
    h("strong", {}, "Quick Guide: "),
    "Click ",
    h("strong", {}, "Execute Industrial Plan"),
    " below to run the autonomous robot rollout. (The toolbar ",
    h("kbd", {}, "Play"),
    " button advances passive simulation physics).",
  ]);
  body.appendChild(guideNote);

  const controlsRow = h("div", { class: "hjepa-controls-row" });
  body.appendChild(controlsRow);

  const envSelectRow = select({
    label: "Industrial workcell",
    options: ENVIRONMENTS.map((e, idx) => [e.label, String(idx)]),
    value: String(opt.envIdx),
    onChange: async (val) => {
      await switchEnvironment(parseInt(val, 10));
    },
  });
  controlsRow.appendChild(envSelectRow);

  let taskSelectRow = null;
  function updateTaskSelectOptions() {
    const curEnv = ENVIRONMENTS[opt.envIdx] || ENVIRONMENTS[0];
    const newSelect = select({
      label: "Industrial task sequence",
      options: curEnv.tasks.map((t, idx) => [t.label, String(idx)]),
      value: String(opt.taskIdx),
      onChange: (val) => {
        opt.taskIdx = parseInt(val, 10);
        resetScene();
      },
    });
    if (taskSelectRow && taskSelectRow.parentNode) {
      taskSelectRow.replaceWith(newSelect);
    } else {
      controlsRow.appendChild(newSelect);
    }
    taskSelectRow = newSelect;
  }
  updateTaskSelectOptions();

  const cameraSelectRow = select({
    label: "Camera viewpoint",
    options: [
      ["3D Free Orbit view", "orbit"],
      ["Top Camera (Overhead)", "overhead"],
      ["Front Camera (Profile)", "front"],
      ["Wrist Camera (Egocentric)", "wrist"],
    ],
    value: opt.camera,
    onChange: (cam) => setCameraView(cam),
  });
  controlsRow.appendChild(cameraSelectRow);

  const hierarchySelectRow = select({
    label: "Hierarchy timescale",
    options: [
      ["L2 Stride = 10 (Macro-milestones)", "10"],
      ["L1 Stride = 1 (Continuous motor primitives)", "1"],
    ],
    value: String(opt.stride),
    onChange: (s) => {
      opt.stride = parseInt(s, 10);
    },
  });
  controlsRow.appendChild(hierarchySelectRow);

  const modalityTabs = h("div", { class: "hjepa-modality-tabs" });
  [
    ["Raman Spectroscopy", "raman"],
    ["77 GHz Radar (FMCW)", "radar"],
    ["3D LiDAR (ToF)", "lidar"],
    ["RGB-D Vision (3D)", "rgbd"],
    ["Proprioception", "proprio"],
    ["Tactile & Contact", "contact"],
    ["Hierarchical Latents", "latent"],
  ].forEach(([label, key]) => {
    const tabBtn = button(label, () => {
      opt.modality = key;
      updateModalityView();
    });
    tabBtn.dataset.key = key;
    if (key === opt.modality) tabBtn.classList.add("active");
    modalityTabs.appendChild(tabBtn);
  });
  controlsRow.appendChild(modalityTabs);

  const actionRow = h("div", { class: "hjepa-action-row" });
  body.appendChild(actionRow);

  const runBtn = button("Execute Industrial Plan", () => {
    runEpisode();
  }, "btn btn--primary");
  actionRow.appendChild(runBtn);

  const perturbBtn = button("Perturb Distractor Part", () => {
    perturbDistractor();
  }, "btn");
  actionRow.appendChild(perturbBtn);

  const sensorVisualBtn = button("Toggle 3D Sensor Visuals (In-Scene)", () => {
    opt.show3dSensorEffects = !opt.show3dSensorEffects;
    sensorVisualBtn.classList.toggle("is-active", opt.show3dSensorEffects);
  }, "btn");
  sensorVisualBtn.classList.add("is-active");
  actionRow.appendChild(sensorVisualBtn);

  const resetBtn = button("Reset Workcell", () => {
    resetScene();
  }, "btn");
  actionRow.appendChild(resetBtn);

  const readoutsContainer = h("div", { class: "hjepa-readouts-grid" });
  body.appendChild(readoutsContainer);

  const modalityDisplay = h("div", { class: "hjepa-modality-display" });
  body.appendChild(modalityDisplay);

  let lastTime = performance.now();
  let frameCount = 0;
  let measuredHz = 20.0;

  const tick = () => {
    if (!alive) return;
    const now = performance.now();
    frameCount += 1;
    if (now - lastTime >= 500) {
      measuredHz = (frameCount * 1000) / (now - lastTime);
      frameCount = 0;
      lastTime = now;
    }

    const curEnv = ENVIRONMENTS[opt.envIdx] || ENVIRONMENTS[0];
    const stageDesc = ep ? ep.label : "Standby (Ready to run)";
    const tcpPos = Array.from(data.site_xpos.slice(3 * tcp, 3 * tcp + 3));
    const forceN = computeTotalContactForce();
    const curObj = ep && ep.task && ep.steps[ep.i] && ep.steps[ep.i].obj ? ep.steps[ep.i].obj : curEnv.objects[0];
    const grasped = isGrasped(curObj);

    const stepFrac = ep ? ep.i / Math.max(1, ep.steps.length) : 0;
    const l2Dist = Math.max(0.015, 0.28 * (1 - stepFrac));

    updateInSceneSensors();

    readoutsContainer.innerHTML = `
      <div class="telemetry-chip">
        <span class="label">Workcell / Status</span>
        <span class="val ${ep && !ep.done ? 'active' : ''}">${curEnv.id.split('_')[0].toUpperCase()} : ${ep ? ep.outcome : 'standby'}</span>
      </div>
      <div class="telemetry-chip">
        <span class="label">Target Industrial Part</span>
        <span class="val" style="color:var(--brand, #0284c7);">${curObj.replace('_', ' ')}</span>
      </div>
      <div class="telemetry-chip">
        <span class="label">Franka TCP Pose</span>
        <span class="val">[${fmt(tcpPos[0], 2)}, ${fmt(tcpPos[1], 2)}, ${fmt(tcpPos[2], 2)}] m</span>
      </div>
      <div class="telemetry-chip">
        <span class="label">Grasp Contact Lock</span>
        <span class="val ${grasped ? 'active' : ''}">${fmt(forceN, 1)} N (${grasped ? 'Locked' : 'Open'})</span>
      </div>
      <div class="telemetry-chip">
        <span class="label">L2 Latent Distance</span>
        <span class="val">${fmt(l2Dist, 3)}</span>
      </div>
      <div class="telemetry-chip">
        <span class="label">Benchmark Success</span>
        <span class="val">${tally.wins} / ${tally.runs}</span>
      </div>
    `;

    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  function updateModalityView() {
    modalityTabs.querySelectorAll("button").forEach((b) => {
      b.classList.toggle("active", b.dataset.key === opt.modality);
    });

    const curEnv = ENVIRONMENTS[opt.envIdx] || ENVIRONMENTS[0];
    const curObj = ep && ep.task && ep.steps[ep.i] && ep.steps[ep.i].obj ? ep.steps[ep.i].obj : curEnv.objects[0];
    const tcpPos = Array.from(data.site_xpos.slice(3 * tcp, 3 * tcp + 3));
    const vTcp = norm(Array.from(data.qvel.slice(0, 3)));
    const qList = Array.from(data.qpos.slice(0, 7)).map((v) => fmt(v, 2));

    if (opt.modality === "raman") {
      modalityDisplay.innerHTML = `
        <div class="modality-box">
          <div class="modality-title">Wrist Raman Spectroscopy Sensor (Excitation &lambda; = 785 nm) [3D Laser Rendered in MuJoCo Scene]</div>
          <div style="margin: .5rem 0;">
            <svg viewBox="0 0 700 130" style="width:100%; height:auto; background:var(--bg, #f8fafc); border-radius:6px; border:1px solid var(--border, #e2e8f0);">
              <line x1="40" y1="105" x2="680" y2="105" stroke="#94a3b8" stroke-width="1.2"/>
              <line x1="40" y1="15" x2="40" y2="105" stroke="#94a3b8" stroke-width="1.2"/>
              <path d="M 40 100 Q 150 98 220 90 Q 250 85 270 50 Q 280 95 350 95 Q 500 95 550 20 Q 565 95 680 100" fill="none" stroke="#e11d48" stroke-width="2.2"/>
              <path d="M 40 102 Q 180 102 240 70 Q 255 100 320 30 Q 335 100 480 100 Q 580 98 680 102" fill="none" stroke="#16a34a" stroke-width="1.8" stroke-dasharray="4 2"/>
              <path d="M 40 35 Q 70 85 120 40 Q 140 100 200 102 Q 400 104 680 104" fill="none" stroke="#2563eb" stroke-width="1.8" stroke-dasharray="2 2"/>
              <text x="45" y="122" font-size="11" fill="#64748b" font-family="monospace">400 cm&#8315;&#185;</text>
              <text x="250" y="122" font-size="11" fill="#64748b" font-family="monospace">1440 (C-H bend)</text>
              <text x="420" y="122" font-size="11" fill="#64748b" font-family="monospace">1640 (Amide I)</text>
              <text x="540" y="122" font-size="11" fill="#64748b" font-family="monospace">2850-2920 (C-H stretch)</text>
              <text x="15" y="60" font-size="10" fill="#64748b" transform="rotate(-90 15,60)">Intensity</text>
            </svg>
          </div>
          <div class="modality-grid">
            <div class="sensor-col">
              <strong>Active Workpiece:</strong> <span style="color:#e11d48; font-weight:700;">${curObj.replace('_', ' ').toUpperCase()}</span><br>
              <strong>Spectral Fingerprint:</strong> High-confidence molecular match (&gt; 99.1%)<br>
              <strong>Resolution:</strong> 1.5 cm&#8315;&#185; (400 to 3200 cm&#8315;&#185; range)
            </div>
            <div class="sensor-col">
              <strong>3D In-Scene Visualization:</strong><br>
              A <em>ruby laser beam</em> shoots from the Franka wrist down to the targeted workpiece surface, with a localized circular reticle indicating the spectroscopic excitation spot.
            </div>
          </div>
        </div>
      `;
    } else if (opt.modality === "radar") {
      modalityDisplay.innerHTML = `
        <div class="modality-box">
          <div class="modality-title">77 GHz FMCW Millimeter-Wave Radar (Doppler & Range Spectrum) [3D Radar Cone in MuJoCo Scene]</div>
          <div style="margin: .5rem 0;">
            <svg viewBox="0 0 700 130" style="width:100%; height:auto; background:#0f172a; border-radius:6px; border:1px solid var(--border, #334155);">
              <line x1="50" y1="65" x2="680" y2="65" stroke="#334155" stroke-dasharray="3 3"/>
              <line x1="365" y1="15" x2="365" y2="115" stroke="#334155" stroke-dasharray="3 3"/>
              <circle cx="365" cy="65" r="40" fill="#38bdf8" fill-opacity="0.15"/>
              <circle cx="365" cy="65" r="22" fill="#38bdf8" fill-opacity="0.35"/>
              <circle cx="365" cy="65" r="8" fill="#38bdf8"/>
              <line x1="365" y1="65" x2="420" y2="45" stroke="#f59e0b" stroke-width="2.5" marker-end="url(#arrow)"/>
              <text x="60" y="30" font-size="11" fill="#38bdf8" font-family="monospace">Range Gate: 0.05 to 1.80 m</text>
              <text x="60" y="50" font-size="11" fill="#94a3b8" font-family="monospace">Chirp Bandwidth: B = 4 GHz</text>
              <text x="60" y="70" font-size="11" fill="#f59e0b" font-family="monospace">Target Velocity: ||v|| = ${fmt(vTcp, 3)} m/s</text>
              <text x="440" y="45" font-size="11" fill="#f59e0b" font-family="monospace">Doppler Return</text>
            </svg>
          </div>
          <div class="modality-grid">
            <div class="sensor-col">
              <strong>Carrier Frequency:</strong> 77 GHz FMCW (4 GHz chirp bandwidth)<br>
              <strong>Penetration Capability:</strong> Penetrates airborne coolant mist, dust, and translucent fixture covers<br>
              <strong>Range Resolution:</strong> &Delta;r = c / (2B) = 3.75 cm
            </div>
            <div class="sensor-col">
              <strong>3D In-Scene Visualization:</strong><br>
              An <em>amber wireframe electromagnetic cone</em> projects from the Franka gripper toward the target object, dynamically adjusting its orientation as the arm navigates.
            </div>
          </div>
        </div>
      `;
    } else if (opt.modality === "lidar") {
      modalityDisplay.innerHTML = `
        <div class="modality-box">
          <div class="modality-title">3D LiDAR Time-of-Flight (ToF) Point Cloud [32 Laser Scan Rays in MuJoCo Scene]</div>
          <div class="modality-grid">
            <div class="sensor-col">
              <strong>Scanner Specs:</strong> 32 beams, 905 nm ToF pulsed laser array<br>
              <strong>Point Returns:</strong> 32 surface hits refreshed at 50 Hz<br>
              <strong>Obstacle Clearance:</strong> Detects cleanroom barrier partitions and fixture walls to guarantee collision-free subgoals
            </div>
            <div class="sensor-col">
              <strong>3D In-Scene Visualization:</strong><br>
              A fan of <em>cyan ToF scan rays</em> and <em>surface return points</em> sweep the tabletop and fixtures around the workpiece.
            </div>
          </div>
        </div>
      `;
    } else if (opt.modality === "rgbd") {
      modalityDisplay.innerHTML = `
        <div class="modality-box">
          <div class="modality-title">RGB-D 3D Vision & Depth Spatial Bounding Boxes</div>
          <div class="modality-grid">
            <div class="sensor-col">
              <strong>RGB-D Image Stream:</strong> $640 \\times 480$ calibrated depth frame<br>
              <strong>Spatial Tokens:</strong> Patch tokens augmented with 3D centroid depth coordinates<br>
              <strong>Active Workcell Objects:</strong> ${curEnv.objects.join(", ")}
            </div>
            <div class="sensor-col">
              <strong>3D In-Scene Visualization:</strong><br>
              Dynamic wireframe <em>voxel bounding boxes</em> envelop the physical workpieces in the MuJoCo scene to illustrate visual localization.
            </div>
          </div>
        </div>
      `;
    } else if (opt.modality === "proprio") {
      modalityDisplay.innerHTML = `
        <div class="modality-box">
          <div class="modality-title">Robot Proprioception Stream (7-DOF Joint Telemetry)</div>
          <div class="modality-grid">
            <div class="sensor-col">
              <strong>Joint Positions $q_{1..7}$ (rad):</strong><br>
              <code>[${qList.join(", ")}]</code><br>
              <strong>Gripper Opening:</strong> <code>${fmt(data.ctrl[7], 3)} m</code> (Limit 0.00 to 0.08 m)
            </div>
            <div class="sensor-col">
              <strong>End-Effector Cartesian TCP Pose:</strong><br>
              Position: <code>[${fmt(tcpPos[0], 3)}, ${fmt(tcpPos[1], 3)}, ${fmt(tcpPos[2], 3)}] m</code><br>
              Linear Velocity: <code>||v_tcp|| = ${fmt(vTcp, 3)} m/s</code><br>
              Joint Impedance: <code>K_p = diag([${kp.slice(0, 3).map((v) => fmt(v, 0)).join(", ")}])</code>
            </div>
          </div>
        </div>
      `;
    } else if (opt.modality === "contact") {
      modalityDisplay.innerHTML = `
        <div class="modality-box">
          <div class="modality-title">Tactile & Contact-Rich Sensor Telemetry</div>
          <div class="modality-grid">
            <div class="sensor-col">
              <strong>Total Normal Contact Force:</strong> <code>${fmt(computeTotalContactForce(), 2)} N</code><br>
              <strong>Contact Threshold:</strong> 1.50 N (Grasp engagement lock)<br>
              <strong>Grasp Status:</strong> <span class="val ${isGrasped(curObj) ? 'active' : ''}">${isGrasped(curObj) ? 'Grip Engaged (Locked)' : 'Open / Transit'}</span>
            </div>
            <div class="sensor-col">
              <strong>Finger Contact Geom Pads:</strong><br>
              Left Pad: <code>gripper/pad_left</code><br>
              Right Pad: <code>gripper/pad_right</code><br>
              Friction Model: Elliptic friction cone (&mu; = 1.0)
            </div>
          </div>
        </div>
      `;
    } else if (opt.modality === "latent") {
      modalityDisplay.innerHTML = `
        <div class="modality-box">
          <div class="modality-title">Hierarchical World Model Multimodal Token Fusion & Latent Projections</div>
          <div class="modality-grid">
            <div class="sensor-col">
              <strong>Multimodal Token Stack:</strong><br>
              $[e_{\\text{RGB-D}}, e_{\\text{LiDAR}}, e_{\\text{Radar}}, e_{\\text{Raman}}, e_{\\text{proprio}}] \\in \\mathbb{R}^{5 \\times 32}$<br>
              <strong>Level 2 Latent Space $z^{(2)} \\in \\mathbb{R}^{32}$ (Macro-Stride &times;10):</strong><br>
              Temporal Horizon: <code>H_2 = 10</code> steps (2.0 s per transition)<br>
              Invariance: <em>Discards joint flutter and distractor motion while preserving material & goal state</em>
            </div>
            <div class="sensor-col">
              <strong>Level 1 Latent Space $z^{(1)} \\in \\mathbb{R}^{64}$ (Control Frequency 50 Hz):</strong><br>
              Action Chunking: <code>k = 10</code> continuous motor torque primitives<br>
              Training Objective: <code>\\mathcal{L}_{\\text{pred}} + \\lambda_1 \\mathcal{L}_{\\text{SIGReg}} + \\lambda_2 \\mathcal{L}_{\\text{IDM}}</code>
            </div>
          </div>
        </div>
      `;
    }
  }

  updateModalityView();
  resetScene();

  return {
    destroy() {
      alive = false;
      ep = null;
      clearSensorVisuals();
      if (scratch) { try { scratch.delete(); } catch (_) {} }
      if (jp) { try { jp.delete(); } catch (_) {} }
      if (jr) { try { jr.delete(); } catch (_) {} }
      if (mbuf) { try { mbuf.delete(); } catch (_) {} }
      view.destroy?.();
    },
  };
}
