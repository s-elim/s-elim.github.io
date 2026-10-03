// MuJoCo WebAssembly runtime: one module instance per page, plus model loading.
//
// INPUT   a model name from the course library ("pendulum") or raw MJCF text
// PROCESS fetch the XML and every file it references into a MuJoCo virtual
//         file system (VFS), then compile with MjModel.from_xml_string
// OUTPUT  an MjModel handle (caller owns it and must call .delete())
//
// Two facts about the 3.14.0 bindings shape this file:
//  * Objects created through the bindings live on the WASM heap and are not
//    garbage collected; every MjModel, MjData, buffer and VFS must be deleted.
//  * Functions that write into an output array need a mujoco.DoubleBuffer (or
//    IntBuffer). A plain Float64Array is copied in and the result is discarded
//    silently. See outBuffer() below.

import { MUJOCO_JS, MUJOCO_VERSION } from "./vendor.js";

export const MODELS_URL = new URL("../code/src/mjcourse/models/", import.meta.url);

let modulePromise = null;

/** Load (once) and return the MuJoCo module. */
export function getMujoco() {
  if (!modulePromise) {
    modulePromise = import(MUJOCO_JS)
      .then((m) => m.default())
      .then((mj) => {
        const v = mj.mj_versionString();
        if (v !== MUJOCO_VERSION) {
          console.warn(`[mujoco] expected ${MUJOCO_VERSION}, loaded ${v}`);
        }
        return mj;
      })
      .catch((err) => {
        modulePromise = null; // allow a retry after a network failure
        throw new Error(`MuJoCo ${MUJOCO_VERSION} (WebAssembly) could not be loaded: ${err.message}`);
      });
  }
  return modulePromise;
}

const textCache = new Map();
const binCache = new Map();

async function fetchText(url) {
  const key = String(url);
  if (!textCache.has(key)) {
    textCache.set(key, fetch(url).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status} fetching ${key}`);
      return r.text();
    }));
  }
  return textCache.get(key);
}

async function fetchBytes(url) {
  const key = String(url);
  if (!binCache.has(key)) {
    binCache.set(key, fetch(url).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status} fetching ${key}`);
      return r.arrayBuffer();
    }).then((b) => new Uint8Array(b)));
  }
  return binCache.get(key);
}

/** Raw MJCF text of a library model. */
export async function modelSource(name) {
  const file = name.endsWith(".xml") ? name : `${name}.xml`;
  return fetchText(new URL(file, MODELS_URL));
}

// Every attribute that names a file: <include file>, <model file>, <mesh file>,
// <texture file>, <hfield file>, <skin file>. Directory attributes such as
// compiler/meshdir are not used by the course models and are not resolved here.
const FILE_ATTR = /\bfile\s*=\s*"([^"]+)"/g;

/**
 * Collect every file referenced (recursively) by `xml`, relative to MODELS_URL.
 * Returns a Map from the path as written in the XML to its bytes.
 */
export async function collectAssets(xml, seen = new Map()) {
  const pending = [];
  for (const match of xml.matchAll(FILE_ATTR)) {
    const path = match[1];
    if (seen.has(path)) continue;
    seen.set(path, null);
    pending.push((async () => {
      const url = new URL(path, MODELS_URL);
      if (path.endsWith(".xml")) {
        const text = await fetchText(url);
        seen.set(path, new TextEncoder().encode(text));
        await collectAssets(text, seen);
      } else {
        seen.set(path, await fetchBytes(url));
      }
    })());
  }
  await Promise.all(pending);
  return seen;
}

/**
 * Compile MJCF text into an MjModel. Throws an Error whose message is MuJoCo's
 * own compiler message (with line numbers) when the XML is invalid.
 */
export async function compileXml(xml) {
  const mj = await getMujoco();
  const assets = await collectAssets(xml);
  const vfs = new mj.MjVFS();
  try {
    for (const [path, bytes] of assets) vfs.addBuffer(path, bytes);
    return mj.MjModel.from_xml_string(xml, vfs);
  } catch (err) {
    throw new Error(cleanMujocoError(err));
  } finally {
    vfs.delete();
  }
}

/** Load a library model by name. */
export async function loadModel(name) {
  return compileXml(await modelSource(name));
}

export function cleanMujocoError(err) {
  const s = String(err && err.message ? err.message : err);
  return s.replace(/^(Error:\s*)+/, "").replace(/MuJoCo Error:\s*/g, "").trim();
}

/** Allocate an output buffer the bindings can write into (remember .delete()). */
export function outBuffer(mj, n) {
  return new mj.DoubleBuffer(n);
}

/** Look up an object id by name; returns -1 when absent. */
export function idOf(mj, model, objType, name) {
  return mj.mj_name2id(model, mj.mjtObj[objType].value, name);
}

/** Name of object `id` of a given type ("" when unnamed). */
export function nameOf(mj, model, objType, id) {
  return mj.mj_id2name(model, mj.mjtObj[objType].value, id) || "";
}

/**
 * Read a boolean model field through the named accessor.
 *
 * Measured on the 3.14.0 bindings: arrays of MuJoCo's byte-sized booleans
 * (jnt_limited, actuator_ctrllimited, actuator_forcelimited, tendon_limited,
 * eq_active0 and 13 others on mjModel; eq_active and bvh_active on mjData)
 * throw "_emval_take_value has unknown type" when read as arrays. The named
 * accessors (model.jnt(i).limited, model.actuator(i).ctrllimited) work.
 * Accessor handles live on the WASM heap, so this deletes the handle it creates.
 */
export function flag(model, accessor, index, field) {
  const acc = model[accessor](index);
  try { return Boolean(acc[field]); } finally { acc.delete(); }
}
