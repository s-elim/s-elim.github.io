"""Lesson 11.3: a pick-and-place dataset with images, and a validator that can fail it.

INPUT   the scripted pick-and-place of Lesson 10.2 (imported from l10_2_pick_place.py), the
        front and wrist cameras of pick_place.xml
PROCESS (1) generate episodes: the red cube at a seeded random pose, 5 Hz frames of RGB,
            depth and body-level labels from two cameras with each camera's pose, the state,
            the action (joint targets and gripper command) and every object's pose, plus the
            torque command of every physics step; one compressed .npz per episode and a
            metadata.json describing the schema, seeds, versions and model hash;
        (2) validate the dataset: schema and dtypes, value ranges, reprojection of cube
            centres into their masks, a physics replay of the stored torques that must
            reproduce every stored state bit for bit, and regeneration from the seed;
        (3) corrupt a copy in three ways and run the validator on it;
        (4) a figure of one frame from both cameras (runs/l11_3/frame.png)
OUTPUT  a dataset directory, printed reports and the figure

Run:  MUJOCO_GL=egl python examples/l11_3_dataset.py [--episodes 50] [--out DIR]
"""
# requires: render

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import l10_2_pick_place as pp  # noqa: E402  (the pipeline of Lesson 10.2)

from mjcourse import model_path  # noqa: E402

SEED, FPS, WIDTH, HEIGHT = 11, 5, 160, 120
FIGURE = Path(__file__).resolve().parents[1] / "runs" / "l11_3" / "frame.png"
OKABE_ITO = ["#000000", "#999999", "#56B4E9", "#D55E00", "#009E73", "#0072B2", "#E69F00"]   # one colour per label
CAMERAS = ("front", "gripper/wrist")
LABELS = {"background": 0, "floor": 1, "robot": 2, "red_cube": 3, "green_cube": 4, "blue_cube": 5, "tray": 6}
SCHEMA_VERSION = "1.0"


def label_table(model: mujoco.MjModel) -> np.ndarray:
    """Geom id -> label (uint8), through each geom's body."""
    table = np.zeros(model.ngeom, np.uint8)
    for g in range(model.ngeom):
        body = model.body(model.geom_bodyid[g]).name
        if body in LABELS:
            table[g] = LABELS[body]
        elif model.geom(g).name == "floor":
            table[g] = LABELS["floor"]
        else:
            table[g] = LABELS["robot"]          # every other body in this scene belongs to the arm or gripper
    return table


def intrinsics(model: mujoco.MjModel, camera: str) -> np.ndarray:
    f = 0.5 * HEIGHT / math.tan(math.radians(model.cam_fovy[model.camera(camera).id]) / 2)
    return np.array([[f, 0, WIDTH / 2], [0, f, HEIGHT / 2], [0, 0, 1]])


