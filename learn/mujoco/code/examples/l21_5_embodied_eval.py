"""Lesson 21.5: ground truth for perception, privileged state, and generalization axes (Level 21).

INPUT   PushEnv (Level 12): arm7 pushes a puck to a goal; its "overview" camera (fovy 45 deg) rendered at 320 x 240;
        the pushing controller tuned in Lesson 17.1
PROCESS (1) 6D pose labels: for 20 random puck poses, the puck's pose in the camera frame, converted from MuJoCo's
            camera convention (x right, y up, looking along -z) to OpenCV's (x right, y down, looking along +z);
            checked against the rendered depth and segmentation: the projected top-face centre's pixel must lie in
            the puck's mask, and the rendered depth there must equal the depth, from the label, of the top face along
            that pixel's ray; the same with the conversion forgotten;
        (2) the puck position the controller uses, from the simulator (privileged), or estimated every step from the
            camera (depth of the puck's segmented pixels, back-projected), with the camera's believed pose correct
            or off by a 1 or 2 degree tilt: estimation error and success on 50 tasks;
        (3) generalization axes for the camera-based controller: a 4x heavier puck (object), goals beyond the
            usual region (spatial), half the arm's force cap (embodiment), against nominal
OUTPUT  printed tables

Run:  MUJOCO_GL=egl (or osmesa) python examples/l21_5_embodied_eval.py          (about 6 minutes)
"""
# requires: render

import math
import os

import mujoco
import numpy as np

from mjcourse.envs import PushEnv
from mjcourse.stats import wilson_interval

FAST = os.environ.get("MJC_FAST") == "1"
W, H = 320, 240
TASKS = 8 if FAST else 50
P = {"speed": 0.107, "slow_gain": 2.168, "depth": 0.004, "lateral": 0.011}    # tuned in Lesson 17.1
R_PUCK, HALF, DT, PUCK_HALF_HEIGHT = 0.035, 0.008, 0.05, 0.02
CV = np.diag([1.0, -1.0, -1.0])                              # MuJoCo camera axes -> OpenCV camera axes


def pusher(tcp: np.ndarray, puck: np.ndarray, goal: np.ndarray) -> np.ndarray:
    """Lesson 17.1's controller: get behind the puck on its line to the goal, then push, slowing near the goal."""
    to_goal = goal - puck
    d = np.linalg.norm(to_goal)
    if d < 0.01:
        return np.zeros(2, np.float32)
    u = to_goal / d
    n = np.array([-u[1], u[0]])
    rel = tcp - puck
    along, lateral = rel @ u, rel @ n
    contact = -(R_PUCK + HALF)
    if along > contact + 0.015 or abs(lateral) > P["lateral"]:
        side = n * math.copysign(R_PUCK + HALF + 0.03, lateral if lateral != 0 else 1.0)
        target = puck + side if along > contact else puck - (R_PUCK + HALF + 0.03) * u
        speed = 0.3
    else:
        target = puck - (R_PUCK + HALF - P["depth"]) * u
        speed = min(P["speed"], P["slow_gain"] * d)
    step = target - tcp
    dist = np.linalg.norm(step)
    return np.clip(step / max(dist, 1e-9) * min(speed * DT, dist) / 0.02, -1, 1).astype(np.float32)


class Camera:
    """Renders depth and segmentation from the overview camera; estimates the puck's position in the plane."""

    def __init__(self, env: PushEnv, tilt_deg: float = 0.0):
        self.env, self.renderer = env, mujoco.Renderer(env.model, H, W)
        self.cam = env.model.camera("overview").id
        self.puck_geom = env.model.geom("puck").id
        self.f = 0.5 * H / math.tan(math.radians(env.model.cam_fovy[self.cam]) / 2)
        c, s = math.cos(math.radians(tilt_deg)), math.sin(math.radians(tilt_deg))
        self.believed_error = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])       # about the camera's own x axis

    def frames(self) -> tuple[np.ndarray, np.ndarray]:
        r, d = self.renderer, self.env.data
        r.update_scene(d, camera=self.cam)
        r.enable_depth_rendering()
        depth = r.render().copy()
        r.disable_depth_rendering()
        r.enable_segmentation_rendering()
        seg = r.render().copy()
        r.disable_segmentation_rendering()
        return depth, seg

    def pose(self) -> tuple[np.ndarray, np.ndarray]:
        d = self.env.data
        return d.cam_xpos[self.cam].copy(), d.cam_xmat[self.cam].reshape(3, 3).copy()

    def estimate(self) -> np.ndarray | None:
        """Mean x, y of the back-projected puck pixels, using the believed camera pose."""
        depth, seg = self.frames()
        v, u = np.nonzero((seg[..., 0] == self.puck_geom) & (seg[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM)))
        if len(u) == 0:
            return None
        z = depth[v, u]
        cam = np.c_[(u + 0.5 - W / 2) * z / self.f, -(v + 0.5 - H / 2) * z / self.f, -z]       # MuJoCo camera frame
        pos, rot = self.pose()
        world = pos + cam @ (rot @ self.believed_error).T
        return world[:, :2].mean(axis=0)


