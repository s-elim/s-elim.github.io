"""The point-mass navigation task and its scripted expert (Level 14).

State s = (x, y, vx, vy); action a = (fx, fy) in [-1, 1] N, applied every 10 ms physics step.
The mass starts left of a round obstacle and must stop at the goal on its right: within
4 cm of it, slower than 5 cm/s. An episode lasts at most 6 s.

With `push_rate` > 0, the mass is kicked at random times (a velocity change of `push`
m/s in a random direction, on average `push_rate` times per second): the states that
follow are ones a demonstration without kicks never shows.

The expert goes around the obstacle on the side it is already on: it steers to a waypoint
0.2 m above or below the obstacle's centre until it has passed it, then to the goal, with
a saturated PD law. Its action is therefore discontinuous at y = 0, where the side flips.
"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from mjcourse.paths import model_path

GOAL = np.array([0.35, 0.0])
START_LOW, START_HIGH = np.array([-0.40, -0.25]), np.array([-0.30, 0.25])
MAX_STEPS = 600


def expert(state: np.ndarray) -> np.ndarray:
    p, v = state[:2], state[2:]
    side = 1.0 if p[1] >= 0 else -1.0
    target = np.array([0.0, 0.2 * side]) if p[0] < -0.02 else GOAL
    return np.clip(4.0 * (target - p) - 1.5 * v, -1.0, 1.0)


def sample_starts(rng: np.random.Generator, n: int) -> np.ndarray:
    return rng.uniform(START_LOW, START_HIGH, (n, 2))


@dataclass
class Rollout:
    states: np.ndarray          # (T, 4) states at which actions were chosen
    actions: np.ndarray         # (T, 2) actions taken
    success: bool
    hit_obstacle: bool
    steps: int


class PointMass:
    def __init__(self):
        self.model = mujoco.MjModel.from_xml_path(str(model_path("point_mass")))
        self.data = mujoco.MjData(self.model)
        self.obstacle = self.model.geom("obstacle").id

    def rollout(self, policy, start: np.ndarray, max_steps: int = MAX_STEPS, push_rate: float = 0.0,
                push: float = 0.4, rng: np.random.Generator | None = None) -> Rollout:
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[:] = start
        mujoco.mj_forward(m, d)
        states, actions, hit = [], [], False
        p_push = push_rate * m.opt.timestep
        for t in range(max_steps):
            if p_push > 0 and rng.random() < p_push:
                angle = rng.uniform(0, 2 * np.pi)
                d.qvel[:] += push * np.array([np.cos(angle), np.sin(angle)])
            s = np.r_[d.qpos, d.qvel]
            a = np.clip(np.asarray(policy(s), dtype=float), -1.0, 1.0)
            states.append(s)
            actions.append(a)
            d.ctrl[:] = a
            mujoco.mj_step(m, d)
            hit |= any(self.obstacle in (c.geom1, c.geom2) for c in d.contact[:d.ncon])
            if np.linalg.norm(d.qpos - GOAL) < 0.04 and np.linalg.norm(d.qvel) < 0.05:
                return Rollout(np.array(states), np.array(actions), True, hit, t + 1)
        return Rollout(np.array(states), np.array(actions), False, hit, max_steps)


def evaluate(policy, starts: np.ndarray, push_rate: float = 0.0, seed: int = 0) -> dict:
    """Closed-loop success, obstacle contacts and time on the given starts; with pushes, the
    i-th episode's kicks come from a generator seeded with (seed, i), so policies are compared
    on the same kicks."""
    sim = PointMass()
    runs = [sim.rollout(policy, s, push_rate=push_rate, rng=np.random.default_rng([seed, i])) for i, s in enumerate(starts)]
    return {"success": float(np.mean([r.success for r in runs])), "hit": float(np.mean([r.hit_obstacle for r in runs])),
            "steps": float(np.mean([r.steps for r in runs if r.success])) if any(r.success for r in runs) else float("nan"),
            "runs": runs}
