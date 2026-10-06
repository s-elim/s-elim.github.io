// wmrollout: a learned world model predicting, open loop, beside MuJoCo (Lesson 23.2). The scene runs in MuJoCo
// under the chosen action source; from the moment you press "Predict from here" the learned model of Lesson 23.2
// (data/l23_2_dynamics.json, run in JavaScript) receives the same actions and predicts the state step by step from
// its own previous prediction. Solid lines are MuJoCo's paths, dashed lines the model's; the plot is the gap.
//
// Config: {"title": "...", "height": 320}

import * as THREE from "three";
import { h, frame, slider, select, button, readout, createSimView, fmt } from "./ui.js";
import { Plot } from "../plot.js";
import { loadDynamics } from "../learned.js";
import * as T from "../tabletop.js";

const Z = 0.021;                                                   // overlay height, just above the pucks' tops
const COLOURS = { pusher: 0x0072b2, puck: 0xd55e00 };

function lineFor(colour, dashed) {
  const geo = new THREE.BufferGeometry();
  const mat = dashed ? new THREE.LineDashedMaterial({ color: colour, dashSize: 0.008, gapSize: 0.006 })
    : new THREE.LineBasicMaterial({ color: colour });
  const line = new THREE.Line(geo, mat);
  line.frustumCulled = false;
  return line;
}

