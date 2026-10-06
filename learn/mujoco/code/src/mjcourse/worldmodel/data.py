from __future__ import annotations

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from mjcourse import tabletop as tt


def collect_episode(seed: int, index: int, steps: int = tt.EPISODE_STEPS, noise: float = 0.3, random_share: float = 0.2,
                    variation: tt.Variation | None = None, render: bool = False) -> dict:
    rng = np.random.default_rng([seed, index])
    task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
    scene = tt.Tabletop(variation)
    scene.reset(tt.sample_layout(rng, task))
    states, actions = [scene.state()], []
    images = [scene.render("top", 64)] if render else None
    for _ in range(steps):
        if rng.random() < random_share:
            a = rng.uniform(-1, 1, 2)
        else:
            a = np.clip(tt.expert(states[-1], task) + rng.normal(0, noise, 2), -1, 1)
        scene.step(a)
        actions.append(a)
        states.append(scene.state())
        if render:
            images.append(scene.render("top", 64))
    scene.close()
    out = {"states": np.array(states, np.float32), "actions": np.array(actions, np.float32), "task": task}
    if render:
        out["images"] = np.array(images)
    return out


def collect(seed: int, episodes: int, workers: int | None = None, **kwargs) -> list[dict]:
    workers = workers or min(32, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        return list(pool.map(_collect, [(seed, i, kwargs) for i in range(episodes)], chunksize=4))


def _collect(args):
    seed, index, kwargs = args
    return collect_episode(seed, index, **kwargs)


def transitions(episodes: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s = np.concatenate([e["states"][:-1] for e in episodes])
    a = np.concatenate([e["actions"] for e in episodes])
    s2 = np.concatenate([e["states"][1:] for e in episodes])
    return s, a, s2


def contact_share(episodes: list[dict], radius: float = tt.PUCK_RADIUS + tt.PUSHER_RADIUS + 0.003) -> float:
    s = np.concatenate([e["states"][:-1] for e in episodes])
    d = np.stack([np.linalg.norm(s[:, 4 + 4 * i:6 + 4 * i] - s[:, :2], axis=1) for i in range(3)], 1)
    return float(np.mean(d.min(1) < radius))