class RecordingEpisode(pp.Episode):
    """Lesson 10.2's Episode, recording frames at FPS and the torque command of every step."""

    def __init__(self, cube_xy: np.ndarray, yaw: float):
        super().__init__(cube_xy, yaw)
        m = self.model
        self.renderer = mujoco.Renderer(m, HEIGHT, WIDTH)
        self.option = mujoco.MjvOption()
        self.option.sitegroup[:] = 0                                   # sites are not objects (Lesson 11.2)
        self.labels = label_table(m)
        self.every = round(1.0 / (FPS * m.opt.timestep))
        self.steps = 0
        spec = mujoco.mjtState.mjSTATE_INTEGRATION                     # qpos, qvel, act, ctrl, warmstart, time, ...
        self.initial_state = np.zeros(mujoco.mj_stateSize(m, spec))
        mujoco.mj_getState(m, self.data, self.initial_state, spec)
        self.physics_ctrl: list[np.ndarray] = []
        self.frames: dict[str, list] = {}
        self.record()

    def step(self, n: int = 1) -> None:
        for _ in range(n):
            super().step(1)
            self.physics_ctrl.append(self.data.ctrl.copy())
            self.steps += 1
            if self.steps % self.every == 0:
                self.record()

    def add(self, key: str, value) -> None:
        self.frames.setdefault(key, []).append(np.asarray(value).copy())

    def record(self) -> None:
        m, d = self.model, self.data
        self.add("time", d.time)
        self.add("step", self.steps)
        self.add("qpos", d.qpos)
        self.add("qvel", d.qvel)
        state = np.zeros(mujoco.mj_stateSize(m, mujoco.mjtState.mjSTATE_INTEGRATION))
        mujoco.mj_getState(m, d, state, mujoco.mjtState.mjSTATE_INTEGRATION)
        self.add("state", state)
        self.add("action", np.r_[self.target, d.ctrl[7]])               # joint targets (7) + gripper command
        self.add("object_pose", np.stack([np.r_[d.xpos[b], d.xquat[b]] for b in
                                          (m.body("red_cube").id, m.body("green_cube").id, m.body("blue_cube").id)]))
        for cam in CAMERAS:
            key = cam.split("/")[-1]
            c = m.camera(cam).id
            self.add(f"{key}/cam_pos", d.cam_xpos[c])
            self.add(f"{key}/cam_mat", d.cam_xmat[c])
            r = self.renderer
            r.disable_depth_rendering()
            r.disable_segmentation_rendering()
            r.update_scene(d, cam, scene_option=self.option)
            self.add(f"{key}/rgb", r.render())
            r.enable_depth_rendering()
            r.update_scene(d, cam, scene_option=self.option)
            self.add(f"{key}/depth", r.render())
            r.disable_depth_rendering()
            r.enable_segmentation_rendering()
            r.update_scene(d, cam, scene_option=self.option)
            seg = r.render()
            labels = np.zeros(seg.shape[:2], np.uint8)
            hit = (seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM) & (seg[..., 0] >= 0)
            labels[hit] = self.labels[seg[..., 0][hit]]
            self.add(f"{key}/labels", labels)


def model_hash() -> str:
    """sha256 of the compiled model, saved as MJB: changes whenever anything in the model does."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "m.mjb")
        mujoco.mj_saveModel(mujoco.MjModel.from_xml_path(str(model_path("pick_place"))), path, None)
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def episode_state(seed: int, index: int) -> tuple[np.ndarray, float]:
    rng = np.random.default_rng([seed, index])
    return np.array([rng.uniform(0.40, 0.60), rng.uniform(-0.20, 0.00)]), float(rng.uniform(-math.pi / 4, math.pi / 4))


def generate_episode(seed: int, index: int) -> dict[str, np.ndarray]:
    cube_xy, yaw = episode_state(seed, index)
    ep = RecordingEpisode(cube_xy, yaw)
    outcome, attempts, tipped = pp.run_episode(cube_xy, yaw, episode=ep)
    ep.renderer.close()
    arrays = {k: np.stack(v) for k, v in ep.frames.items()}
    arrays["initial_state"] = ep.initial_state
    arrays["physics_ctrl"] = np.stack(ep.physics_ctrl)
    arrays["outcome"] = np.array(outcome)
    arrays["cube_init"] = np.r_[cube_xy, yaw]
    return arrays


def write_dataset(out: Path, episodes: int, seed: int = SEED) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path(str(model_path("pick_place")))
    meta = {
        "schema_version": SCHEMA_VERSION, "mujoco_version": mujoco.__version__, "model": "pick_place.xml",
        "model_sha256": model_hash(), "seed": seed, "episode_seeds": "numpy.random.default_rng([seed, index])",
        "episodes": episodes, "fps": FPS, "timestep": model.opt.timestep, "image_size": [WIDTH, HEIGHT],
        "cameras": {cam.split("/")[-1]: {"name": cam, "K": intrinsics(model, cam).tolist(),
                                         "convention": "pixel centres at index + 0.5; cam_mat is MuJoCo's cam_xmat (camera looks along -z, y up)"}
                    for cam in CAMERAS},
        "labels": LABELS, "depth": "float32 metres along the optical axis; sites hidden in RGB, depth and labels",
        "arrays": {"time": "(T,) s", "step": "(T,) physics step index", "qpos": "(T, nq)", "qvel": "(T, nv)",
                   "state": "(T, mj_stateSize) mj_getState(mjSTATE_INTEGRATION) at each frame",
                   "action": "(T, 8) joint targets (rad) and gripper half-opening command (m), as held at that frame",
                   "object_pose": "(T, 3, 7) red, green, blue cube: position (m) and quaternion (w, x, y, z)",
                   "<camera>/rgb": "(T, H, W, 3) uint8", "<camera>/depth": "(T, H, W) float32 m",
                   "<camera>/labels": "(T, H, W) uint8", "<camera>/cam_pos": "(T, 3)", "<camera>/cam_mat": "(T, 9)",
                   "physics_ctrl": "(steps, nu) torque and gripper command applied at every physics step",
                   "initial_state": "mj_getState(mjSTATE_INTEGRATION) before the first step",
                   "outcome": "scripted pipeline's outcome", "cube_init": "(x, y, yaw)"},
        "generator": "examples/l11_3_dataset.py",
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=1))
    for i in range(episodes):
        np.savez_compressed(out / f"episode_{i:04d}.npz", **generate_episode(seed, i))
    return meta


# ---------------------------------------------------------------- validation

def project(k: np.ndarray, cam_pos: np.ndarray, cam_mat: np.ndarray, p: np.ndarray) -> tuple[np.ndarray, float]:
    r_wc = cam_mat.reshape(3, 3) @ np.diag([1.0, -1.0, -1.0])
    pc = r_wc.T @ (p - cam_pos)
    return (k @ (pc / pc[2]))[:2], pc[2]


def floor_height(k, cam_pos, cam_mat, depth, labels) -> np.ndarray:
    """Heights of the floor pixels' back-projected points: zero if depth, K and pose agree."""
    vs, us = np.nonzero(labels == LABELS["floor"])
    z = depth[vs, us]
    p_cv = np.c_[(us + 0.5 - k[0, 2]) * z / k[0, 0], (vs + 0.5 - k[1, 2]) * z / k[1, 1], z]
    r_wc = cam_mat.reshape(3, 3) @ np.diag([1.0, -1.0, -1.0])
    return (p_cv @ r_wc.T + cam_pos)[:, 2]


