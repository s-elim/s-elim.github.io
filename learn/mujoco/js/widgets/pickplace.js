// pickplace: the scripted pick-and-place of Lesson 10.2, running in the page.
// Waypoints are 6-D tcp poses (tool down, yaw matched to the cube); each is turned
// into joint angles by damped-least-squares IK, the joints follow minimum-jerk paths
// tracked by PD with gravity compensation, and the grasp is checked from contacts.
// The cube's position is "perceived" with Gaussian error of the chosen size.
//
// Config: {"title": "...", "height": 300}

import { h, frame, slider, select, button, readout, createSimView } from "./ui.js";
import { idOf } from "../runtime.js";
import { solve, transpose, matVec, norm, quatFromMat, quatMul, quatConj, quatToRotvec } from "../linalg.js";

const AREA = [[0.40, 0.60], [-0.20, 0.00]], WN = 20, OPEN = 0.04;

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "A scripted pick-and-place", kind: "Lab" });
  const view = await createSimView(body, {
    model: "pick_place", key: 1, height: config.height || 300, onReset: () => { ep = null; hold = homeQ.slice(); },
    camera: config.camera || { azimuth: -140, elevation: 30, distance: 1.5, target: [0.5, 0.0, 0.1] },
  });
  const sim = view.sim;
  const { mj, model, data } = sim;
  const nv = model.nv;
  const tcp = idOf(mj, model, "mjOBJ_SITE", "gripper/tcp");
  const cubeBody = idOf(mj, model, "mjOBJ_BODY", "red_cube"), cubeGeom = idOf(mj, model, "mjOBJ_GEOM", "red_cube");
  const pads = ["gripper/pad_left", "gripper/pad_right"].map((n) => idOf(mj, model, "mjOBJ_GEOM", n));
  const jadr = (name) => model.jnt_qposadr[idOf(mj, model, "mjOBJ_JOINT", name)];
  const lo = [], hi = [];
  for (let j = 0; j < 7; j++) { lo.push(model.jnt_range[2 * j]); hi.push(model.jnt_range[2 * j + 1]); }
  const scratch = new mj.MjData(model);
  const jp = new mj.DoubleBuffer(3 * nv), jr = new mj.DoubleBuffer(3 * nv), mbuf = new mj.DoubleBuffer(nv * nv);
  mj.mj_forward(model, data);
  const homeQ = Array.from(data.qpos.slice(0, 7));
  const down = quatFromMat(Array.from(data.site_xmat.slice(9 * tcp, 9 * tcp + 9)));
  mj.mj_fullM(model, data, mbuf);
  const mdiag = Array.from({ length: 7 }, (_, j) => mbuf.GetView()[j * nv + j]);
  const kp = mdiag.map((m) => m * WN * WN), kd = mdiag.map((m) => 2 * m * WN);
  let seed = 1;
  const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  const gauss = () => Math.sqrt(-2 * Math.log(rand() + 1e-12)) * Math.cos(2 * Math.PI * rand());
  const opt = { sigma: 0.0, check: true, retries: 1 };
  const tally = { runs: 0, wins: 0 };
  let ep = null, hold = homeQ.slice();       // joint targets the PD loop tracks, also between episodes

  /** Damped-least-squares IK for the tcp, arm joints only, on the scratch data. */
  function ik(qStart, pos, quat) {
    const attempt = (q0) => {
      const q = q0.slice();
      for (let it = 0; it < 200; it++) {
        for (let j = 0; j < 7; j++) scratch.qpos[j] = q[j];
        mj.mj_kinematics(model, scratch); mj.mj_comPos(model, scratch);
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
  const cubePos = () => Array.from(data.xpos.slice(3 * cubeBody, 3 * cubeBody + 3));
  function grasped() {
    const touching = new Set();
    for (const c of sim.contacts()) for (const p of pads) if ((c.geom1 === p && c.geom2 === cubeGeom) || (c.geom2 === p && c.geom1 === cubeGeom)) touching.add(p);
    return touching.size === 2 && data.ten_length[0] > 0.01 && data.ten_length[0] < 0.035;
  }

  // The episode is a list of steps: joint-space moves to tcp poses, timed gripper
  // commands and waits, and the checks. A failed grasp check splices a retry in.
  const estimate = () => { const c = cubePos(); return [c[0] + opt.sigma * gauss(), c[1] + opt.sigma * gauss()]; };
  const graspSteps = () => [
    { kind: "move", label: "approach", at: 0.15, perceive: true, secs: 1.5 },
    { kind: "move", label: "descend", at: 0.022, secs: 1.0 },
    { kind: "grip", label: "close", value: 0, secs: 0.6 },
    { kind: "check", label: "check grasp" },
  ];
  function plan(tray) {
    const t = (z) => [tray[0], tray[1], z];
    return [
      ...graspSteps(),
      { kind: "move", label: "lift", at: 0.15, secs: 1.0 },
      { kind: "checkHeld", label: "check lift" },
      { kind: "move", label: "carry", pos: t(0.15), yaw: 0, secs: 1.5 },
      { kind: "checkCarried", label: "check carry" },
      { kind: "move", label: "lower", pos: t(0.07), yaw: 0, secs: 0.8 },
      { kind: "grip", label: "release", value: OPEN, secs: 0.5 },
      { kind: "move", label: "retreat", pos: t(0.15), yaw: 0, secs: 0.8 },
      { kind: "wait", label: "settle", secs: 0.5 },
      { kind: "judge", label: "judge" },
    ];
  }

  function startStep() {
    const s = ep.steps[ep.i];
    ep.label = s.label;
    if (s.kind === "move") {
      if (s.perceive) ep.estimate = estimate();
      const pos = s.pos || [ep.estimate[0], ep.estimate[1], s.at];
      const goal = ik(Array.from(data.qpos.slice(0, 7)), pos, yawQuat(s.yaw ?? ep.yaw));
      if (!goal) return finish("IK failed");
      ep.from = hold.slice(); ep.to = goal; ep.t0 = data.time; ep.dur = s.secs; ep.until = data.time + s.secs + 0.2;
    } else {
      ep.to = null;
      if (s.kind === "grip") data.ctrl[7] = s.value;
      ep.until = data.time + (s.secs || 0);
    }
  }
  function endStep() {
    const s = ep.steps[ep.i];
    if (s.kind === "check" && opt.check && !grasped()) {
      // let go, back off above the estimate, then look again (or give up)
      data.ctrl[7] = OPEN;
      const back = [{ kind: "wait", label: "let go", secs: 0.4 }, { kind: "move", label: "back off", at: 0.15, secs: 0.8 }];
      if (ep.attempts > opt.retries) back.push({ kind: "fail", label: "give up", outcome: "grasp missed" });
      else back.push({ kind: "retry", label: "retry" }, ...graspSteps());
      ep.steps.splice(ep.i + 1, 0, ...back);
    }
    if (s.kind === "retry") ep.attempts += 1;
    if (s.kind === "fail") return finish(s.outcome);
    if (s.kind === "checkHeld" && opt.check && (cubePos()[2] < 0.08 || !grasped())) return finish("dropped while lifting");
    if (s.kind === "checkCarried" && opt.check && cubePos()[2] < 0.08) return finish("dropped while carrying");
    if (s.kind === "judge") {
      const p = cubePos();
      const inside = Math.abs(p[0] - ep.tray[0]) < 0.07 && Math.abs(p[1] - ep.tray[1]) < 0.07 && p[2] < 0.06;
      if (inside) return finish("success");
      return finish(Math.hypot(p[0] - ep.start[0], p[1] - ep.start[1]) < 0.05 ? "never picked up (found only at the end)" : "missed the tray");
    }
    ep.i += 1;
    startStep();
  }
  function finish(outcome) {
    ep.outcome = outcome; ep.done = true; ep.label = "done";
    tally.runs += 1; if (outcome === "success") tally.wins += 1;
  }

  // PD with gravity compensation on the arm joints, always on, so the arm holds its pose
  // between episodes; the step machine only moves the target.
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

  function runEpisode() {
    view.reset();                                           // clears ep and hold via onReset
    const x = AREA[0][0] + rand() * 0.2, y = AREA[1][0] + rand() * 0.2, yaw = (rand() - 0.5) * Math.PI / 2;
    const set = (name, vals) => { const a = jadr(name); vals.forEach((v, i) => { data.qpos[a + i] = v; }); };
    set("green_cube", [-0.6, 0.6, 0.02]); set("blue_cube", [-0.6, -0.6, 0.02]);
    set("red_cube", [x, y, 0.02, Math.cos(yaw / 2), 0, 0, Math.sin(yaw / 2)]);
    data.ctrl[7] = OPEN;
    mj.mj_forward(model, data);
    const traySite = idOf(mj, model, "mjOBJ_SITE", "tray_center");
    const tray = Array.from(data.site_xpos.slice(3 * traySite, 3 * traySite + 3));
    const gy = ((yaw + Math.PI / 4) % (Math.PI / 2) + Math.PI / 2) % (Math.PI / 2) - Math.PI / 4;   // a cube repeats every 90 degrees
    ep = { start: [x, y], yaw: gy, tray, attempts: 1, i: 0, done: false, outcome: "running", label: "", steps: plan(tray) };
    startStep();
    view.play();
  }

  const outs = { state: readout("state"), attempts: readout("grasp attempts"), outcome: readout("outcome"), tally: readout("successes / episodes") };
  let alive = true;
  const tick = () => {
    if (!alive) return;
    outs.state.set(ep ? ep.label : "-");
    outs.attempts.set(ep ? String(ep.attempts) : "-");
    outs.outcome.set(ep ? ep.outcome : "-");
    outs.tally.set(`${tally.wins} / ${tally.runs}`);
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  body.append(h("div", { class: "toolbar" }, button("Run an episode", runEpisode, "btn btn--primary")),
    h("div", { class: "controls" },
      slider({ label: "perception error σ", unit: "mm", min: 0, max: 20, step: 1, value: 0, digits: 0, onInput: (v) => { opt.sigma = v / 1000; } }),
      select({ label: "grasp check from contacts", options: [["on, one retry", "on"], ["off (blind)", "off"]], value: "on", onChange: (v) => { opt.check = v === "on"; } })),
    h("div", { class: "readouts" }, Object.values(outs)),
    h("p", { class: "widget__note", html: "Each episode places the red cube at a new random pose in a 20 × 20 cm area. Use the 4x speed button to run several episodes quickly. With the check off, the arm carries on regardless and the outcome is only known at the end." }));

  return { destroy() { alive = false; [jp, jr, mbuf].forEach((b) => b.delete()); scratch.delete(); view.destroy(); } };
}
