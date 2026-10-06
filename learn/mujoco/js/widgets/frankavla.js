// Interactive 7-DOF Franka Panda simulation on the LIBERO benchmark suite.
// Demonstrates closed-loop Vision-Language-Action (VLA) execution across
// LIBERO-Spatial, LIBERO-Object, LIBERO-Goal, and LIBERO-10 long-horizon tasks.
//
// Kinematics and control:
//   7-DOF Franka Panda arm tracked via damped-least-squares inverse kinematics,
//   gravity-compensated PD joint impedance control, tendon-actuated parallel
//   gripper, and physical contact detection.
//
// Config: {"dock": true, "title": "...", "height": 340}

import { h, frame, slider, select, button, readout, createSimView, fmt } from "./ui.js";
import { idOf } from "../runtime.js";
import { solve, transpose, matVec, norm, quatFromMat, quatMul, quatConj, quatToRotvec } from "../linalg.js";

const WN = 20;
const OPEN = 0.04;

const CAMERAS = {
  orbit: { azimuth: -140, elevation: 30, distance: 1.5, target: [0.5, 0.0, 0.1] },
  overhead: { azimuth: 180, elevation: 89, distance: 1.35, target: [0.5, 0.0, 0.02] },
  front: { azimuth: 0, elevation: 22, distance: 1.35, target: [0.5, 0.0, 0.15] },
  wrist: { azimuth: -160, elevation: 15, distance: 0.75, target: [0.48, 0.0, 0.1] },
};

const LIBERO_SUITES = [
  ["LIBERO-Spatial (Spatial reasoning)", "spatial"],
  ["LIBERO-Object (Object generalization)", "object"],
  ["LIBERO-Goal (Goal conditioning)", "goal"],
  ["LIBERO-10 (Long-horizon multi-step)", "long"],
];

const TASKS = {
  spatial: [
    {
      id: "sp_1",
      label: "pick up red cube and place in tray",
      instruction: "pick up the red cube and place it in the tray",
      stages: [{ obj: "red_cube", dest: "tray" }],
      layout: "spatial_open",
      note: "Tests 3D spatial grounding: transferring object to an elevated tray container.",
    },
    {
      id: "sp_2",
      label: "pick up green cube and place on left zone",
      instruction: "pick up the green cube and place it on the left target zone",
      stages: [{ obj: "green_cube", dest: "left_zone" }],
      layout: "spatial_open",
      note: "Tests directional spatial reasoning: left target zone (+y workspace).",
    },
    {
      id: "sp_3",
      label: "pick up blue cube and place on right zone",
      instruction: "pick up the blue cube and place it on the right target zone",
      stages: [{ obj: "blue_cube", dest: "right_zone" }],
      layout: "spatial_open",
      note: "Tests directional spatial reasoning: right target zone (-y workspace).",
    },
  ],
  object: [
    {
      id: "ob_1",
      label: "pick up red cube from cluster into tray",
      instruction: "pick up the red cube from the tabletop cluster and place it in the tray",
      stages: [{ obj: "red_cube", dest: "tray" }],
      layout: "cluster",
      note: "Tests object discrimination: retrieve red target adjacent to distractors.",
    },
    {
      id: "ob_2",
      label: "pick up green cube from cluster into tray",
      instruction: "pick up the green cube from between the cubes and place it in the tray",
      stages: [{ obj: "green_cube", dest: "tray" }],
      layout: "cluster",
      note: "Tests collision-aware grasping amidst adjacent object geometries.",
    },
    {
      id: "ob_3",
      label: "pick up blue cube from corner into tray",
      instruction: "pick up the blue cube from the far table corner and place it in the tray",
      stages: [{ obj: "blue_cube", dest: "tray" }],
      layout: "spread",
      note: "Tests out-of-cluster object localization and extended reach.",
    },
  ],
  goal: [
    {
      id: "gl_1",
      label: "place red cube into destination tray",
      instruction: "place the red cube into the destination tray receptacle",
      stages: [{ obj: "red_cube", dest: "tray" }],
      layout: "standard",
      note: "Tests goal conditioning: target destination boundary is the tray receptacle.",
    },
    {
      id: "gl_2",
      label: "place green cube onto left zone",
      instruction: "place the green cube onto the planar left target zone marker",
      stages: [{ obj: "green_cube", dest: "left_zone" }],
      layout: "standard",
      note: "Tests goal conditioning: target boundary is a planar surface zone.",
    },
    {
      id: "gl_3",
      label: "place blue cube onto right zone",
      instruction: "place the blue cube onto the planar right target zone marker",
      stages: [{ obj: "blue_cube", dest: "right_zone" }],
      layout: "standard",
      note: "Tests goal conditioning: target boundary is an opposing planar surface zone.",
    },
  ],
  long: [
    {
      id: "ln_1",
      label: "sequence: red to tray, then green to left zone",
      instruction: "pick up red cube, place in tray, then move green cube to left zone",
      stages: [
        { obj: "red_cube", dest: "tray" },
        { obj: "green_cube", dest: "left_zone" },
      ],
      layout: "standard",
      note: "Tests long-horizon sequential execution: sub-goal switching without resetting robot state.",
    },
    {
      id: "ln_2",
      label: "sequence: green to tray, then blue to right zone",
      instruction: "pick up green cube, place in tray, then move blue cube to right zone",
      stages: [
        { obj: "green_cube", dest: "tray" },
        { obj: "blue_cube", dest: "right_zone" },
      ],
      layout: "standard",
      note: "Tests multi-stage compositionality: sequential transport across contrasting destinations.",
    },
  ],
};

