// Viewer: draws a MuJoCo model with three.js, reading poses straight from mjData.
//
// INPUT   a Sim (MjModel + MjData)
// PROCESS once: build one three.js mesh per geom from model.geom_type/size/rgba
//                (and mesh_vert/mesh_face for mesh geoms);
//         every frame: copy data.geom_xpos / data.geom_xmat into each mesh's
//                matrix, then draw optional overlays from data (frames, joint
//                axes, contacts and contact forces, centres of mass, cameras).
// OUTPUT  pixels on a canvas, plus pick() and drag-to-perturb interaction.
//
// This is a course renderer, not MuJoCo's own OpenGL renderer: shading, shadows
// and textures differ. Geometry and every pose are MuJoCo's, frame for frame.
// MuJoCo is z-up; the three.js camera is given up = +z so world coordinates are
// used unchanged. A MuJoCo camera looks along its local -z with +y up, which is
// also the three.js camera convention, so model cameras map over directly.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const GEOM = { PLANE: 0, HFIELD: 1, SPHERE: 2, CAPSULE: 3, ELLIPSOID: 4, CYLINDER: 5, BOX: 6, MESH: 7, SDF: 8 };
const JNT = { FREE: 0, BALL: 1, SLIDE: 2, HINGE: 3 };

export const DEFAULT_OVERLAYS = {
  frames: false, joints: false, contacts: false, forces: false, com: false,
  sites: false, cameras: false, shadows: true, groups: [true, true, true, false, false, false],
};

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export class Viewer {
  constructor(container, sim, opts = {}) {
    this.container = container;
    this.overlays = { ...DEFAULT_OVERLAYS, ...(opts.overlays || {}) };
    this.forceScale = opts.forceScale ?? 0.02;   // metres of arrow per newton
    this.onPick = opts.onPick || null;
    this.trailSite = null;
    this.trail = [];

    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.domElement.className = "viewer-canvas";
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.01, 100);
    this.camera.up.set(0, 0, 1);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.12;

    this._resizeObserver = new ResizeObserver(() => this.resize());
    this._resizeObserver.observe(container);
    this._setupInteraction();
    this.setSim(sim, opts.camera);
  }

  // ---------------------------------------------------------------- building

  setSim(sim, cameraOpts) {
    this.sim = sim;
    this._clearScene();
    const { model } = sim;
    this._lights();
    this.geomMeshes = [];
    for (let g = 0; g < model.ngeom; g++) this.geomMeshes.push(this._buildGeom(g));
    this._buildOverlays();
    this.frameCamera(cameraOpts);
    this.update();
  }

  _clearScene() {
    this.scene.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose());
    });
    this.scene.clear();
    this.trail = [];
  }

  _lights() {
    const bg = new THREE.Color(cssVar("--viewer-bg", "#e9ece8"));
    this.scene.background = bg;
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8f88, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    const ext = Math.max(this.sim.model.stat.extent, 0.5);
    const c = this.sim.model.stat.center;
    sun.position.set(c[0] + ext, c[1] - ext * 1.2, c[2] + ext * 2.2);
    sun.target.position.set(c[0], c[1], c[2]);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    const s = ext * 1.5;
    Object.assign(sun.shadow.camera, { left: -s, right: s, top: s, bottom: -s, near: 0.01, far: ext * 8 });
    sun.shadow.bias = -0.0005;
    this.sun = sun;
    this.scene.add(sun, sun.target);
  }

  _geomColor(g) {
    const { model } = this.sim;
    let rgba = model.geom_rgba.subarray(4 * g, 4 * g + 4);
    const mat = model.geom_matid[g];
    const isDefault = Math.abs(rgba[0] - 0.5) < 1e-6 && Math.abs(rgba[1] - 0.5) < 1e-6 && Math.abs(rgba[2] - 0.5) < 1e-6;
    if (mat >= 0 && isDefault) rgba = model.mat_rgba.subarray(4 * mat, 4 * mat + 4);
    return rgba;
  }

  _buildGeom(g) {
    const { model } = this.sim;
    const type = model.geom_type[g];
    const size = model.geom_size.subarray(3 * g, 3 * g + 3);
    let geometry = null;
    switch (type) {
      case GEOM.PLANE: {
        const sx = size[0] > 0 ? size[0] : 5, sy = size[1] > 0 ? size[1] : 5;
        geometry = new THREE.PlaneGeometry(2 * sx, 2 * sy);
        break;
      }
      case GEOM.SPHERE: geometry = new THREE.SphereGeometry(size[0], 32, 16); break;
      case GEOM.ELLIPSOID: geometry = new THREE.SphereGeometry(1, 32, 16).scale(size[0], size[1], size[2]); break;
      case GEOM.CAPSULE:
        geometry = new THREE.CapsuleGeometry(size[0], 2 * size[1], 8, 24).rotateX(Math.PI / 2);
        break;
      case GEOM.CYLINDER:
        geometry = new THREE.CylinderGeometry(size[0], size[0], 2 * size[1], 32).rotateX(Math.PI / 2);
        break;
      case GEOM.BOX: geometry = new THREE.BoxGeometry(2 * size[0], 2 * size[1], 2 * size[2]); break;
      case GEOM.MESH: geometry = this._meshGeometry(model.geom_dataid[g]); break;
      default: return null; // height fields and SDFs are not drawn by the course viewer
    }
    const rgba = this._geomColor(g);
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(rgba[0], rgba[1], rgba[2]),
      transparent: rgba[3] < 1, opacity: rgba[3], roughness: 0.65, metalness: 0.05,
      side: type === GEOM.PLANE ? THREE.DoubleSide : THREE.FrontSide,
    });
    if (type === GEOM.PLANE) {
      material.map = checkerTexture(rgba);
      const sx = size[0] > 0 ? size[0] : 5, sy = size[1] > 0 ? size[1] : 5;
      material.map.repeat.set(sx * 4, sy * 4);
    }
    const mesh = new THREE.Mesh(geometry, material);
    mesh.matrixAutoUpdate = false;
    mesh.castShadow = type !== GEOM.PLANE && rgba[3] > 0.5;
    mesh.receiveShadow = true;
    mesh.userData = { geom: g, body: model.geom_bodyid[g], group: model.geom_group[g] };
    this.scene.add(mesh);
    return mesh;
  }

  _meshGeometry(meshId) {
    const { model } = this.sim;
    const va = model.mesh_vertadr[meshId], vn = model.mesh_vertnum[meshId];
    const fa = model.mesh_faceadr[meshId], fn = model.mesh_facenum[meshId];
    const pos = new Float32Array(model.mesh_vert.subarray(3 * va, 3 * (va + vn)));
    const idx = new Uint32Array(model.mesh_face.subarray(3 * fa, 3 * (fa + fn)));
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geometry.setIndex(new THREE.BufferAttribute(idx, 1));
    geometry.computeVertexNormals();
    return geometry;
  }

  _buildOverlays() {
    const { model } = this.sim;
    this.overlayGroup = new THREE.Group();
    this.scene.add(this.overlayGroup);
    const ext = Math.max(model.stat.extent, 0.3);
    this.axisLen = 0.08 * ext;

    this.bodyFrames = [];
    for (let b = 1; b < model.nbody; b++) {
      const ax = new THREE.AxesHelper(this.axisLen);
      ax.matrixAutoUpdate = false;
      this.bodyFrames.push(ax);
      this.overlayGroup.add(ax);
    }
    this.jointArrows = [];
    for (let j = 0; j < model.njnt; j++) {
      const t = model.jnt_type[j];
      if (t !== JNT.HINGE && t !== JNT.SLIDE) { this.jointArrows.push(null); continue; }
      const color = t === JNT.HINGE ? 0xd9480f : 0x1971c2;
      const arrow = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(), this.axisLen * 1.6, color, this.axisLen * 0.35, this.axisLen * 0.2);
      this.jointArrows.push(arrow);
      this.overlayGroup.add(arrow);
    }
    this.comMarkers = [];
    const comGeo = new THREE.SphereGeometry(0.012 * ext, 12, 8);
    const comMat = new THREE.MeshBasicMaterial({ color: 0x7048e8, depthTest: false, transparent: true, opacity: 0.85 });
    for (let b = 1; b < model.nbody; b++) {
      const m = new THREE.Mesh(comGeo, comMat);
      m.renderOrder = 10;
      this.comMarkers.push(m);
      this.overlayGroup.add(m);
    }
    this.siteMeshes = [];
    const siteMat = new THREE.MeshBasicMaterial({ color: 0xf08c00, transparent: true, opacity: 0.9 });
    for (let s = 0; s < model.nsite; s++) {
      const r = Math.max(model.site_size[3 * s], 0.004);
      const m = new THREE.Mesh(new THREE.SphereGeometry(r, 12, 8), siteMat);
      m.matrixAutoUpdate = false;
      this.siteMeshes.push(m);
      this.overlayGroup.add(m);
    }
    this.cameraHelpers = [];
    for (let c = 0; c < model.ncam; c++) {
      const cam = new THREE.PerspectiveCamera(model.cam_fovy[c], 4 / 3, 0.02, 0.25 * ext);
      cam.matrixAutoUpdate = false;
      const helper = new THREE.CameraHelper(cam);
      this.cameraHelpers.push({ cam, helper });
      this.overlayGroup.add(helper);
    }
    // Contacts are drawn into pre-allocated pools that grow on demand.
    this.contactPool = [];
    this.contactGroup = new THREE.Group();
    this.overlayGroup.add(this.contactGroup);
    this.trailLine = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0xe8590c }));
    this.trailLine.frustumCulled = false;
    this.overlayGroup.add(this.trailLine);
  }

  frameCamera(opts = {}) {
    const { model } = this.sim;
    const c = model.stat.center, ext = Math.max(model.stat.extent, 0.3);
    const target = opts.target || [c[0], c[1], c[2]];
    const dist = opts.distance || ext * 1.9;
    const az = (opts.azimuth ?? -55) * Math.PI / 180, el = (opts.elevation ?? 25) * Math.PI / 180;
    this.controls.target.set(...target);
    this.camera.position.set(
      target[0] + dist * Math.cos(el) * Math.cos(az),
      target[1] + dist * Math.cos(el) * Math.sin(az),
      target[2] + dist * Math.sin(el));
    this.camera.near = Math.max(ext * 0.005, 0.002);
    this.camera.far = ext * 50;
    this.camera.updateProjectionMatrix();
    this.controls.update();
  }

  // ---------------------------------------------------------------- per frame

  update() {
    const { model, data } = this.sim;
    const m4 = new THREE.Matrix4();
    for (let g = 0; g < this.geomMeshes.length; g++) {
      const mesh = this.geomMeshes[g];
      if (!mesh) continue;
      const grp = model.geom_group[g];
      mesh.visible = grp < 6 ? this.overlays.groups[grp] : false;
      if (!mesh.visible) continue;
      setPose(mesh, data.geom_xpos, data.geom_xmat, g, m4);
    }
    const ov = this.overlays;
    this.sun.castShadow = ov.shadows;
    for (let b = 1; b < model.nbody; b++) {
      const ax = this.bodyFrames[b - 1];
      ax.visible = ov.frames;
      if (ov.frames) setPose(ax, data.xpos, data.xmat, b, m4);
      const com = this.comMarkers[b - 1];
      com.visible = ov.com && model.body_mass[b] > 0;
      if (com.visible) com.position.set(data.xipos[3 * b], data.xipos[3 * b + 1], data.xipos[3 * b + 2]);
    }
    for (let j = 0; j < this.jointArrows.length; j++) {
      const arrow = this.jointArrows[j];
      if (!arrow) continue;
      arrow.visible = ov.joints;
      if (!ov.joints) continue;
      arrow.position.set(data.xanchor[3 * j], data.xanchor[3 * j + 1], data.xanchor[3 * j + 2]);
      arrow.setDirection(new THREE.Vector3(data.xaxis[3 * j], data.xaxis[3 * j + 1], data.xaxis[3 * j + 2]));
    }
    for (let s = 0; s < this.siteMeshes.length; s++) {
      const m = this.siteMeshes[s];
      m.visible = ov.sites;
      if (ov.sites) setPose(m, data.site_xpos, data.site_xmat, s, m4);
    }
    for (let c = 0; c < this.cameraHelpers.length; c++) {
      const { cam, helper } = this.cameraHelpers[c];
      helper.visible = ov.cameras;
      if (!ov.cameras) continue;
      setPose(cam, data.cam_xpos, data.cam_xmat, c, m4);
      cam.matrixWorldNeedsUpdate = true;
      cam.updateMatrixWorld(true);
      helper.update();
    }
    this._updateContacts();
    this._updateTrail();
    this._applyDrag();
  }

  _updateContacts() {
    const ov = this.overlays;
    const show = ov.contacts || ov.forces;
    this.contactGroup.visible = show;
    if (!show) return;
    const contacts = this.sim.contacts();
    const ext = Math.max(this.sim.model.stat.extent, 0.3);
    while (this.contactPool.length < contacts.length) {
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.006 * ext, 10, 6), new THREE.MeshBasicMaterial({ color: 0x2f9e44, depthTest: false }));
      dot.renderOrder = 11;
      const normal = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(), 0.05 * ext, 0x2f9e44);
      const force = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(), 0.1, 0xe03131);
      const fric = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(), 0.1, 0x1c7ed6);
      [normal, force, fric].forEach((a) => { a.line.material.depthTest = false; a.cone.material.depthTest = false; a.renderOrder = 12; });
      this.contactGroup.add(dot, normal, force, fric);
      this.contactPool.push({ dot, normal, force, fric });
    }
    for (let i = 0; i < this.contactPool.length; i++) {
      const p = this.contactPool[i];
      const c = contacts[i];
      const on = i < contacts.length;
      p.dot.visible = on && ov.contacts;
      p.normal.visible = on && ov.contacts;
      p.force.visible = on && ov.forces;
      p.fric.visible = on && ov.forces;
      if (!on) continue;
      const pos = new THREE.Vector3(...c.pos);
      p.dot.position.copy(pos);
      const n = new THREE.Vector3(c.frame[0], c.frame[1], c.frame[2]);
      p.normal.position.copy(pos);
      p.normal.setDirection(n);
      // Force on geom2 in world coordinates: f_n * normal (+ friction along the two tangents).
      const t1 = new THREE.Vector3(c.frame[3], c.frame[4], c.frame[5]);
      const t2 = new THREE.Vector3(c.frame[6], c.frame[7], c.frame[8]);
      const fn = c.force[0];
      const ft = t1.clone().multiplyScalar(c.force[1]).add(t2.clone().multiplyScalar(c.force[2]));
      setArrow(p.force, pos, n.clone().multiplyScalar(fn), this.forceScale);
      setArrow(p.fric, pos, ft, this.forceScale);
    }
  }

  setTrail(siteId, maxPoints = 600) {
    this.trailSite = siteId;
    this.trailMax = maxPoints;
    this.trail = [];
  }

  _updateTrail() {
    if (this.trailSite == null || this.trailSite < 0) { this.trailLine.visible = false; return; }
    const d = this.sim.data, s = this.trailSite;
    this.trail.push(d.site_xpos[3 * s], d.site_xpos[3 * s + 1], d.site_xpos[3 * s + 2]);
    if (this.trail.length > 3 * this.trailMax) this.trail.splice(0, this.trail.length - 3 * this.trailMax);
    this.trailLine.geometry.setAttribute("position", new THREE.Float32BufferAttribute(this.trail, 3));
    this.trailLine.visible = true;
  }

  render() {
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  resize() {
    const w = this.container.clientWidth, h = this.container.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  // ------------------------------------------------- rendering a model camera

  /**
   * Render from MuJoCo camera `camId` into an offscreen target.
   * mode "rgb": Uint8ClampedArray RGBA; "depth": Float32Array of metric depth
   * along the optical axis (metres; Infinity where nothing was hit);
   * "seg": Int32Array of geom ids (-1 = background).
   * Image rows are returned top-to-bottom, like an image file.
   */
  renderCamera(camId, { width = 160, height = 120, mode = "rgb" } = {}) {
    const { model, data } = this.sim;
    const ext = Math.max(model.stat.extent, 0.3);
    const near = model.vis.map.znear * ext, far = model.vis.map.zfar * ext;
    const cam = new THREE.PerspectiveCamera(model.cam_fovy[camId], width / height, near, far);
    cam.up.set(0, 1, 0);
    cam.matrixAutoUpdate = false;
    setPose(cam, data.cam_xpos, data.cam_xmat, camId, new THREE.Matrix4());
    cam.updateMatrixWorld(true);

    const overlayVisible = this.overlayGroup.visible;
    this.overlayGroup.visible = false;
    let result;
    if (mode === "rgb") {
      const rt = new THREE.WebGLRenderTarget(width, height);
      this.renderer.setRenderTarget(rt);
      this.renderer.render(this.scene, cam);
      const buf = new Uint8Array(width * height * 4);
      this.renderer.readRenderTargetPixels(rt, 0, 0, width, height, buf);
      result = flipRows(new Uint8ClampedArray(buf.buffer), width, height, 4);
      rt.dispose();
    } else {
      // Depth and segmentation: re-render with flat id-coded or depth-coded materials.
      const saved = this.geomMeshes.map((m) => (m ? m.material : null));
      const bg = this.scene.background;
      // Clear to alpha 0 so pixels that no geom covers can be told apart from hits.
      this.scene.background = null;
      const clear = this.renderer.getClearColor(new THREE.Color()), clearAlpha = this.renderer.getClearAlpha();
      this.renderer.setClearColor(0x000000, 0);
      const mats = [];
      this.geomMeshes.forEach((m, g) => {
        if (!m) return;
        const mat = mode === "seg" ? idMaterial(g + 1) : depthMaterial(near, far);
        mats.push(mat);
        m.material = mat;
      });
      const rt = new THREE.WebGLRenderTarget(width, height, { type: THREE.FloatType });
      this.renderer.setRenderTarget(rt);
      this.renderer.render(this.scene, cam);
      const buf = new Float32Array(width * height * 4);
      this.renderer.readRenderTargetPixels(rt, 0, 0, width, height, buf);
      const flipped = flipRows(buf, width, height, 4);
      if (mode === "seg") {
        result = new Int32Array(width * height);
        for (let i = 0; i < width * height; i++) result[i] = flipped[4 * i + 3] > 0 ? Math.round(flipped[4 * i]) - 1 : -1;
      } else {
        result = new Float32Array(width * height);
        for (let i = 0; i < width * height; i++) result[i] = flipped[4 * i + 3] > 0 ? flipped[4 * i] : Infinity;
      }
      this.geomMeshes.forEach((m, g) => { if (m) m.material = saved[g]; });
      mats.forEach((m) => m.dispose());
      this.scene.background = bg;
      this.renderer.setClearColor(clear, clearAlpha);
      rt.dispose();
    }
    this.renderer.setRenderTarget(null);
    this.overlayGroup.visible = overlayVisible;
    return result;
  }

  // ------------------------------------------------------------ interaction

  _setupInteraction() {
    const el = this.renderer.domElement;
    this.raycaster = new THREE.Raycaster();
    this.drag = null;
    el.addEventListener("pointerdown", (e) => {
      const hit = this.pick(e);
      if (hit && this.onPick) this.onPick(hit);
      const wantDrag = e.ctrlKey || e.metaKey || this.dragMode;
      // body_weldid == 0 means the body is welded to the world: nothing to drag.
      if (!hit || !wantDrag || this.sim.model.body_weldid[hit.body] === 0) return;
      const { data } = this.sim;
      const b = hit.body;
      // Store the grab point in body coordinates so it moves with the body.
      const R = rowMajor3(data.xmat, b), p = new THREE.Vector3(...vec3(data.xpos, b));
      const local = hit.point.clone().sub(p).applyMatrix3(R.clone().transpose());
      const normal = new THREE.Vector3();
      this.camera.getWorldDirection(normal);
      this.drag = { body: b, local, target: hit.point.clone(), plane: new THREE.Plane().setFromNormalAndCoplanarPoint(normal, hit.point), last: null };
      this.controls.enabled = false;
      el.setPointerCapture(e.pointerId);
    });
    el.addEventListener("pointermove", (e) => {
      if (!this.drag) return;
      this._ray(e);
      const p = new THREE.Vector3();
      if (this.raycaster.ray.intersectPlane(this.drag.plane, p)) this.drag.target.copy(p);
    });
    const end = () => {
      if (!this.drag) return;
      const b = this.drag.body;
      this.sim.data.xfrc_applied.fill(0, 6 * b, 6 * b + 6);
      this.drag = null;
      this.controls.enabled = true;
    };
    el.addEventListener("pointerup", end);
    el.addEventListener("pointercancel", end);
  }

  _ray(e) {
    const r = this.renderer.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(ndc, this.camera);
  }

  /** Geom, body and world point under a pointer event, or null. */
  pick(e) {
    this._ray(e);
    const hits = this.raycaster.intersectObjects(this.geomMeshes.filter((m) => m && m.visible), false);
    if (!hits.length) return null;
    const h = hits[0];
    return { geom: h.object.userData.geom, body: h.object.userData.body, point: h.point.clone() };
  }

  /**
   * A spring-damper from the grab point to the cursor, applied through
   * data.xfrc_applied (a world-frame force and torque at the body's centre of
   * mass). Stiffness scales with the mass of the subtree so light and heavy
   * bodies respond alike, the same idea as MuJoCo's own mouse perturbation.
   */
  _applyDrag() {
    if (!this.drag) return;
    const { model, data } = this.sim;
    const b = this.drag.body;
    const R = rowMajor3(data.xmat, b);
    const p = this.drag.local.clone().applyMatrix3(R).add(new THREE.Vector3(...vec3(data.xpos, b)));
    const mass = model.body_subtreemass[b] || 1;
    const k = 60 * mass, c = 2 * Math.sqrt(k * mass); // critically damped for a point mass
    // Grab-point velocity by finite difference between rendered frames.
    const v = new THREE.Vector3();
    const last = this.drag.last;
    if (last && data.time > last.t) v.copy(p).sub(last.p).divideScalar(data.time - last.t);
    this.drag.last = { p: p.clone(), t: data.time };
    const f = this.drag.target.clone().sub(p).multiplyScalar(k).sub(v.multiplyScalar(c));
    const com = new THREE.Vector3(...vec3(data.xipos, b));
    const tau = p.clone().sub(com).cross(f);
    // xfrc_applied rows are [force(3), torque(3)] in world coordinates, applied at the body COM.
    data.xfrc_applied.set([f.x, f.y, f.z, tau.x, tau.y, tau.z], 6 * b);
  }

  dispose() {
    this._resizeObserver.disconnect();
    this.controls.dispose();
    this._clearScene();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}

// --------------------------------------------------------------- helpers

function vec3(arr, i) { return [arr[3 * i], arr[3 * i + 1], arr[3 * i + 2]]; }

function rowMajor3(arr, i) {
  const a = arr.subarray(9 * i, 9 * i + 9);
  return new THREE.Matrix3().set(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8]);
}

/** Copy a MuJoCo position (3) and row-major rotation (9) into an object's matrix. */
function setPose(obj, posArr, matArr, i, m4) {
  const a = matArr.subarray(9 * i, 9 * i + 9);
  m4.set(a[0], a[1], a[2], posArr[3 * i],
         a[3], a[4], a[5], posArr[3 * i + 1],
         a[6], a[7], a[8], posArr[3 * i + 2],
         0, 0, 0, 1);
  obj.matrix.copy(m4);
  obj.matrixWorldNeedsUpdate = true;
  if (obj.isCamera) {
    obj.matrixWorld.copy(m4);
    obj.matrixWorldInverse.copy(m4).invert();
  }
}

function setArrow(arrow, origin, vec, scale) {
  const len = vec.length() * scale;
  if (len < 1e-6) { arrow.visible = false; return; }
  arrow.position.copy(origin);
  arrow.setDirection(vec.clone().normalize());
  arrow.setLength(len, Math.min(0.3 * len, 0.03), Math.min(0.15 * len, 0.015));
}

function flipRows(buf, w, h, ch) {
  const out = new buf.constructor(buf.length);
  const row = w * ch;
  for (let y = 0; y < h; y++) out.set(buf.subarray(y * row, (y + 1) * row), (h - 1 - y) * row);
  return out;
}

function checkerTexture(rgba) {
  const size = 64;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const g = c.getContext("2d");
  const base = new THREE.Color(rgba[0], rgba[1], rgba[2]);
  const dark = base.clone().multiplyScalar(0.92);
  g.fillStyle = `#${base.getHexString()}`; g.fillRect(0, 0, size, size);
  g.fillStyle = `#${dark.getHexString()}`; g.fillRect(0, 0, size / 2, size / 2); g.fillRect(size / 2, size / 2, size / 2, size / 2);
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function idMaterial(id) {
  return new THREE.ShaderMaterial({
    uniforms: { id: { value: id } },
    vertexShader: "void main(){ gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
    fragmentShader: "uniform float id; void main(){ gl_FragColor = vec4(id, 0.0, 0.0, 1.0); }",
    side: THREE.DoubleSide,
  });
}

function depthMaterial(near, far) {
  // Writes view-space depth (distance along the optical axis) in metres; alpha marks a hit.
  return new THREE.ShaderMaterial({
    vertexShader: "varying float vz; void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vz = -mv.z; gl_Position = projectionMatrix * mv; }",
    fragmentShader: "varying float vz; void main(){ gl_FragColor = vec4(vz, 0.0, 0.0, 1.0); }",
    side: THREE.DoubleSide,
  });
}