function setPath(line, points) {
  line.geometry.setAttribute("position", new THREE.Float32BufferAttribute(points.flatMap((p) => [p[0], p[1], Z]), 3));
  if (line.material.isLineDashedMaterial) line.computeLineDistances();
}

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "A learned world model beside MuJoCo", kind: "Lab" });
  const [view, dyn] = await Promise.all([
    createSimView(body, { model: "tabletop", height: config.height || 320, toolbar: false,
      camera: { azimuth: 180, elevation: 89, distance: 0.95, target: [0, 0, 0] } }),
    loadDynamics()]);
  const { sim, mj } = view, { model, data } = sim;
  const adr = T.addresses(mj, model);
  const opt = { task: ["red", "left"], source: "noisy", horizon: 30, auto: true };
  let r = T.rng(1), action = [0, 0], nextAction = 0, pred = null;

  const lines = { truePusher: lineFor(COLOURS.pusher, false), predPusher: lineFor(COLOURS.pusher, true),
    truePuck: lineFor(COLOURS.puck, false), predPuck: lineFor(COLOURS.puck, true) };
  view.viewer.overlayGroup.add(...Object.values(lines));

  const plotEl = h("div");
  const plot = new Plot(plotEl, { mode: "xy", xlabel: "steps predicted (0.1 s each)", ylabel: "error (mm)", height: 150, xmin: 0, ymin: 0,
    traces: [{ label: "pusher (mm)" }, { label: "pushed puck (mm)" }] });
  const outs = { step: readout("steps predicted"), pusher: readout("pusher error"), puck: readout("pushed puck error"),
    contact: readout("pusher touching the puck (MuJoCo / model)") };

  const target = () => 4 + 4 * T.OBJECTS.indexOf(opt.task[0]);
  function chooseAction(s) {
    if (opt.source === "random") return [r.uniform(-1, 1), r.uniform(-1, 1)];
    const a = T.expert(s, opt.task);
    if (opt.source === "demonstrator") return a;
    return a.map((v) => Math.min(Math.max(v + 0.3 * r.normal(), -1), 1));
  }
  function touching(s) {
    const i = target();
    return Math.hypot(s[0] - s[i], s[1] - s[i + 1]) < T.PUCK_RADIUS + T.PUSHER_RADIUS + 0.003;
  }

  let pendingStart = true;
  function startPrediction() { pendingStart = true; }               // takes effect at the next control step

  function report(s, p) {
    const i = target();
    pred.ep.push(1000 * Math.hypot(p[0] - s[0], p[1] - s[1]));
    pred.eq.push(1000 * Math.hypot(p[i] - s[i], p[i + 1] - s[i + 1]));
    const xs = pred.ep.map((_, k) => k + 1);
    plot.setSeries(0, xs, pred.ep); plot.setSeries(1, xs, pred.eq); plot.draw();
    outs.step.set(String(pred.ep.length));
    outs.pusher.set(`${fmt(pred.ep[pred.ep.length - 1], 1)} mm`);
    outs.puck.set(`${fmt(pred.eq[pred.eq.length - 1], 1)} mm`);
    outs.contact.set(`${touching(s) ? "yes" : "no"} / ${touching(p) ? "yes" : "no"}`);
  }

  function onControlStep() {                                         // every 0.1 s of simulated time
    const s = T.planarState(data, adr);
    if (pred && !pred.frozen && pred.states.length > pred.truth.length) {   // compare the prediction made one step ago
      pred.truth.push(s);
      report(s, pred.states[pred.truth.length - 1]);
      if (pred.ep.length >= opt.horizon) {
        if (opt.auto) pendingStart = true; else { pred.frozen = true; view.pause(); }
      }
    }
    if (pendingStart) {
      pred = { states: [s], truth: [s], ep: [], eq: [], frozen: false };
      plot.setSeries(0, [], []); plot.setSeries(1, [], []); plot.draw();
      pendingStart = false;
    }
    action = chooseAction(s);
    if (!pred.frozen) pred.states.push(dyn.step(pred.states[pred.states.length - 1], action));
    const i = target(), shown = pred.states.slice(0, pred.truth.length);   // the model's path up to now, not ahead
    setPath(lines.truePusher, pred.truth.map((q) => [q[0], q[1]]));
    setPath(lines.predPusher, shown.map((q) => [q[0], q[1]]));
    setPath(lines.truePuck, pred.truth.map((q) => [q[i], q[i + 1]]));
    setPath(lines.predPuck, shown.map((q) => [q[i], q[i + 1]]));
  }

  sim.controller = (s) => {
    if (s.data.time >= nextAction - 1e-9) { onControlStep(); nextAction = s.data.time + T.CONTROL_DT; }
    s.data.ctrl[0] = action[0] * T.MAX_SPEED; s.data.ctrl[1] = action[1] * T.MAX_SPEED;
  };

  function newLayout() {
    r = T.rng(Math.floor(Math.random() * 1e9));
    T.applyLayout(mj, model, data, adr, T.sampleLayout(r, opt.task));
    nextAction = data.time; pred = null; pendingStart = true;
    Object.values(lines).forEach((l) => setPath(l, []));
    plot.setSeries(0, [], []); plot.setSeries(1, [], []); plot.draw();
    view.play();
  }

  const taskOptions = T.OBJECTS.flatMap((o) => Object.keys(T.ZONES).map((z) => [`${o},${z}`, `${o} puck to the ${z} zone`]));
  body.append(
    h("div", { class: "toolbar" }, button("New layout", newLayout, "btn btn--primary"), button("Predict from here", startPrediction),
      button("Pause / play", () => view.toggle())),
    h("div", { class: "controls" },
      select({ label: "task", options: taskOptions, value: "red,left", onChange: (v) => { opt.task = v.split(","); newLayout(); } }),
      select({ label: "actions", options: [["demonstrator", "the demonstrator"], ["noisy", "the demonstrator plus noise (training data's policy)"], ["random", "uniformly random"]],
        value: opt.source, onChange: (v) => { opt.source = v; } }),
      slider({ label: "prediction horizon", min: 5, max: 60, step: 5, value: opt.horizon, unit: "steps", digits: 0, onInput: (v) => { opt.horizon = v; } }),
      select({ label: "when the horizon is reached", options: [["restart", "predict again from there"], ["stop", "pause and keep the paths"]],
        value: "restart", onChange: (v) => { opt.auto = v === "restart"; } })),
    h("div", { class: "readouts" }, Object.values(outs)), plotEl,
    h("p", { class: "widget__note", html: "Solid: MuJoCo. Dashed: the learned model, fed its own predictions. Blue: the pusher; orange: the puck named in the task. The model and the demonstrator run in JavaScript and agree with the Python versions to 2e-7 over ten steps. Measured in Python on 100 held-out episodes: 1.0 mm of puck error after one step, 8.1 mm after 10, 76.7 mm after 50." }));
  newLayout();

  return { destroy() { view.viewer.overlayGroup.remove(...Object.values(lines)); Object.values(lines).forEach((l) => { l.geometry.dispose(); l.material.dispose(); }); plot.dispose(); view.destroy(); } };
}