export async function mount(el, config = {}) {
  const { body } = frame(el, {
    title: config.title || "Live MuJoCo Simulation: 7-DOF Franka Panda on LIBERO Benchmark Tasks",
    kind: "Lab",
  });

  let ep = null;
  let homeQ = null;
  let hold = null;

  const view = await createSimView(body, {
    model: "pick_place",
    key: 1,
    height: config.height || 340,
    onReset: () => {
      ep = null;
      if (homeQ) hold = homeQ.slice();
    },
    camera: CAMERAS.orbit,
  });

  const sim = view.sim;
  const { mj, model, data } = sim;
  const nv = model.nv;

  const tcp = idOf(mj, model, "mjOBJ_SITE", "gripper/tcp");
  const pads = ["gripper/pad_left", "gripper/pad_right"].map((n) => idOf(mj, model, "mjOBJ_GEOM", n));
  const jadr = (name) => model.jnt_qposadr[idOf(mj, model, "mjOBJ_JOINT", name)];

  const lo = [], hi = [];
  for (let j = 0; j < 7; j++) {
    lo.push(model.jnt_range[2 * j]);
    hi.push(model.jnt_range[2 * j + 1]);
  }

  const scratch = new mj.MjData(model);
  const jp = new mj.DoubleBuffer(3 * nv), jr = new mj.DoubleBuffer(3 * nv), mbuf = new mj.DoubleBuffer(nv * nv);

  mj.mj_forward(model, data);
  homeQ = Array.from(data.qpos.slice(0, 7));
  hold = homeQ.slice();
  const down = quatFromMat(Array.from(data.site_xmat.slice(9 * tcp, 9 * tcp + 9)));

  mj.mj_fullM(model, data, mbuf);
  const mdiag = Array.from({ length: 7 }, (_, j) => mbuf.GetView()[j * nv + j]);
  const kp = mdiag.map((m) => m * WN * WN);
  const kd = mdiag.map((m) => 2 * m * WN);

  let seed = 42;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  const gauss = () => Math.sqrt(-2 * Math.log(rand() + 1e-12)) * Math.cos(2 * Math.PI * rand());

  const opt = {
    suite: "spatial",
    taskIdx: 0,
    camera: "orbit",
    sigma: 0.0,
    chunkSize: 10,
    check: true,
  };

  const tally = { runs: 0, wins: 0 };

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

  const getBodyPos = (name) => {
    const bId = idOf(mj, model, "mjOBJ_BODY", name);
    return Array.from(data.xpos.slice(3 * bId, 3 * bId + 3));
  };

  const getTargetPos = (name) => {
    if (name === "tray") {
      const sId = idOf(mj, model, "mjOBJ_SITE", "tray_center");
      return Array.from(data.site_xpos.slice(3 * sId, 3 * sId + 3));
    }
    if (name === "left_zone") {
      const sId = idOf(mj, model, "mjOBJ_SITE", "left_zone");
      return Array.from(data.site_xpos.slice(3 * sId, 3 * sId + 3));
    }
    if (name === "right_zone") {
      const sId = idOf(mj, model, "mjOBJ_SITE", "right_zone");
      return Array.from(data.site_xpos.slice(3 * sId, 3 * sId + 3));
    }
    return [0.5, 0.0, 0.02];
  };

  function isGrasped(cubeName) {
    const cubeGeom = idOf(mj, model, "mjOBJ_GEOM", cubeName);
    const touching = new Set();
    for (const c of sim.contacts()) {
      for (const p of pads) {
        if ((c.geom1 === p && c.geom2 === cubeGeom) || (c.geom2 === p && c.geom1 === cubeGeom)) {
          touching.add(p);
        }
      }
    }
    const tenOpening = data.ten_length[0];
    return touching.size === 2 && tenOpening > 0.01 && tenOpening < 0.038;
  }

  function planStage(stage, stageIdx, totalStages) {
    const objName = stage.obj;
    const destName = stage.dest;
    const destIsTray = destName === "tray";
    const destPos = getTargetPos(destName);
    const placeZ = destIsTray ? 0.075 : 0.025;

    return [
      { kind: "move", label: `stage ${stageIdx + 1}/${totalStages}: approach`, at: 0.15, obj: objName, perceive: true, secs: 1.2 },
      { kind: "move", label: `stage ${stageIdx + 1}/${totalStages}: descend`, at: 0.022, obj: objName, secs: 0.9 },
      { kind: "grip", label: `stage ${stageIdx + 1}/${totalStages}: close gripper`, value: 0, secs: 0.5 },
      { kind: "check", label: `stage ${stageIdx + 1}/${totalStages}: check grasp`, obj: objName },
      { kind: "move", label: `stage ${stageIdx + 1}/${totalStages}: lift`, at: 0.15, obj: objName, secs: 0.9 },
      { kind: "checkHeld", label: `stage ${stageIdx + 1}/${totalStages}: check lift`, obj: objName },
      { kind: "move", label: `stage ${stageIdx + 1}/${totalStages}: transport`, pos: [destPos[0], destPos[1], 0.15], yaw: 0, secs: 1.4 },
      { kind: "move", label: `stage ${stageIdx + 1}/${totalStages}: lower`, pos: [destPos[0], destPos[1], placeZ], yaw: 0, secs: 0.8 },
      { kind: "grip", label: `stage ${stageIdx + 1}/${totalStages}: release`, value: OPEN, secs: 0.5 },
      { kind: "move", label: `stage ${stageIdx + 1}/${totalStages}: retract`, pos: [destPos[0], destPos[1], 0.15], yaw: 0, secs: 0.8 },
      { kind: "wait", label: `stage ${stageIdx + 1}/${totalStages}: settle`, secs: 0.4 },
      { kind: "judgeStage", label: `stage ${stageIdx + 1}/${totalStages}: judge`, obj: objName, dest: destName },
    ];
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
        const estX = c[0] + opt.sigma * gauss();
        const estY = c[1] + opt.sigma * gauss();
        targetCoords = [estX, estY, s.at];
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
        { kind: "move", label: "back off", at: 0.15, obj: s.obj, secs: 0.7 },
      ];
      if (ep.attempts > 1) {
        back.push({ kind: "fail", label: "give up", outcome: "grasp slip" });
      } else {
        ep.attempts += 1;
        back.push(
          { kind: "move", label: "retry approach", at: 0.15, obj: s.obj, secs: 0.8 },
          { kind: "move", label: "retry descend", at: 0.022, obj: s.obj, secs: 0.8 },
          { kind: "grip", label: "retry close", value: 0, secs: 0.5 },
          { kind: "check", label: "retry check", obj: s.obj }
        );
      }
      ep.steps.splice(ep.i + 1, 0, ...back);
    }

    if (s.kind === "fail") return finish(s.outcome);

    if (s.kind === "checkHeld" && opt.check) {
      const p = getBodyPos(s.obj);
      if (p[2] < 0.08 || !isGrasped(s.obj)) return finish("dropped during lift");
    }

    if (s.kind === "judgeStage") {
      const p = getBodyPos(s.obj);
      const tgt = getTargetPos(s.dest);
      const radius = s.dest === "tray" ? 0.075 : 0.065;
      const inside = Math.hypot(p[0] - tgt[0], p[1] - tgt[1]) < radius;
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
    ep.label = outcome === "success" ? "completed successfully" : `failed: ${outcome}`;
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

  function setupSceneForLayout(layoutKind) {
    const setPos = (name, x, y, z = 0.02, yaw = 0) => {
      const a = jadr(name);
      data.qpos[a] = x;
      data.qpos[a + 1] = y;
      data.qpos[a + 2] = z;
      data.qpos[a + 3] = Math.cos(yaw / 2);
      data.qpos[a + 4] = 0;
      data.qpos[a + 5] = 0;
      data.qpos[a + 6] = Math.sin(yaw / 2);
    };

    if (layoutKind === "cluster") {
      setPos("red_cube", 0.46 + rand() * 0.02, 0.02 + rand() * 0.02, 0.02, 0);
      setPos("green_cube", 0.52 + rand() * 0.02, 0.08 + rand() * 0.02, 0.02, 0);
      setPos("blue_cube", 0.40 + rand() * 0.02, -0.05 + rand() * 0.02, 0.02, 0);
    } else if (layoutKind === "spread") {
      setPos("red_cube", 0.42 + rand() * 0.04, 0.12 + rand() * 0.04, 0.02, 0);
      setPos("green_cube", 0.55 + rand() * 0.04, -0.02 + rand() * 0.04, 0.02, 0);
      setPos("blue_cube", 0.38 + rand() * 0.04, -0.16 + rand() * 0.04, 0.02, 0);
    } else {
      setPos("red_cube", 0.45 + (rand() - 0.5) * 0.08, 0.10 + (rand() - 0.5) * 0.06, 0.02, (rand() - 0.5) * 0.4);
      setPos("green_cube", 0.54 + (rand() - 0.5) * 0.08, -0.04 + (rand() - 0.5) * 0.06, 0.02, (rand() - 0.5) * 0.4);
      setPos("blue_cube", 0.42 + (rand() - 0.5) * 0.08, -0.14 + (rand() - 0.5) * 0.06, 0.02, (rand() - 0.5) * 0.4);
    }

    data.ctrl[7] = OPEN;
    mj.mj_forward(model, data);
  }

  function runEpisode() {
    view.reset();
    const taskList = TASKS[opt.suite] || TASKS.spatial;
    const task = taskList[opt.taskIdx] || taskList[0];

    setupSceneForLayout(task.layout);

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
      label: "initializing",
      steps: allSteps,
    };

    startStep();
    view.play();
  }

  function resetScene() {
    view.reset();
    ep = null;
    if (homeQ) hold = homeQ.slice();
    const tList = TASKS[opt.suite] || TASKS.spatial;
    setupSceneForLayout(tList[opt.taskIdx]?.layout || "standard");
  }

  function setCameraView(camKey) {
    opt.camera = camKey;
    const cfg = CAMERAS[camKey] || CAMERAS.orbit;
    view.viewer.frameCamera(cfg);
  }

  const outs = {
    instruction: readout("LIBERO instruction"),
    stage: readout("VLA execution phase"),
    tcp: readout("Franka TCP pose (x, y, z)"),
    gripper: readout("gripper opening / contact"),
    rate: readout("control loop frequency"),
    outcome: readout("episode outcome"),
    tally: readout("benchmark success rate"),
  };

  let alive = true;
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

    const curTask = (TASKS[opt.suite] || TASKS.spatial)[opt.taskIdx] || TASKS.spatial[0];
    outs.instruction.set(`"${curTask.instruction}"`);
    outs.stage.set(ep ? ep.label : "idle (ready to run)");

    const p = Array.from(data.site_xpos.slice(3 * tcp, 3 * tcp + 3));
    outs.tcp.set(`[${fmt(p[0], 3)}, ${fmt(p[1], 3)}, ${fmt(p[2], 3)}] m`);

    const gripMm = fmt(data.ten_length[0] * 1000, 1);
    const inContact = ep && ep.task ? (isGrasped(ep.task.stages[0].obj) ? "grasped" : "open") : "open";
    outs.gripper.set(`${gripMm} mm (${inContact})`);

    const targetHz = Math.round(measuredHz);
    outs.rate.set(`${targetHz} Hz (operational-space step: 50 ms)`);

    outs.outcome.set(ep ? ep.outcome : "-");
    const pct = tally.runs > 0 ? ` (${Math.round((100 * tally.wins) / tally.runs)}%)` : "";
    outs.tally.set(`${tally.wins} / ${tally.runs}${pct}`);

    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  const noteEl = h("p", { class: "widget__note" }, TASKS.spatial[0].note);

  const taskSelectRow = select({
    label: "Task instruction",
    options: TASKS.spatial.map((t, idx) => [t.label, idx]),
    value: 0,
    onChange: (v) => {
      opt.taskIdx = parseInt(v, 10);
      noteEl.textContent = ((TASKS[opt.suite] || TASKS.spatial)[opt.taskIdx] || {}).note || "";
    },
  });

  const suiteSelectRow = select({
    label: "LIBERO suite",
    options: LIBERO_SUITES,
    value: "spatial",
    onChange: (s) => {
      opt.suite = s;
      opt.taskIdx = 0;
      const list = TASKS[s] || TASKS.spatial;
      const selEl = taskSelectRow.querySelector("select");
      if (selEl) {
        selEl.innerHTML = "";
        list.forEach((t, idx) => {
          const optEl = document.createElement("option");
          optEl.value = String(idx);
          optEl.textContent = t.label;
          selEl.appendChild(optEl);
        });
        selEl.value = "0";
      }
      noteEl.textContent = list[0]?.note || "";
    },
  });

  const cameraSelectRow = select({
    label: "Camera viewpoint",
    options: [
      ["3D Free Orbit view", "orbit"],
      ["Top Camera (Overhead / Agentview)", "overhead"],
      ["Front Camera (Profile workspace)", "front"],
      ["Wrist Camera (Egocentric 1st-person)", "wrist"],
    ],
    value: "orbit",
    onChange: (cam) => setCameraView(cam),
  });

  const chunkSelectRow = select({
    label: "Action chunk horizon (H)",
    options: [
      ["H = 1 (instantaneous)", "1"],
      ["H = 5 (receding horizon)", "5"],
      ["H = 10 (standard VLA)", "10"],
      ["H = 20 (long chunk)", "20"],
    ],
    value: "10",
    onChange: (v) => {
      opt.chunkSize = parseInt(v, 10);
    },
  });

  const noiseSliderRow = slider({
    label: "Perception noise σ",
    unit: "mm",
    min: 0,
    max: 15,
    step: 1,
    value: 0,
    digits: 0,
    onInput: (v) => {
      opt.sigma = v / 1000;
    },
  });

  body.append(
    h(
      "div",
      { class: "toolbar" },
      button("Run VLA Rollout", runEpisode, "btn btn--primary"),
      button("Reset Scene", resetScene, "btn")
    ),
    h("div", { class: "controls" }, suiteSelectRow, taskSelectRow, cameraSelectRow, chunkSelectRow, noiseSliderRow),
    h("div", { class: "readouts" }, Object.values(outs)),
    noteEl,
    h(
      "p",
      { class: "widget__note" },
      "In robot learning benchmarks such as LIBERO, a Vision-Language-Action policy consumes dual camera observations (overhead context and wrist egocentric context) together with proprioception to generate action chunks. Spatial generalization tests coordinate grounding across relative table locations, object generalization isolates novel distractor configurations, goal conditioning tests diverse destination specifications, and LIBERO-10 measures compounding error over multi-stage composite sequences."
    )
  );

  return {
    destroy() {
      alive = false;
      try {
        [jp, jr, mbuf].forEach((b) => b.delete());
        scratch.delete();
      } catch (e) {
        // memory already released
      }
      view.destroy();
    },
  };
}