def run(task_seed: int, source: str = "privileged", tilt: float = 0.0, options: dict | None = None,
        max_lead: float = 0.02) -> tuple[bool, float]:
    env = PushEnv(action_mode="ee_delta", terminate_on_success=False, max_lead=max_lead)
    obs, _ = env.reset(seed=task_seed, options=options or {})
    camera = Camera(env, tilt) if source == "camera" else None
    errors, done, info = [], False, {}
    while not done:
        puck = obs[17:19]
        if camera is not None:
            seen = camera.estimate()
            if seen is not None:
                errors.append(np.linalg.norm(seen - env.puck_xy()))
                puck = seen
        obs, _, terminated, truncated, info = env.step(pusher(obs[14:16], puck, obs[19:21]))
        done = terminated or truncated
    if camera is not None:
        camera.renderer.close()
    env.close()
    return bool(info["distance"] < env.success_radius), float(np.mean(errors)) if errors else 0.0


def summary(results: list[tuple[bool, float]], with_error: bool) -> str:
    ok = [r[0] for r in results]
    lo, hi = wilson_interval(int(sum(ok)), len(ok))
    text = f"success {np.mean(ok):.2f} [{lo:.2f}, {hi:.2f}]"
    return text + (f", position error {1000 * np.mean([r[1] for r in results]):.1f} mm" if with_error else "")


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}; overview camera rendered at {W} x {H}; {TASKS} tasks per row")
    print("(1) 6D pose labels of the puck in the camera frame, checked against the renders (20 poses)")
    env = PushEnv(action_mode="ee_delta")
    camera = Camera(env)
    rng = np.random.default_rng(0)
    rows = {"OpenCV axes (converted)": [], "MuJoCo axes used as OpenCV (forgotten)": []}
    for k in range(20):
        env.reset(seed=k, options={"puck": rng.uniform([0.42, -0.1], [0.55, 0.1])})
        dof = env.model.jnt_qposadr[env.model.joint("puck").id]
        yaw = rng.uniform(-np.pi, np.pi)
        env.data.qpos[dof + 3:dof + 7] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
        mujoco.mj_forward(env.model, env.data)
        depth, seg = camera.frames()
        pos, rot = camera.pose()
        top = env.data.xpos[env.puck] + env.data.xmat[env.puck].reshape(3, 3) @ [0, 0, PUCK_HALF_HEIGHT]
        t_mj = rot.T @ (top - pos)                                     # top-face centre in MuJoCo camera axes
        for label, t in (("OpenCV axes (converted)", CV @ t_mj), ("MuJoCo axes used as OpenCV (forgotten)", t_mj)):
            if t[2] <= 0:
                rows[label].append((False, float("nan")))
                continue
            u, v = camera.f * t[0] / t[2] + W / 2 - 0.5, camera.f * t[1] / t[2] + H / 2 - 0.5
            ui, vi = int(round(u)), int(round(v))
            inside = 0 <= ui < W and 0 <= vi < H
            hit = inside and seg[vi, ui, 0] == camera.puck_geom and seg[vi, ui, 1] == int(mujoco.mjtObj.mjOBJ_GEOM)
            if hit:                      # the depth along the ray through that pixel's centre, to the top face's plane
                ray = rot @ np.array([(ui + 0.5 - W / 2) / camera.f, -(vi + 0.5 - H / 2) / camera.f, -1.0])
                normal = env.data.xmat[env.puck].reshape(3, 3)[:, 2]
                expected = (top - pos) @ normal / (ray @ normal)
            rows[label].append((bool(hit), abs(depth[vi, ui] - expected) if hit else float("nan")))
    camera.renderer.close()
    for label, r in rows.items():
        hits = [h for h, _ in r]
        errs = [e for h, e in r if h]
        text = f"rendered depth against the label's, largest difference {1e6 * max(errs):.2f} um" if errs else "no projected point lands on the puck"
        print(f"    {label:<40} projected top centre on the puck's mask in {sum(hits)}/20 poses; {text}")
    print(f"(2) where the controller's puck position comes from, {TASKS} tasks")
    tasks = np.random.default_rng(1717).integers(0, 10**6, TASKS)
    for label, kw in (("simulator state (privileged)", {"source": "privileged"}), ("camera, pose known", {"source": "camera"}),
                      ("camera, believed pose off by a 1 deg tilt", {"source": "camera", "tilt": 1.0}),
                      ("camera, believed pose off by a 2 deg tilt", {"source": "camera", "tilt": 2.0})):
        print(f"    {label:<44} " + summary([run(int(t), **kw) for t in tasks], kw["source"] == "camera"))
    print(f"(3) generalization axes for the camera-based controller, {TASKS} tasks")
    goal_rng = np.random.default_rng(5)
    far = [{"goal": goal_rng.uniform([0.68, -0.2], [0.74, 0.2])} for _ in tasks]
    for label, maker in (("nominal", lambda i: {}), ("object: puck 4x heavier (0.8 kg)", lambda i: {"options": {"puck_mass": 0.8}}),
                         ("spatial: goals at x 0.68-0.74 m (usual 0.58-0.66)", lambda i: {"options": far[i]}),
                         ("embodiment: arm force cap halved", lambda i: {"max_lead": 0.01})):
        print(f"    {label:<52} " + summary([run(int(t), source="camera", **maker(i)) for i, t in enumerate(tasks)], True))
