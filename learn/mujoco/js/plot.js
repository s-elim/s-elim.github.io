// Plot: a small dependency-free canvas plotter for live lab signals.
//
// Modes
//   "time"  rolling time series: push(t, [v1, v2, ...]); x axis is time in s
//   "xy"    arbitrary series:    setSeries(i, xs, ys); for phase plots, sweeps
//   "hist"  histogram:           setHistogram(values, {bins, range})
//
// Colours come from the Okabe-Ito palette, which stays distinguishable under the
// common forms of colour-vision deficiency. Axis labels carry units; every lab
// that plots a quantity names its unit in the trace label.

export const PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#7a7a7a"];

function css(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function niceStep(span, target = 5) {
  const raw = span / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10;
  return step * mag;
}

function fmt(v) {
  const a = Math.abs(v);
  if (a !== 0 && (a < 1e-3 || a >= 1e4)) return v.toExponential(1);
  return String(Number(v.toPrecision(4)));
}

export class Plot {
  /**
   * @param container element to fill
   * @param opts { mode, traces: [{label, color?, dash?}], xlabel, ylabel,
   *               window (s, time mode), ymin, ymax, symmetric, refLines: [{y, label}],
   *               height }
   */
  constructor(container, opts = {}) {
    this.opts = { mode: "time", window: 5, height: 150, ...opts };
    this.traces = (opts.traces || []).map((t, i) => ({ color: PALETTE[i % PALETTE.length], ...t }));
    this.wrap = document.createElement("div");
    this.wrap.className = "plot";
    this.canvas = document.createElement("canvas");
    this.canvas.style.height = `${this.opts.height}px`;
    this.legend = document.createElement("div");
    this.legend.className = "plot-legend";
    this.wrap.append(this.canvas, this.legend);
    container.appendChild(this.wrap);
    this.clear();
    this._renderLegend();
    this._ro = new ResizeObserver(() => this.draw());
    this._ro.observe(this.canvas);
  }

  _renderLegend() {
    this.legend.innerHTML = "";
    for (const t of this.traces) {
      const item = document.createElement("span");
      item.className = "plot-legend__item";
      const sw = document.createElement("i");
      sw.style.background = t.dash
        ? `repeating-linear-gradient(90deg, ${t.color} 0 4px, transparent 4px 7px)`
        : t.color;
      item.append(sw, document.createTextNode(t.label));
      this.legend.appendChild(item);
    }
  }

  setTraces(traces) {
    this.traces = traces.map((t, i) => ({ color: PALETTE[i % PALETTE.length], ...t }));
    this.clear();
    this._renderLegend();
  }

  clear() {
    this.t = [];
    this.series = this.traces.map(() => ({ xs: [], ys: [] }));
    this.hist = null;
    this.draw();
  }

  /** Append one sample to every trace (time mode). */
  push(t, values) {
    if (this.t.length && t < this.t[this.t.length - 1]) this.clear(); // time went backwards: a reset
    this.t.push(t);
    values.forEach((v, i) => { if (this.series[i]) this.series[i].ys.push(v); });
    const cutoff = t - this.opts.window * 1.2;
    let drop = 0;
    while (drop < this.t.length && this.t[drop] < cutoff) drop++;
    if (drop > 256) {
      this.t.splice(0, drop);
      this.series.forEach((s) => s.ys.splice(0, drop));
    }
  }

  setSeries(i, xs, ys) {
    while (this.series.length <= i) this.series.push({ xs: [], ys: [] });
    this.series[i] = { xs: Array.from(xs), ys: Array.from(ys) };
  }

  setHistogram(values, { bins = 20, range = null } = {}) {
    const vals = values.filter(Number.isFinite);
    const lo = range ? range[0] : Math.min(...vals), hi = range ? range[1] : Math.max(...vals);
    const width = (hi - lo) / bins || 1;
    const counts = new Array(bins).fill(0);
    for (const v of vals) counts[Math.min(bins - 1, Math.max(0, Math.floor((v - lo) / width)))]++;
    this.hist = { lo, hi, counts, n: vals.length };
  }

  _extent() {
    const o = this.opts;
    let x0, x1;
    if (o.mode === "time") {
      const tEnd = this.t.length ? this.t[this.t.length - 1] : 0;
      x1 = Math.max(tEnd, o.window); x0 = x1 - o.window;
    } else if (o.mode === "hist" && this.hist) {
      x0 = this.hist.lo; x1 = this.hist.hi;
    } else {
      const xs = this.series.flatMap((s) => s.xs);
      x0 = o.xmin ?? (xs.length ? Math.min(...xs) : 0);
      x1 = o.xmax ?? (xs.length ? Math.max(...xs) : 1);
    }
    let y0 = o.ymin, y1 = o.ymax;
    if (y0 == null || y1 == null) {
      let lo = Infinity, hi = -Infinity;
      if (o.mode === "hist" && this.hist) { lo = 0; hi = Math.max(...this.hist.counts, 1); }
      else {
        for (let s = 0; s < this.series.length; s++) {
          const ys = this.series[s].ys;
          for (let k = 0; k < ys.length; k++) {
            if (o.mode === "time" && this.t[k] < x0) continue;
            const v = ys[k];
            if (Number.isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; }
          }
        }
        for (const r of o.refLines || []) { lo = Math.min(lo, r.y); hi = Math.max(hi, r.y); }
      }
      if (!Number.isFinite(lo)) { lo = -1; hi = 1; }
      if (o.symmetric) { const m = Math.max(Math.abs(lo), Math.abs(hi)); lo = -m; hi = m; }
      // Never zoom into floating-point noise: enforce a minimum span relative to the values.
      const minSpan = o.minSpan ?? Math.max(1e-9, 0.02 * Math.max(Math.abs(lo), Math.abs(hi)));
      if (hi - lo < minSpan) { const mid = (hi + lo) / 2; lo = mid - minSpan / 2; hi = mid + minSpan / 2; }
      const pad = (hi - lo) * 0.08 || Math.abs(hi) * 0.1 || 1;
      y0 = y0 ?? lo - pad; y1 = y1 ?? hi + pad;
    }
    if (x1 - x0 < 1e-12) x1 = x0 + 1;
    return { x0, x1, y0, y1 };
  }

  draw() {
    const c = this.canvas;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = c.clientWidth, H = c.clientHeight;
    if (!W || !H) return;
    if (c.width !== Math.round(W * dpr) || c.height !== Math.round(H * dpr)) {
      c.width = Math.round(W * dpr); c.height = Math.round(H * dpr);
    }
    const g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, W, H);
    const ink = css("--ink-2", "#4c5b57"), line = css("--line", "#d8ddd6"), mono = css("--mono", "monospace");
    const L = this.opts.ylabel ? 62 : 48, R = 8, T = 8, B = this.opts.xlabel ? 30 : 18;
    const pw = W - L - R, ph = H - T - B;
    const { x0, x1, y0, y1 } = this._extent();
    const X = (x) => L + ((x - x0) / (x1 - x0)) * pw;
    const Y = (y) => T + (1 - (y - y0) / (y1 - y0)) * ph;

    g.font = `10px ${mono}`;
    g.fillStyle = ink;
    g.strokeStyle = line;
    g.lineWidth = 1;
    const ys = niceStep(y1 - y0, 4);
    for (let v = Math.ceil(y0 / ys) * ys; v <= y1 + 1e-12; v += ys) {
      const y = Math.round(Y(v)) + 0.5;
      g.beginPath(); g.moveTo(L, y); g.lineTo(L + pw, y); g.stroke();
      g.textAlign = "right"; g.textBaseline = "middle"; g.fillText(fmt(v), L - 4, y);
    }
    const xs = niceStep(x1 - x0, Math.max(3, Math.floor(pw / 70)));
    for (let v = Math.ceil(x0 / xs) * xs; v <= x1 + 1e-12; v += xs) {
      const x = Math.round(X(v)) + 0.5;
      g.beginPath(); g.moveTo(x, T); g.lineTo(x, T + ph); g.stroke();
      g.textAlign = "center"; g.textBaseline = "top"; g.fillText(fmt(v), x, T + ph + 3);
    }
    if (this.opts.xlabel) { g.textAlign = "center"; g.fillText(this.opts.xlabel, L + pw / 2, H - 11); }
    if (this.opts.ylabel) {
      g.save(); g.translate(9, T + ph / 2); g.rotate(-Math.PI / 2);
      g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(this.opts.ylabel, 0, 0); g.restore();
    }

    g.save();
    g.beginPath(); g.rect(L, T, pw, ph); g.clip();
    for (const r of this.opts.refLines || []) {
      g.strokeStyle = ink; g.setLineDash([4, 4]);
      g.beginPath(); g.moveTo(L, Y(r.y)); g.lineTo(L + pw, Y(r.y)); g.stroke();
      g.setLineDash([]);
      if (r.label) { g.textAlign = "left"; g.textBaseline = "bottom"; g.fillText(r.label, L + 4, Y(r.y) - 2); }
    }
    if (this.opts.mode === "hist" && this.hist) {
      const { lo, hi, counts } = this.hist;
      const bw = (hi - lo) / counts.length;
      g.fillStyle = this.traces[0]?.color || PALETTE[0];
      counts.forEach((n, i) => {
        const xa = X(lo + i * bw), xb = X(lo + (i + 1) * bw);
        g.fillRect(xa + 1, Y(n), Math.max(xb - xa - 2, 1), Y(0) - Y(n));
      });
    } else {
      this.series.forEach((s, i) => {
        const tr = this.traces[i] || { color: PALETTE[i % PALETTE.length] };
        const xsData = this.opts.mode === "time" ? this.t : s.xs;
        g.strokeStyle = tr.color; g.lineWidth = tr.width || 1.6;
        g.setLineDash(tr.dash ? [5, 4] : []);
        if (tr.points) {
          g.fillStyle = tr.color;
          for (let k = 0; k < s.ys.length; k++) {
            if (!Number.isFinite(s.ys[k])) continue;
            g.beginPath(); g.arc(X(xsData[k]), Y(s.ys[k]), tr.radius || 2.2, 0, 2 * Math.PI); g.fill();
          }
          return;
        }
        g.beginPath();
        let pen = false;
        for (let k = 0; k < s.ys.length; k++) {
          const xv = xsData[k], yv = s.ys[k];
          if (!Number.isFinite(yv) || xv < x0 - (x1 - x0)) { pen = false; continue; }
          const px = X(xv), py = Y(yv);
          if (pen) g.lineTo(px, py); else { g.moveTo(px, py); pen = true; }
        }
        g.stroke();
      });
      g.setLineDash([]);
    }
    g.restore();
    g.strokeStyle = ink;
    g.strokeRect(L + 0.5, T + 0.5, pw, ph);
  }

  /** Download the plotted data as CSV (time mode or xy mode). */
  toCSV() {
    const header = ["x", ...this.traces.map((t) => t.label)];
    const rows = [header.join(",")];
    const n = this.opts.mode === "time" ? this.t.length : Math.max(0, ...this.series.map((s) => s.xs.length));
    for (let k = 0; k < n; k++) {
      const x = this.opts.mode === "time" ? this.t[k] : this.series[0]?.xs[k];
      rows.push([x, ...this.series.map((s) => s.ys[k])].join(","));
    }
    return rows.join("\n");
  }

  dispose() { this._ro.disconnect(); this.wrap.remove(); }
}
