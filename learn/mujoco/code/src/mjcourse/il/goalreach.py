"""Reaching a goal the policy must see (Level 15).

The point mass of Level 14, with the goal moved to a random place right of the obstacle in
every episode and a camera above the arena. A policy that observes state is given the
goal's coordinates; a policy that observes pixels must find the goal marker in the image.
Optionally a distractor (a blue disc) is drawn; during training it can be placed at a
fixed offset from the goal, which makes it a shortcut a vision policy may learn instead.

Conditions change what the camera sees without changing the task: "nominal", "dim light"
(the scene's lights at a third of their intensity and moved), "camera shifted" (the
camera moved 5 cm and tilted 3 degrees).
The policy acts every 50 ms (5 physics steps); episodes last at most 6 s.
"""

from __future__ import annotations

import math

import mujoco
import numpy as np

from mjcourse.paths import model_path

SKIP, MAX_ACTIONS = 5, 120
GOAL_LOW, GOAL_HIGH = np.array([0.20, -0.30]), np.array([0.40, 0.30])
DISTRACTOR_OFFSET = np.array([0.0, 0.12])          # training-time shortcut: always this far from the goal
CONDITIONS = ("nominal", "dim light", "camera shifted")


def build(condition: str = "nominal") -> mujoco.MjModel:
    spec = mujoco.MjSpec.from_file(str(model_path("point_mass")))
    spec.visual.headlight.diffuse = [0.25, 0.25, 0.25]
    spec.visual.headlight.ambient = [0.15, 0.15, 0.15]
    spec.worldbody.add_light(name="key", pos=[0.3, -0.3, 1.5], dir=[-0.2, 0.2, -1], diffuse=[0.25, 0.25, 0.25])
    spec.worldbody.add_geom(name="distractor", type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[0.035, 0.001, 0],
                            pos=[0.0, 0.4, 0.002], rgba=[0.1, 0.3, 0.9, 1.0], contype=0, conaffinity=0)
    tilt = math.radians(3) if condition == "camera shifted" else 0.0
    shift = 0.05 if condition == "camera shifted" else 0.0
    spec.worldbody.add_camera(name="top", pos=[shift, shift, 1.25], quat=[math.cos(tilt / 2), math.sin(tilt / 2), 0, 0], fovy=45)
    model = spec.compile()
    if condition == "dim light":
        model.light_diffuse[:] *= 0.33
        model.light_pos[:, :2] *= -1.0
    goal = model.site("goal").id
    model.site_rgba[goal] = [0.1, 0.75, 0.3, 1.0]                  # opaque, so it is easy to see
    model.site_size[goal][0] = 0.035
    return model


def expert(state: np.ndarray, goal: np.ndarray) -> np.ndarray:
    p, v = state[:2], state[2:4]
    side = 1.0 if p[1] >= 0 else -1.0
    target = np.array([0.0, 0.2 * side]) if p[0] < -0.02 else goal
    return np.clip(4.0 * (target - p) - 1.5 * v, -1.0, 1.0)


class GoalReach:
    def __init__(self, condition: str = "nominal", size: int = 64):
        self.model = build(condition)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, size, size)
        self.renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = False     # shadows cost most of a small frame
        self.goal_site, self.distractor = self.model.site("goal").id, self.model.geom("distractor").id

    def reset(self, start: np.ndarray, goal: np.ndarray, distractor: np.ndarray | None) -> None:
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[:] = start
        m.site_pos[self.goal_site][:2] = goal
        m.geom_pos[self.distractor][:2] = distractor if distractor is not None else [0.0, 0.6]   # off camera
        mujoco.mj_forward(m, d)
        self.goal = np.asarray(goal, float)

    def state(self) -> np.ndarray:
        return np.r_[self.data.qpos, self.data.qvel]

    def image(self, depth: bool = False) -> np.ndarray:
        """(H, W, 3) uint8 RGB, or (H, W, 4) float32 RGB in [0, 1] plus depth in metres."""
        r = self.renderer
        r.update_scene(self.data, "top")
        rgb = r.render().copy()
        if not depth:
            return rgb
        r.enable_depth_rendering()
        r.update_scene(self.data, "top")
        z = r.render().copy()
        r.disable_depth_rendering()
        return np.concatenate([rgb / 255.0, z[..., None]], axis=-1).astype(np.float32)

    def step(self, action: np.ndarray) -> bool:
        d = self.data
        d.ctrl[:] = np.clip(action, -1, 1)
        for _ in range(SKIP):
            mujoco.mj_step(self.model, d)
        return bool(np.linalg.norm(d.qpos - self.goal) < 0.04 and np.linalg.norm(d.qvel) < 0.05)

    def close(self) -> None:
        self.renderer.close()


def sample_task(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    start = rng.uniform([-0.40, -0.25], [-0.30, 0.25])
    goal = rng.uniform(GOAL_LOW, GOAL_HIGH)
    return start, goal


def distractor_position(goal: np.ndarray, shortcut: bool, rng: np.random.Generator) -> np.ndarray:
    """At a fixed offset from the goal (the shortcut) or anywhere right of the obstacle."""
    if shortcut:
        return goal + DISTRACTOR_OFFSET * (1 if goal[1] < 0.15 else -1)
    return rng.uniform(GOAL_LOW, GOAL_HIGH)
