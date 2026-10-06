// The tabletop scene of Levels 22 and 23 in the browser: constants, the planar state, the demonstrator and layouts.
// A port of code/src/mjcourse/tabletop.py; the Python module is the reference, and the labs that use this file
// say which of its numbers were measured in Python.

export const OBJECTS = ["red", "green", "blue"];
export const ZONES = { upper: [0.21, 0], lower: [-0.21, 0], left: [0, 0.21], right: [0, -0.21] };
export const CONTROL_DT = 0.1, MAX_SPEED = 0.2, SUCCESS_RADIUS = 0.05, EPISODE_STEPS = 120;
export const PUCK_RADIUS = 0.03, PUSHER_RADIUS = 0.015;

/** Addresses of the pucks' free joints in qpos and qvel. */
export function addresses(mj, model) {
  const id = (n) => mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT.value, n);
  return OBJECTS.map((o) => ({ q: model.jnt_qposadr[id(`${o}_puck`)], v: model.jnt_dofadr[id(`${o}_puck`)] }));
}

/** The 16-number planar state: pusher x, y, vx, vy, then x, y, vx, vy of each puck. */
export function planarState(data, adr) {
  const s = new Float64Array(16);
  s[0] = data.qpos[0]; s[1] = data.qpos[1]; s[2] = data.qvel[0]; s[3] = data.qvel[1];
  adr.forEach((a, k) => {
    s[4 + 4 * k] = data.qpos[a.q]; s[5 + 4 * k] = data.qpos[a.q + 1];
    s[6 + 4 * k] = data.qvel[a.v]; s[7 + 4 * k] = data.qvel[a.v + 1];
  });
  return s;
}

const smoothstep = (x) => { const t = Math.min(Math.max(x, 0), 1); return t * t * (3 - 2 * t); };
const clip = (v) => Math.min(Math.max(v, -1), 1);

function toward(u, target, gain) {
  const dx = target[0] - u[0], dy = target[1] - u[1], d = Math.hypot(dx, dy) + 1e-9;
  const speed = Math.min(1, gain * d);
  return [speed * dx / d, speed * dy / d];
}

/** The demonstrator of Level 22 (tabletop.expert): one continuous velocity field, from the true state. */
export function expert(s, task, pushSpeed = 0.6, lateralGain = 30, sideWidth = 0.006) {
  const i = 4 + 4 * OBJECTS.indexOf(task[0]), g = ZONES[task[1]];
  const u = [s[0], s[1]], p = [s[i], s[i + 1]];
  const gx = g[0] - p[0], gy = g[1] - p[1], dist = Math.hypot(gx, gy);
  const d = [gx / (dist + 1e-9), gy / (dist + 1e-9)], n = [-d[1], d[0]];
  const r = PUCK_RADIUS + PUSHER_RADIUS;
  const rel = [u[0] - p[0], u[1] - p[1]];
  const along = rel[0] * d[0] + rel[1] * d[1], lateral = rel[0] * n[0] + rel[1] * n[1], gap = Math.hypot(rel[0], rel[1]);
  const finish = Math.min(1, dist / 0.03);
  const push = [0, 1].map((k) => pushSpeed * finish * d[k] - lateralGain * lateral * n[k] + 10 * (-(r - 0.003) - along) * d[k]);
  const behind = [p[0] - d[0] * (r + 0.02), p[1] - d[1] * (r + 0.02)];
  const approach = toward(u, behind, 15);
  const front = smoothstep((along + 0.6 * r) / (0.6 * r));
  const near = gap > r ? Math.exp(-(((gap - r) / 0.03) ** 2)) : 1;
  const side = Math.tanh(lateral / sideWidth) * front * near;
  const clear = Math.max(0, (r + 0.015 - gap) / 0.015) * front / (gap + 1e-9);
  const w = smoothstep((-along - 0.45 * r) / (0.35 * r)) * Math.exp(-((lateral / (0.45 * r)) ** 2));
  return [0, 1].map((k) => clip(w * push[k] + (1 - w) * (approach[k] + side * n[k] + clear * rel[k])));
}

/** A small seeded generator (mulberry32) with uniform and normal draws. */
export function rng(seed) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return { uniform: (lo, hi) => lo + (hi - lo) * next(), normal: () => Math.sqrt(-2 * Math.log(next() + 1e-12)) * Math.cos(2 * Math.PI * next()), next };
}

/** A layout like tabletop.sample_layout: pucks 0.1 m apart, away from the zones, the target 0.12 m from its zone. */
export function sampleLayout(r, task) {
  const centres = Object.values(ZONES);
  for (;;) {
    const pucks = [0, 1, 2].map(() => [r.uniform(-0.2, 0.2), r.uniform(-0.2, 0.2)]);
    const far = (a, b, m) => Math.hypot(a[0] - b[0], a[1] - b[1]) >= m;
    if (!(far(pucks[0], pucks[1], 0.1) && far(pucks[0], pucks[2], 0.1) && far(pucks[1], pucks[2], 0.1))) continue;
    if (pucks.some((p) => centres.some((c) => !far(p, c, SUCCESS_RADIUS + 0.02)))) continue;
    if (task && !far(pucks[OBJECTS.indexOf(task[0])], ZONES[task[1]], 0.12)) continue;
    const pusher = [r.uniform(-0.25, 0.25), r.uniform(-0.25, 0.25)];
    if (pucks.some((p) => !far(p, pusher, 0.08))) continue;
    return { pusher, pucks };
  }
}

/** Put a layout into MuJoCo's data and recompute (pucks flat, at rest). */
export function applyLayout(mj, model, data, adr, layout) {
  mj.mj_resetData(model, data);
  data.qpos[0] = layout.pusher[0]; data.qpos[1] = layout.pusher[1];
  adr.forEach((a, k) => {
    data.qpos[a.q] = layout.pucks[k][0]; data.qpos[a.q + 1] = layout.pucks[k][1]; data.qpos[a.q + 2] = 0.01;
    data.qpos[a.q + 3] = 1; data.qpos[a.q + 4] = 0; data.qpos[a.q + 5] = 0; data.qpos[a.q + 6] = 0;
  });
  mj.mj_forward(model, data);
}

export function success(s, task) {
  const i = 4 + 4 * OBJECTS.indexOf(task[0]), g = ZONES[task[1]];
  return Math.hypot(s[i] - g[0], s[i + 1] - g[1]) < SUCCESS_RADIUS;
}
