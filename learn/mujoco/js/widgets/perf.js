// perf: how many MuJoCo steps per second this browser sustains, for 1 to 1000
// independent simulations of the same model, single-threaded WebAssembly.
//
// Each environment is its own MjData; all share one MjModel. The model is
// compiled with <size memory="512K"/>: MuJoCo's default arena for these models is
// about 13 to 14 MiB per MjData (it is a guess made at compile time), so 1000
// environments would need over 13 GB, beyond WebAssembly's 2 GB heap. The
// course measured actual use at 0.3 KiB (cart-pole) and 73 KiB (pick-and-place).
//
// Config: {"models": [["cartpole", "Cart-pole"], ["pick_place", "Pick-and-place"]], "counts": [1, 10, 100, 1000]}

import { h, frame, select, button, fmt } from "./ui.js";
import { getMujoco, modelSource, compileXml } from "../runtime.js";

export async function mount(el, config = {}) {
  const { body } = frame(el, { title: config.title || "Steps per second in this browser", kind: "Benchmark" });
  const mj = await getMujoco();
  const models = config.models || [["cartpole", "Cart-pole (2 DOF, no contacts)"], ["pick_place", "Pick-and-place (27 DOF, contacts)"]];
  const counts = config.counts || [1, 10, 100, 1000];
  let modelName = models[0][0];
  let running = false;

  const table = h("table", {}, h("thead", {}, h("tr", {}, ["environments", "steps/s", "x real time", "ms per step", "heap (MB)"].map((t) => h("th", {}, t)))));
  const tbody = h("tbody");
  table.appendChild(tbody);
  const status = h("p", { class: "widget__note" }, "Press Run. The benchmark runs in short slices so the page stays responsive.");
  const runBtn = button("Run", () => run(), "btn btn--primary");
  body.append(h("div", { class: "controls" }, select({ label: "model", options: models, value: modelName, onChange: (v) => { modelName = v; } })),
    h("div", { class: "toolbar" }, runBtn), h("div", { class: "arrays" }, table), status);

  const sleep = () => new Promise((r) => setTimeout(r, 0));

  async function run() {
    if (running) return;
    running = true;
    runBtn.disabled = true;
    tbody.replaceChildren();
    const xml = (await modelSource(modelName)).replace(/<mujoco([^>]*)>/, '<mujoco$1>\n  <size memory="512K"/>');
    const model = await compileXml(xml);
    const keyId = model.nkey > 1 ? 1 : -1;
    try {
      for (const n of counts) {
        status.textContent = `Running ${n} environment${n > 1 ? "s" : ""}...`;
        await sleep();
        const datas = [];
        try {
          for (let i = 0; i < n; i++) {
            const d = new mj.MjData(model);
            if (keyId >= 0) mj.mj_resetDataKeyframe(model, d, keyId);
            datas.push(d);
          }
        } catch (err) {
          datas.forEach((d) => d.delete());
          tbody.appendChild(h("tr", {}, h("td", {}, String(n)), h("td", { colspan: 4 }, `could not allocate: ${String(err.message || err).slice(0, 80)}`)));
          break;
        }
        // Step budget: aim for roughly one second of work per row.
        const t0 = performance.now();
        let steps = 0;
        while (performance.now() - t0 < 1000) {
          for (const d of datas) for (let k = 0; k < 10; k++) mj.mj_step(model, d);
          steps += 10 * n;
          if (performance.now() - t0 > 200) await sleep();      // yield now and then
        }
        const secs = (performance.now() - t0) / 1000;
        const sps = steps / secs;
        const heap = datas[0].qpos.buffer.byteLength / 2 ** 20;
        tbody.appendChild(h("tr", {}, h("td", {}, String(n)), h("td", {}, Math.round(sps).toLocaleString()),
          h("td", {}, fmt(sps * model.opt.timestep, 1)), h("td", {}, fmt(1000 / sps, 4)), h("td", {}, fmt(heap, 0))));
        datas.forEach((d) => d.delete());
      }
      status.textContent = "Done. Compare with the Python table above; this is one thread, with yields to keep the page alive.";
    } finally {
      model.delete();
      running = false;
      runBtn.disabled = false;
    }
  }
  return { destroy() { running = false; } };
}
