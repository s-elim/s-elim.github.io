from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np
from mujoco import rollout as mj_rollout

from mjcourse import tabletop as tt


@dataclass
class PlannerConfig:
    horizon: int = 12
    samples: int = 64
    elites: int = 16
    iterations: int = 3
    init_std: float = 0.6
    seed: int = 0


def cost(states: np.ndarray, task: tuple[str, str], actions: np.ndarray) -> np.ndarray:
    i = 4 + 4 * tt.OBJECTS.index(task[0])
    puck = states[:, 1:, i:i + 2]
    to_zone_vec = tt.ZONES[task[1]] - puck
    to_zone = np.linalg.norm(to_zone_vec, axis=-1)
    behind = puck - to_zone_vec / (to_zone[..., None] + 1e-6) * (tt.PUCK_RADIUS + tt.PUSHER_RADIUS + 0.005)
    to_behind = np.linalg.norm(states[:, 1:, 0:2] - behind, axis=-1)
    weights = np.linspace(0.5, 1.5, to_zone.shape[1])
    return (weights * (to_zone + 0.5 * to_behind)).mean(1) + 0.01 * (actions ** 2).sum((1, 2))


class MujocoModel:
    def __init__(self, scene: tt.Tabletop, threads: int = 1, plan_scene: tt.Tabletop | None = None):
        self.scene = scene
        self.plan_model = (plan_scene or scene).model
        self.datas = [mujoco.MjData(self.plan_model) for _ in range(threads)]
        self.spec = mujoco.mjtState.mjSTATE_FULLPHYSICS
        self.nq, self.nv = scene.model.nq, scene.model.nv
        self.qadr = [scene.model.jnt_qposadr[scene.model.joint(f"{o}_puck").id] for o in tt.OBJECTS]
        self.vadr = [scene.model.jnt_dofadr[scene.model.joint(f"{o}_puck").id] for o in tt.OBJECTS]

    def planar(self, full: np.ndarray) -> np.ndarray:
        q, v = full[..., 1:1 + self.nq], full[..., 1 + self.nq:1 + self.nq + self.nv]
        parts = [q[..., 0:2], v[..., 0:2]]
        for a, b in zip(self.qadr, self.vadr):
            parts += [q[..., a:a + 2], v[..., b:b + 2]]
        return np.concatenate(parts, -1)

    def predict(self, state: np.ndarray, actions: np.ndarray) -> np.ndarray:
        m, d = self.scene.model, self.scene.data
        x0 = np.zeros(mujoco.mj_stateSize(m, self.spec))
        mujoco.mj_getState(m, d, x0, self.spec)
        k = actions.shape[0]
        skip = self.scene.frame_skip
        control = np.repeat(actions * self.scene.variation.max_speed, skip, axis=1)
        full, _ = mj_rollout.rollout(self.plan_model, self.datas, np.tile(x0, (k, 1)), control)
        planar = self.planar(full[:, skip - 1::skip])
        return np.concatenate([np.repeat(state[None, None], k, 0), planar], 1)


class LearnedModel:
    def __init__(self, dynamics):
        self.dynamics = dynamics

    def predict(self, state: np.ndarray, actions: np.ndarray) -> np.ndarray:
        return self.dynamics.rollout(np.repeat(state[None], len(actions), 0), actions)


class Planner:
    def __init__(self, model, task: tuple[str, str], cfg: PlannerConfig | None = None):
        self.model, self.task, self.cfg = model, task, cfg or PlannerConfig()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.mean = np.zeros((self.cfg.horizon, 2))
        self.last: dict = {}

    def act(self, state: np.ndarray) -> np.ndarray:
        return self.plan(state)[0]

    def plan(self, state: np.ndarray, execute: int = 1) -> np.ndarray:
        cfg = self.cfg
        mean, std = self.mean, np.full_like(self.mean, cfg.init_std)
        for _ in range(cfg.iterations):
            actions = np.clip(mean + std * self.rng.standard_normal((cfg.samples, *mean.shape)), -1, 1)
            actions[0] = np.clip(mean, -1, 1)
            states = self.model.predict(state, actions)
            costs = cost(states, self.task, actions)
            elite = actions[np.argsort(costs)[:cfg.elites]]
            mean, std = elite.mean(0), elite.std(0) + 0.05
        best = int(np.argmin(costs))
        self.last = {"actions": actions, "states": states, "costs": costs, "best": best}
        self.mean = np.concatenate([actions[best][execute:], np.repeat(actions[best][-1:], execute, 0)])
        return actions[best]


def run_episode(planner_model_factory, task, layout, variation: tt.Variation | None = None, cfg: PlannerConfig | None = None,
                steps: int = tt.EPISODE_STEPS, record: bool = False, execute: int = 1) -> dict:
    scene = tt.Tabletop(variation)
    scene.reset(layout)
    planner = Planner(planner_model_factory(scene), task, cfg)
    states, predicted_cost, queue = [scene.state()], [], []
    for _ in range(steps):
        if not queue:
            queue = list(planner.plan(states[-1], execute)[:execute])
            if record:
                predicted_cost.append(float(planner.last["costs"][planner.last["best"]]))
        scene.step(queue.pop(0))
        states.append(scene.state())
        if scene.success(task) and np.linalg.norm(states[-1][4 + 4 * tt.OBJECTS.index(task[0]) + 2:][:2]) < 0.02:
            break
    out = {"success": scene.success(task), "steps": len(states) - 1, "states": np.array(states)}
    if record:
        out["predicted_cost"] = predicted_cost
    scene.close()
    return out
