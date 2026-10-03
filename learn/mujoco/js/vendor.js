// Pinned third-party URLs. Every external dependency of the course is listed here,
// so moving to self-hosted copies is a change to this file only.
//
// MuJoCo is the official Google DeepMind WebAssembly build (npm @mujoco/mujoco),
// whose version numbers track MuJoCo releases one to one. The single-threaded
// build is used because it needs no cross-origin-isolation headers, which
// GitHub Pages cannot send.

export const MUJOCO_VERSION = "3.14.0";
export const MUJOCO_JS = `https://cdn.jsdelivr.net/npm/@mujoco/mujoco@${MUJOCO_VERSION}/mujoco.js`;

export const THREE_VERSION = "0.170.0";
export const THREE_JS = `https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/build/three.module.js`;
export const ORBIT_CONTROLS_JS = `https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/examples/jsm/controls/OrbitControls.js`;

export const MARKED_JS = "https://cdn.jsdelivr.net/npm/marked@15.0.7/lib/marked.esm.js";
export const KATEX_JS = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.11/katex.min.js";
export const KATEX_CSS = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.11/katex.min.css";
export const HLJS_JS = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/highlight.min.js";
export const HLJS_LANGS = ["python", "xml", "bash", "javascript", "yaml", "json"].map(
  (l) => `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/languages/${l}.min.js`
);
export const CODEMIRROR_JS = "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.18/codemirror.min.js";
export const CODEMIRROR_CSS = "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.18/codemirror.min.css";
export const CODEMIRROR_XML = "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.18/mode/xml/xml.min.js";

// Classic (non-module) scripts and stylesheets are loaded once and memoised.
const loaded = new Map();

export function loadScript(src) {
  if (!loaded.has(src)) {
    loaded.set(src, new Promise((resolve, reject) => {
      const el = document.createElement("script");
      el.src = src;
      el.async = false; // preserve order for dependent scripts (hljs languages)
      el.onload = () => resolve();
      el.onerror = () => reject(new Error(`could not load ${src}`));
      document.head.appendChild(el);
    }));
  }
  return loaded.get(src);
}

export function loadStyle(href) {
  if (!loaded.has(href)) {
    loaded.set(href, new Promise((resolve, reject) => {
      const el = document.createElement("link");
      el.rel = "stylesheet";
      el.href = href;
      el.onload = () => resolve();
      el.onerror = () => reject(new Error(`could not load ${href}`));
      document.head.appendChild(el);
    }));
  }
  return loaded.get(href);
}
