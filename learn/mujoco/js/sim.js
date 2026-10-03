// Sim: one MjModel + MjData pair and the real-time stepping loop around them.
//
// The loop is the same one every MuJoCo application runs:
//
//     each display frame:
//         target = sim time + wall-clock dt * speed
//         while data.time < target:
//             controller writes data.ctrl     (the "policy" or "controller")
//             mj_step(model, data)            (physics advances one timestep)
//             recorders sample data           (plots, logs)
//
// Nothing here is specific to the browser except requestAnimationFrame, which
// the caller drives through `advance(wallDt)`.

import { getMujoco, outBuffer } from "./runtime.js";

const MAX_STEPS_PER_FRAME = 4000;

export class Sim {
  /** @param mj MuJoCo module, @param model compiled MjModel (ownership moves to Sim). */
  constructor(mj, model) {
    this.mj = mj;
    this.model = model;
    this.data = new mj.MjData(model);
    this.paused = true;
    this.speed = 1;
    this.controller = null;      // (sim) => void, called before every mj_step
    this.recorders = new Set();  // (sim) => void, called after every mj_step
    this.listeners = new Set();  // (sim, event) => void, UI notifications
    this.lag = false;            // true when the last frame could not keep real time
    this.keyframe = -1;
    this._warnSeen = new Array(8).fill(0);
    this._buffers = [];
    this.disposed = false;
    mj.mj_forward(model, this.data);
  }

  static async fromModel(model) {
    return new Sim(await getMujoco(), model);
  }

  get time() { return this.data.time; }
  get timestep() { return this.model.opt.timestep; }

  /** Reset to qpos0 (or to keyframe `key` when key >= 0) and recompute derived quantities. */
  reset(key = this.keyframe) {
    const { mj, model, data } = this;
    if (key >= 0 && key < model.nkey) mj.mj_resetDataKeyframe(model, data, key);
    else mj.mj_resetData(model, data);
    mj.mj_forward(model, data);
    this._warnSeen.fill(0);
    this.emit("reset");
  }

  /** Advance exactly n timesteps. */
  step(n = 1) {
    const { mj, model, data } = this;
    for (let i = 0; i < n; i++) {
      if (this.controller) this.controller(this);
      mj.mj_step(model, data);
      for (const r of this.recorders) r(this);
    }
    this.checkWarnings();
  }

  /** Recompute positions, velocities, contacts and forces without advancing time. */
  forward() {
    this.mj.mj_forward(this.model, this.data);
  }

  /** Step enough to cover `wallDt` seconds of wall time at the current speed. */
  advance(wallDt) {
    if (this.paused || this.disposed) return 0;
    const dt = this.model.opt.timestep;
    const simDt = Math.min(wallDt, 0.1) * this.speed; // ignore long stalls (tab switch)
    const wanted = Math.round(simDt / dt + (this._carry || 0));
    const n = Math.min(Math.max(wanted, 0), MAX_STEPS_PER_FRAME);
    this._carry = simDt / dt + (this._carry || 0) - wanted;
    this.lag = wanted > MAX_STEPS_PER_FRAME;
    if (n > 0) this.step(n);
    return n;
  }

  play() { this.paused = false; this.emit("play"); }
  pause() { this.paused = true; this.emit("pause"); }
  toggle() { this.paused ? this.play() : this.pause(); }

  on(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  emit(event, detail) { for (const fn of this.listeners) fn(this, event, detail); }

  /**
   * MuJoCo counts warnings in data.warning[i].number (it does not throw). The
   * bad-acceleration warning also means MuJoCo has already reset the state.
   *
   * Memory rule measured on the 3.14.0 bindings: data.warning (like data.solver)
   * is a live reference into mjData and must NOT be deleted; deleting it frees
   * mjData's own buffer and later aborts with a double free. Elements returned
   * by .get(i) are copies and must be deleted. data.contact, by contrast, is a
   * copy of the whole vector and must be deleted.
   */
  checkWarnings() {
    const w = this.data.warning;
    const names = ["inertia", "contactfull", "cnstrfull", "badqpos", "badqvel", "badqacc", "badctrl"];
    const count = Math.min(names.length, w.size());
    for (let i = 0; i < count; i++) {
      const stat = w.get(i);
      const n = stat.number;
      stat.delete();
      if (n > this._warnSeen[i]) {
        this._warnSeen[i] = n;
        this.emit("warning", { kind: names[i], count: n, time: this.data.time });
      }
    }
  }

  /** A DoubleBuffer that is freed with the Sim. */
  buffer(n) {
    const b = outBuffer(this.mj, n);
    this._buffers.push(b);
    return b;
  }

  /** Contacts as plain objects: geoms, position, frame and 6-D force in the contact frame. */
  contacts() {
    const { mj, model, data } = this;
    const out = [];
    if (data.ncon === 0) return out;
    const f = this._fbuf || (this._fbuf = this.buffer(6));
    const vec = data.contact;
    for (let i = 0; i < data.ncon; i++) {
      const c = vec.get(i);
      mj.mj_contactForce(model, data, i, f);
      const fv = f.GetView();
      out.push({
        geom1: c.geom1, geom2: c.geom2, dist: c.dist,
        pos: Array.from(c.pos), frame: Array.from(c.frame),
        force: Array.from(fv), active: c.efc_address >= 0, dim: c.dim,
      });
      c.delete();
    }
    vec.delete();
    return out;
  }

  /** Kinetic + potential energy (enables the energy flag on first use). */
  energy() {
    const { mj, model, data } = this;
    const bit = mj.mjtEnableBit.mjENBL_ENERGY.value;
    if (!(model.opt.enableflags & bit)) {
      model.opt.enableflags |= bit;
      mj.mj_forward(model, data);
    }
    return { potential: data.energy[0], kinetic: data.energy[1], total: data.energy[0] + data.energy[1] };
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.listeners.clear();
    this.recorders.clear();
    for (const b of this._buffers) b.delete();
    this.data.delete();
    this.model.delete();
  }
}

/** Helpers that read named rows out of the flat arrays the bindings expose. */
export function vec3(arr, i) { return [arr[3 * i], arr[3 * i + 1], arr[3 * i + 2]]; }
export function mat3(arr, i) { return Array.from(arr.subarray(9 * i, 9 * i + 9)); }
