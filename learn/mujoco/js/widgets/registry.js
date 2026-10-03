// Widget registry: maps a directive name to the module that implements it.
// Modules load on first use, so a lesson pays only for the labs it contains.
//
// Every module exports `mount(el, config, ctx)` returning { destroy() }.

const MODULES = {
  simlab: () => import("./simlab.js"),
  playground: () => import("./playground.js"),
  inspector: () => import("./inspector.js"),
  quiz: () => import("./quiz.js"),
  io: () => import("./io.js"),
  debug: () => import("./debugcase.js"),
  integrators: () => import("./integrators.js"),
  frames: () => import("./frames.js"),
  fk2: () => import("./fk2.js"),
  ik: () => import("./ik.js"),
  dynamics: () => import("./dynamics.js"),
  pd: () => import("./pd.js"),
  osc: () => import("./osc.js"),
  pickplace: () => import("./pickplace.js"),
  contact: () => import("./contact.js"),
  incline: () => import("./incline.js"),
  grasp: () => import("./grasp.js"),
  camera: () => import("./camera.js"),
  rl: () => import("./rl.js"),
  bc: () => import("./bc.js"),
  dr: () => import("./dr.js"),
  sysid: () => import("./sysid.js"),
  sim2real: () => import("./sim2real.js"),
  pipeline: () => import("./pipeline.js"),
  perf: () => import("./perf.js"),
  mpc: () => import("./mpc.js"),
};

export function hasWidget(name) { return name in MODULES; }

export async function mountWidget(name, el, config, ctx) {
  const loader = MODULES[name];
  if (!loader) {
    el.innerHTML = `<div class="widget__error">Unknown lab "${String(name)}".</div>`;
    return null;
  }
  try {
    const mod = await loader();
    return await mod.mount(el, config, ctx);
  } catch (err) {
    console.error(`[widget ${name}]`, err);
    el.innerHTML = `<div class="widget"><div class="widget__body"><div class="widget__error">This lab could not start: ${String(err.message || err)}</div><p class="widget__note">The lesson text and the Python companion code do not depend on it. If the message mentions WebAssembly or a network error, reload the page; MuJoCo's WebAssembly module is about 10 MB.</p></div></div>`;
    return null;
  }
}
