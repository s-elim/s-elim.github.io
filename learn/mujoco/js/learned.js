// A learned dynamics model in the browser: the MLP of Lesson 23.2, exported by examples/l23_2_learned_dynamics.py
// to data/l23_2_dynamics.json (weights as base64 float32). It predicts the next 16-number planar state from the
// current one and a pusher action, exactly as mjcourse.worldmodel.dynamics.DynamicsModel does in Python.

function decode(b64, n) {
  const bin = atob(b64), bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const out = new Float32Array(bytes.buffer);
  if (out.length !== n) throw new Error(`expected ${n} weights, got ${out.length}`);
  return out;
}

export async function loadDynamics(url = new URL("../data/l23_2_dynamics.json", import.meta.url)) {
  const blob = await (await fetch(url)).json();
  const layers = blob.layers.map((l) => ({ out: l.out, in: l.in, w: decode(l.w, l.out * l.in), b: decode(l.b, l.out) }));
  return new Dynamics(layers, blob);
}

const silu = (x) => x / (1 + Math.exp(-x));

export class Dynamics {
  constructor(layers, blob) {
    this.layers = layers;
    this.sMean = Float64Array.from(blob.s_mean); this.sStd = Float64Array.from(blob.s_std);
    this.dMean = Float64Array.from(blob.d_mean); this.dStd = Float64Array.from(blob.d_std);
    this.source = blob.source;
  }

  /** Next state (Float64Array(16)) from a state (16) and an action (2), one step of 0.1 s. */
  step(s, a) {
    let x = new Float64Array(18);
    for (let i = 0; i < 16; i++) x[i] = (s[i] - this.sMean[i]) / this.sStd[i];
    x[16] = a[0]; x[17] = a[1];
    this.layers.forEach((l, k) => {
      const y = new Float64Array(l.out);
      for (let o = 0; o < l.out; o++) {
        let acc = l.b[o];
        const row = o * l.in;
        for (let i = 0; i < l.in; i++) acc += l.w[row + i] * x[i];
        y[o] = k < this.layers.length - 1 ? silu(acc) : acc;
      }
      x = y;
    });
    const next = new Float64Array(16);
    for (let i = 0; i < 16; i++) next[i] = s[i] + x[i] * this.dStd[i] + this.dMean[i];
    return next;
  }

  /** Open-loop prediction: [s0, s1, ..., sH] under actions [a0, ..., a(H-1)]. */
  rollout(s0, actions) {
    const out = [Float64Array.from(s0)];
    for (const a of actions) out.push(this.step(out[out.length - 1], a));
    return out;
  }
}