def validate(root: Path, regenerate: int | None = 0) -> list[tuple[str, bool, str]]:
    """Run every check; returns (check, passed, detail) rows."""
    meta = json.loads((root / "metadata.json").read_text())
    files = sorted(root.glob("episode_*.npz"))
    model = mujoco.MjModel.from_xml_path(str(model_path("pick_place")))
    w, h = meta["image_size"]
    fail: dict[str, list[str]] = {k: [] for k in ("schema", "ranges", "floor", "replay", "resume")}
    reproj, inside, floor_err, replay_frames, resume_frames = [], [], [], 0, 0
    for path in files:
        z = np.load(path)
        t = len(z["time"])
        n_state = mujoco.mj_stateSize(model, mujoco.mjtState.mjSTATE_INTEGRATION)
        expected = {"qpos": ((t, model.nq), np.float64), "qvel": ((t, model.nv), np.float64), "action": ((t, 8), np.float64),
                    "state": ((t, n_state), np.float64),
                    "object_pose": ((t, 3, 7), np.float64)}
        for cam in meta["cameras"]:
            expected |= {f"{cam}/rgb": ((t, h, w, 3), np.uint8), f"{cam}/depth": ((t, h, w), np.float32),
                         f"{cam}/labels": ((t, h, w), np.uint8), f"{cam}/cam_pos": ((t, 3), np.float64), f"{cam}/cam_mat": ((t, 9), np.float64)}
        for key, (shape, dtype) in expected.items():
            if key not in z.files or z[key].shape != shape or z[key].dtype != dtype:
                fail["schema"].append(f"{path.name}:{key}")
        if not np.allclose(np.diff(z["time"]), 1.0 / meta["fps"], atol=1e-9):
            fail["ranges"].append(f"{path.name}: frame interval {np.diff(z['time']).max():.2f} s")
        if not np.allclose(np.linalg.norm(z["object_pose"][..., 3:], axis=-1), 1.0, atol=1e-9):
            fail["ranges"].append(f"{path.name}: quaternion norm")
        for cam, spec in meta["cameras"].items():
            depth, labels, k = z[f"{cam}/depth"], z[f"{cam}/labels"], np.array(spec["K"])
            if not (np.isfinite(depth).all() and depth.min() > 0) or labels.max() > max(meta["labels"].values()):
                fail["ranges"].append(f"{path.name}:{cam} depth or labels")
            for f in range(0, t, 5):                                  # every fifth frame is enough to catch a fault
                heights = np.abs(floor_height(k, z[f"{cam}/cam_pos"][f], z[f"{cam}/cam_mat"][f], depth[f], labels[f]))
                if len(heights):
                    floor_err.append(np.median(heights))
                    if np.median(heights) > 0.001:
                        fail["floor"].append(f"{path.name}:{cam} frame {f}: {1000 * np.median(heights):.0f} mm")
        k = np.array(meta["cameras"]["front"]["K"])
        for f in range(t):                                            # cube centres against their front masks
            for j, name in enumerate(("red_cube", "green_cube", "blue_cube")):
                vs, us = np.nonzero(z["front/labels"][f] == meta["labels"][name])
                if len(us) < 20 or us.min() == 0 or vs.min() == 0 or us.max() == w - 1 or vs.max() == h - 1:
                    continue
                uv, _ = project(k, z["front/cam_pos"][f], z["front/cam_mat"][f], z["object_pose"][f, j, :3])
                reproj.append(np.hypot(uv[0] - us.mean() - 0.5, uv[1] - vs.mean() - 0.5))
        kw = np.array(meta["cameras"]["wrist"]["K"])
        for f in range(t):                                            # the red cube's centre lands on its wrist mask
            uv, depth_c = project(kw, z["wrist/cam_pos"][f], z["wrist/cam_mat"][f], z["object_pose"][f, 0, :3])
            u, v = int(uv[0]), int(uv[1])
            if depth_c > 0 and 0 <= u < w and 0 <= v < h:
                inside.append(z["wrist/labels"][f, v, u] == meta["labels"]["red_cube"])
        data = mujoco.MjData(model)                                   # replay the stored torques
        mujoco.mj_setState(model, data, z["initial_state"], mujoco.mjtState.mjSTATE_INTEGRATION)
        frame_at = {int(s): i for i, s in enumerate(z["step"])}
        if 0 in frame_at and not np.array_equal(data.qpos, z["qpos"][frame_at[0]]):
            fail["replay"].append(f"{path.name}: initial state")
        for s, ctrl in enumerate(z["physics_ctrl"], start=1):
            data.ctrl[:] = ctrl
            mujoco.mj_step(model, data)
            if s in frame_at:
                replay_frames += 1
                if not (np.array_equal(data.qpos, z["qpos"][frame_at[s]]) and np.array_equal(data.qvel, z["qvel"][frame_at[s]])):
                    fail["replay"].append(f"{path.name}: step {s}")
        mid = t // 2                                                   # resuming from a stored frame is exact too
        same, _ = resume(model, z, mid, full_state=True)
        resume_frames += t - mid - 1
        if same != t - mid - 1:
            fail["resume"].append(f"{path.name}: {same}/{t - mid - 1}")
    reproj = np.array(reproj)
    rows = [("episode count matches metadata", len(files) == meta["episodes"], f"{len(files)} files, {meta['episodes']} declared"),
            ("model and MuJoCo version match", model_hash() == meta["model_sha256"] and mujoco.__version__ == meta["mujoco_version"],
             f"{meta['model_sha256'][:12]}, {meta['mujoco_version']}"),
            ("schema: keys, shapes, dtypes", not fail["schema"], "; ".join(fail["schema"][:3]) or "all arrays"),
            ("ranges: frame timing, quaternions, depth, labels", not fail["ranges"], "; ".join(fail["ranges"][:3]) or "all in range"),
            ("floor pixels back-project to z = 0 (median < 1 mm)", not fail["floor"],
             ", ".join(f"{sum(f':{cam} ' in n for n in fail['floor'])} {cam} frames fail" for cam in meta["cameras"]) if fail["floor"]
             else f"{len(floor_err)} frame-cameras, worst median {1000 * max(floor_err):.3f} mm"),
            ("front: cube centres within 2 px of mask centroids", bool(len(reproj)) and reproj.max() < 2.0,
             f"{len(reproj)} cube-frames, mean {reproj.mean():.2f} px, max {reproj.max():.2f} px" if len(reproj) else "no complete masks"),
            ("wrist: red cube centre lands on its mask (> 90%)", bool(inside) and np.mean(inside) > 0.9,
             f"{np.mean(inside):.1%} of {len(inside)} frames with the cube in view" if inside else "never in view"),
            ("physics replay reproduces states bit for bit", not fail["replay"] and replay_frames > 0,
             "; ".join(fail["replay"][:2]) or f"{replay_frames} frames identical"),
            ("resuming at each episode's middle frame is exact", not fail["resume"] and resume_frames > 0,
             "; ".join(fail["resume"][:2]) or f"{resume_frames} later frames identical")]
    if regenerate is not None:
        fresh = generate_episode(meta["seed"], regenerate)
        stored = np.load(files[regenerate])
        differing = [k for k in stored.files if not np.array_equal(stored[k], fresh[k])]
        rows.append((f"episode {regenerate} regenerated from its seed is identical", not differing,
                     f"{len(stored.files)} arrays compared" + (f"; differ: {differing[:4]}" if differing else "")))
    return rows


