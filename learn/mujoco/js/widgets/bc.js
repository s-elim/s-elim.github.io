// bc: behaviour cloning and DAgger on the point-mass task of Level 14, drawn from above.
// The physics is MuJoCo (point_mass.xml) running in the page; the expert is the scripted
// one of mjcourse.il.pointmass; the learner is a k-nearest-neighbour regressor on the
// recorded (state, action) pairs, so "training" is instantaneous. The lesson's script uses
// an MLP instead: the two policy classes fail in different details, the same way.
//
// Config: {"title": "...", "height": 340}

import { h, frame, select, button, readout } from "./ui.js";
import { Plot } from "../plot.js";
import { getMujoco, loadModel, idOf } from "../runtime.js";

const GOAL = [0.35, 0], MAX_STEPS = 600, PUSH = 0.4;

function mulberry32(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const clamp = (v) => Math.max(-1, Math.min(1, v));
const nextFrame = () => new Promise((r) => requestAnimationFrame(() => r()));

function expert(s) {
  const side = s[1] >= 0 ? 1 : -1;
  const target = s[0] < -0.02 ? [0, 0.2 * side] : GOAL;
  return [clamp(4 * (target[0] - s[0]) - 1.5 * s[2]), clamp(4 * (target[1] - s[1]) - 1.5 * s[3])];
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Cloning an expert, and DAgger", kind: "Lab" });
  const mj = await getMujoco();
  const model = await loadModel("point_mass");
  const data = new mj.MjData(model);
  const obstacle = idOf(mj, model, "mjOBJ_GEOM", "obstacle");
  const opt = { k: 1, pushRate: 1.0, demoPush: false };
  const states = [], actions = [];                   // the dataset
  let scale = [0.2, 0.2, 0.3, 0.3];                  // state units for neighbour distances
  let rand = mulberry32(5);
  const heldOut = (() => { const r = mulberry32(999); return Array.from({ length: 20 }, () => [-0.4 + 0.1 * r(), -0.25 + 0.5 * r()]); })();
  const sampleStart = () => [-0.4 + 0.1 * rand(), -0.25 + 0.5 * rand()];

  function knn(s) {
    if (!states.length) return [0, 0];
    const best = [];                                  // k smallest distances: [d, index]
    for (let i = 0; i < states.length; i++) {
      const p = states[i];
      let d = 0;
      for (let j = 0; j < 4; j++) { const e = (p[j] - s[j]) / scale[j]; d += e * e; }
      if (best.length < opt.k) { best.push([d, i]); best.sort((a, b) => a[0] - b[0]); }
      else if (d < best[opt.k - 1][0]) { best[opt.k - 1] = [d, i]; best.sort((a, b) => a[0] - b[0]); }
    }
    const a = [0, 0];
    for (const [, i] of best) { a[0] += actions[i][0] / best.length; a[1] += actions[i][1] / best.length; }
    return a;
  }

  /** One episode; pushes come from `pr` at `rate` per second. Returns path, states, success, hit. */
  function rollout(policy, start, rate, pr) {
    mj.mj_resetData(model, data);
    data.qpos[0] = start[0]; data.qpos[1] = start[1];
    mj.mj_forward(model, data);
    const path = [], visited = [];
    let hit = false;
    const pPush = rate * model.opt.timestep;
    for (let t = 0; t < MAX_STEPS; t++) {
      if (pPush > 0 && pr() < pPush) { const a = 2 * Math.PI * pr(); data.qvel[0] += PUSH * Math.cos(a); data.qvel[1] += PUSH * Math.sin(a); }
      const s = [data.qpos[0], data.qpos[1], data.qvel[0], data.qvel[1]];
      const u = policy(s);
      visited.push(s); path.push([s[0], s[1]]);
      data.ctrl[0] = clamp(u[0]); data.ctrl[1] = clamp(u[1]);
      mj.mj_step(model, data);
      if (data.ncon > 0) {
        const vec = data.contact;                     // a wrapper per access: delete it, and each element
        for (let c = 0; c < data.ncon; c++) {
          const con = vec.get(c);
          if (con.geom1 === obstacle || con.geom2 === obstacle) hit = true;
          con.delete();
        }
        vec.delete();
      }
      if (Math.hypot(data.qpos[0] - GOAL[0], data.qpos[1] - GOAL[1]) < 0.04 && Math.hypot(data.qvel[0], data.qvel[1]) < 0.05) {
        path.push([data.qpos[0], data.qpos[1]]);
        return { path, visited, success: true, hit };
      }
    }
    return { path, visited, success: false, hit };
  }

  // ---------------------------------------------------------------- drawing
  const canvas = h("canvas", { width: 520, height: 520, style: { width: "100%", maxWidth: `${config.height || 340}px`, display: "block", margin: "8px auto", background: "#f4f5f2", borderRadius: "6px" } });
  const ctx = canvas.getContext("2d");
  const X = (x) => (x + 0.5) * 520, Y = (y) => (0.5 - y) * 520;
  let layers = { demos: [], dagger: [], tests: [] };
  function draw() {
    ctx.clearRect(0, 0, 520, 520);
    ctx.strokeStyle = "#777"; ctx.lineWidth = 6; ctx.strokeRect(3, 3, 514, 514);
    ctx.fillStyle = "#9c8a73"; ctx.beginPath(); ctx.arc(X(0), Y(0), 0.1 * 520, 0, 2 * Math.PI); ctx.fill();
    ctx.fillStyle = "rgba(0,158,115,0.35)"; ctx.beginPath(); ctx.arc(X(GOAL[0]), Y(GOAL[1]), 0.04 * 520, 0, 2 * Math.PI); ctx.fill();
    const line = (path, colour, width) => {
      ctx.strokeStyle = colour; ctx.lineWidth = width; ctx.beginPath();
      path.forEach(([x, y], i) => (i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y)))); ctx.stroke();
    };
    layers.demos.forEach((p) => line(p, "rgba(120,120,120,0.45)", 1.5));
    layers.dagger.forEach((p) => line(p, "rgba(0,114,178,0.55)", 1.5));
    layers.tests.forEach(({ path, success }) => line(path, success ? "rgba(0,158,115,0.9)" : "rgba(213,94,0,0.9)", 2));
  }

  const plotEl = h("div");
  const plot = new Plot(plotEl, { mode: "xy", xlabel: "expert labels in the dataset", ylabel: "test successes / 20", height: 140, ymin: 0, ymax: 20,
    traces: [{ label: "test with the chosen pushes" }] });
  const pts = { x: [], y: [] };
  const outs = { labels: readout("expert labels"), test: readout("last test: successes / 20"), hit: readout("last test: touched the obstacle"), status: readout("status") };
  const updateOuts = () => { outs.labels.set(String(states.length)); };

  let busy = false;
  async function run(task) {
    if (busy) return;
    busy = true;
    try { await task(); } finally { busy = false; outs.status.set("ready"); updateOuts(); draw(); }
  }
  const addData = (vis, labels) => { for (let i = 0; i < vis.length; i++) { states.push(vis[i]); actions.push(labels[i]); } };
  function refreshScale() {
    if (states.length < 10) return;
    scale = [0, 1, 2, 3].map((j) => {
      const m = states.reduce((s, p) => s + p[j], 0) / states.length;
      return Math.sqrt(states.reduce((s, p) => s + (p[j] - m) ** 2, 0) / states.length) + 1e-6;
    });
  }

  const record = () => run(async () => {
    for (let i = 0; i < 5; i++) {
      outs.status.set(`recording demonstration ${i + 1} / 5`);
      const r = rollout(expert, sampleStart(), opt.demoPush ? opt.pushRate : 0, rand);
      addData(r.visited, r.visited.map(expert));
      layers.demos.push(r.path);
      refreshScale(); updateOuts(); draw(); await nextFrame();
    }
  });
  const test = () => run(async () => {
    if (!states.length) { outs.status.set("record demonstrations first"); return; }
    layers.tests = [];
    let wins = 0, hits = 0;
    for (let i = 0; i < heldOut.length; i++) {
      outs.status.set(`test episode ${i + 1} / 20`);
      const r = rollout(knn, heldOut[i], opt.pushRate, mulberry32(10_000 + i));
      wins += r.success; hits += r.hit;
      layers.tests.push(r);
      draw(); await nextFrame();
    }
    outs.test.set(`${wins} / 20`); outs.hit.set(`${hits} / 20`);
    pts.x.push(states.length); pts.y.push(wins);
    plot.setSeries(0, pts.x, pts.y); plot.draw();
  });
  const daggerStep = () => run(async () => {
    if (!states.length) { outs.status.set("record demonstrations first"); return; }
    const pending = [];
    for (let i = 0; i < 4; i++) {
      outs.status.set(`DAgger rollout ${i + 1} / 4`);
      const r = rollout(knn, sampleStart(), opt.pushRate, rand);       // the learner drives
      pending.push(r);                                                 // labels are added after all four
      layers.dagger.push(r.path);
      draw(); await nextFrame();
    }
    for (const r of pending) addData(r.visited, r.visited.map(expert)); // the expert labels what the learner saw
  });
  const clear = () => { if (busy) return; states.length = 0; actions.length = 0; layers = { demos: [], dagger: [], tests: [] }; pts.x = []; pts.y = []; plot.setSeries(0, [], []); plot.draw(); rand = mulberry32(5); outs.test.set("-"); outs.hit.set("-"); updateOuts(); draw(); };

  body.append(
    h("div", { class: "toolbar" }, button("Record 5 demonstrations", record, "btn btn--primary"), button("Test on 20 starts", test), button("DAgger: 4 rollouts", daggerStep), button("Clear", clear)),
    h("div", { class: "controls" },
      select({ label: "pushes per second (tests and DAgger)", options: [["0", "0"], ["1", "1"], ["2", "2"]], value: "1", onChange: (v) => { opt.pushRate = Number(v); } }),
      select({ label: "pushes while demonstrating", options: [["no", "no"], ["yes", "yes"]], value: "no", onChange: (v) => { opt.demoPush = v === "yes"; } }),
      select({ label: "neighbours averaged (k)", options: [["1", "1"], ["5", "5"]], value: "1", onChange: (v) => { opt.k = Number(v); } })),
    canvas, h("div", { class: "readouts" }, Object.values(outs)), plotEl,
    h("p", { class: "widget__note", html: "Grey: demonstrations. Blue: DAgger rollouts (the learner drives, the expert labels every state it visits). Green and orange: test episodes that succeeded and failed. The 20 test starts and their pushes are the same every time, so tests are comparable." }));
  updateOuts(); outs.status.set("ready"); draw();

  return { destroy() { data.delete(); plot.dispose(); } };
}
