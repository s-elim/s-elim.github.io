// One requestAnimationFrame loop for every lab on the page.
//
// Each lab registers a tick(wallDt) callback and an element. Labs that are
// scrolled out of view are not stepped or rendered, so a lesson with several
// simulations costs no more than the ones on screen.

const entries = new Set();
let running = false;
let last = 0;
let active = null;

const observer = new IntersectionObserver((records) => {
  for (const r of records) {
    for (const e of entries) if (e.el === r.target) e.visible = r.isIntersecting;
  }
}, { rootMargin: "120px" });

function frame(now) {
  const dt = last ? (now - last) / 1000 : 0;
  last = now;
  for (const e of entries) {
    if (!e.visible || document.hidden) continue;
    try { e.tick(dt); } catch (err) { console.error("[lab]", err); e.visible = false; }
  }
  if (entries.size) requestAnimationFrame(frame);
  else { running = false; last = 0; }
}

/**
 * Register a lab. `controls` may expose { toggle, step, reset } for keyboard
 * shortcuts. Returns an unregister function.
 */
export function register(el, tick, controls = {}) {
  const entry = { el, tick, controls, visible: false };
  entries.add(entry);
  observer.observe(el);
  el.addEventListener("pointerenter", () => { active = entry; });
  if (!running) { running = true; requestAnimationFrame(frame); }
  return () => {
    observer.unobserve(el);
    entries.delete(entry);
    if (active === entry) active = null;
  };
}

/** The lab keyboard shortcuts act on: the one under the pointer, else the first visible. */
export function activeLab() {
  if (active && entries.has(active)) return active.controls;
  for (const e of entries) if (e.visible) return e.controls;
  return null;
}