def resume(model, z, frame: int, full_state: bool) -> tuple[int, float]:
    """Restart at a stored frame and step to the end with the stored commands; returns the
    number of later frames reproduced exactly and the largest qpos difference."""
    data = mujoco.MjData(model)
    if full_state:
        mujoco.mj_setState(model, data, z["state"][frame], mujoco.mjtState.mjSTATE_INTEGRATION)
    else:
        start = int(z["step"][frame])
        data.qpos[:], data.qvel[:], data.time = z["qpos"][frame], z["qvel"][frame], float(z["time"][frame])
        data.ctrl[:] = z["physics_ctrl"][start - 1] if start > 0 else 0.0
    frame_at = {int(s): i for i, s in enumerate(z["step"])}
    same, worst = 0, 0.0
    for s in range(int(z["step"][frame]) + 1, len(z["physics_ctrl"]) + 1):
        data.ctrl[:] = z["physics_ctrl"][s - 1]
        mujoco.mj_step(model, data)
        if s in frame_at:
            i = frame_at[s]
            same += bool(np.array_equal(data.qpos, z["qpos"][i]) and np.array_equal(data.qvel, z["qvel"][i]))
            worst = max(worst, float(np.abs(data.qpos - z["qpos"][i]).max()))
    return same, worst


def show(rows) -> None:
    for name, ok, detail in rows:
        print(f"  [{'pass' if ok else 'FAIL'}] {name:<54} {detail}")


def corrupt(src: Path, dst: Path) -> None:
    """Three realistic faults: a dropped frame, depth in millimetres, and a stale camera pose."""
    shutil.copytree(src, dst)
    files = sorted(dst.glob("episode_*.npz"))
    z = dict(np.load(files[0]))
    for key in list(z):
        if key in ("time", "step", "qpos", "qvel", "state", "action", "object_pose") or "/" in key:
            z[key] = np.delete(z[key], 3, axis=0)                     # frame 3 lost by a writer
    np.savez_compressed(files[0], **z)
    z = dict(np.load(files[1]))
    z["front/depth"] = (z["front/depth"] * 1000).astype(np.float32)   # one episode written in mm
    z["wrist/cam_pos"] = np.repeat(z["wrist/cam_pos"][:1], len(z["wrist/cam_pos"]), axis=0)   # pose not updated
    z["wrist/cam_mat"] = np.repeat(z["wrist/cam_mat"][:1], len(z["wrist/cam_mat"]), axis=0)
    np.savez_compressed(files[1], **z)


def figure(root: Path, out: Path) -> int:
    """RGB, depth and labels from both cameras at the frame where the red cube is highest."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    z = np.load(sorted(root.glob("episode_*.npz"))[0])
    f = int(np.argmax(z["object_pose"][:, 0, 2]))
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.4), constrained_layout=True)
    for row, cam in enumerate(("front", "wrist")):
        axes[row, 0].imshow(z[f"{cam}/rgb"][f])
        depth = np.ma.masked_where(z[f"{cam}/labels"][f] == LABELS["background"], z[f"{cam}/depth"][f])
        im = axes[row, 1].imshow(depth, cmap="viridis")
        fig.colorbar(im, ax=axes[row, 1], fraction=0.046, label="depth (m)")
        axes[row, 2].imshow(z[f"{cam}/labels"][f], cmap=ListedColormap(OKABE_ITO), vmin=-0.5, vmax=len(LABELS) - 0.5, interpolation="nearest")
        axes[row, 0].set_ylabel(cam)
    for col, title in enumerate(("RGB", "depth along the optical axis", "labels")):
        axes[0, col].set_title(title)
    for ax in axes.ravel():
        ax.set_xticks([])
        ax.set_yticks([])
    handles = [plt.Rectangle((0, 0), 1, 1, color=OKABE_ITO[v]) for v in LABELS.values()]
    fig.legend(handles, list(LABELS), loc="lower center", ncol=len(LABELS), frameon=False, bbox_to_anchor=(0.5, -0.06))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=2 if os.environ.get("MJC_FAST") == "1" else 6)
    ap.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "mjcourse_l11_3")
    args = ap.parse_args()
    shutil.rmtree(args.out, ignore_errors=True)
    print(f"MuJoCo {mujoco.__version__}; {args.episodes} episodes, seed {SEED}, {FPS} Hz, {WIDTH} x {HEIGHT}, cameras {CAMERAS}")
    print("(1) generate")
    start = time.perf_counter()
    write_dataset(args.out, args.episodes)
    elapsed = time.perf_counter() - start
    sizes = [p.stat().st_size for p in sorted(args.out.glob("episode_*.npz"))]
    first = np.load(sorted(args.out.glob("episode_*.npz"))[0])
    raw = sum(first[k].nbytes for k in first.files)
    outcomes = [str(np.load(p)["outcome"]) for p in sorted(args.out.glob("episode_*.npz"))]
    print(f"  {elapsed:.1f} s for {args.episodes} episodes ({elapsed / args.episodes:.1f} s each); outcomes: {outcomes}")
    print(f"  episode 0: {len(first['time'])} frames, {len(first['physics_ctrl'])} physics steps; "
          f"{raw / 1e6:.1f} MB in memory, {sizes[0] / 1e6:.1f} MB compressed; all episodes {sum(sizes) / 1e6:.1f} MB")
    for key in ("front/rgb", "front/depth", "front/labels", "wrist/rgb", "physics_ctrl"):
        print(f"    {key:<14} {str(first[key].shape):<22} {first[key].dtype}")
    print("(2) validate")
    show(validate(args.out))
    ep0 = np.load(sorted(args.out.glob("episode_*.npz"))[0])
    mid = len(ep0["time"]) // 2
    same, worst = resume(mujoco.MjModel.from_xml_path(str(model_path("pick_place"))), ep0, mid, full_state=False)
    print(f"  for comparison, resuming episode 0 at frame {mid} from qpos and qvel alone: {same} of "
          f"{len(ep0['time']) - mid - 1} later frames identical, largest qpos difference {worst:.1e}")
    print("(3) a corrupted copy: frame 3 dropped in episode 0; episode 1 with front depth in mm and a frozen wrist pose")
    bad = args.out.with_name(args.out.name + "_corrupted")
    shutil.rmtree(bad, ignore_errors=True)
    corrupt(args.out, bad)
    show(validate(bad, regenerate=None))
    frame = figure(args.out, FIGURE)
    print(f"(4) figure of episode 0, frame {frame} (time {frame / FPS:.1f} s): {FIGURE.relative_to(FIGURE.parents[2])}")
