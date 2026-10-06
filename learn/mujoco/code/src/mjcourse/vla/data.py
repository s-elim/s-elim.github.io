from __future__ import annotations

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from mjcourse import tabletop as tt
from mjcourse.vla import language


def episode(seed: int, index: int, split: str = "train", variation: tt.Variation | None = None, camera: str = "top"):
    rng = np.random.default_rng([seed, index])
    text, task = language.instructions(split)[rng.integers(len(language.instructions(split)))]
    scene = tt.Tabletop(variation)
    scene.reset(tt.sample_layout(rng, task))
    images, states, actions, pucks = [], [], [], []
    for _ in range(tt.EPISODE_STEPS):
        s = scene.state()
        a = tt.expert(s, task)
        images.append(scene.render(camera, 64))
        states.append(s[:4])
        pucks.append(np.r_[s[4:6], s[8:10], s[12:14]])
        actions.append(a)
        scene.step(a)
        if scene.success(task) and np.linalg.norm(scene.state()[4 + 4 * tt.OBJECTS.index(task[0]) + 2:][:2]) < 0.02:
            break
    ok = scene.success(task)
    scene.close()
    return {"text": text, "task": task, "images": np.array(images), "states": np.array(states, np.float32),
            "actions": np.array(actions, np.float32), "pucks": np.array(pucks, np.float32), "success": ok}


def generate(seed: int, n: int, split: str = "train", workers: int | None = None) -> list[dict]:
    workers = workers or min(32, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        return list(pool.map(episode, [seed] * n, range(n), [split] * n, chunksize=4))


def cached(seed: int, n: int, split: str = "train") -> list[dict]:
    import pickle
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "runs" / "vla" / f"demos_{split}_{seed}_{n}.pkl"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pickle.dumps(generate(seed, n, split)))
    return pickle.loads(path.read_bytes())


def to_arrays(episodes: list[dict], tokenizer, chunk: int) -> dict:
    images, words, states, targets, masks, pucks, tasks = [], [], [], [], [], [], []
    for ep in episodes:
        if not ep["success"]:
            continue
        t_len = len(ep["actions"])
        tokens = tokenizer(ep["text"])
        padded = np.concatenate([ep["actions"], np.zeros((chunk, 2), np.float32)])
        task = [tt.OBJECTS.index(ep["task"][0]), list(tt.ZONES).index(ep["task"][1])]
        for t in range(t_len):
            images.append(ep["images"][t])
            words.append(tokens)
            states.append(ep["states"][t])
            targets.append(padded[t:t + chunk])
            masks.append((np.arange(chunk) + t < t_len).astype(np.float32))
            pucks.append(ep["pucks"][t])
            tasks.append(task)
    return {"images": np.array(images), "words": np.array(words), "states": np.array(states),
            "targets": np.array(targets), "masks": np.array(masks), "pucks": np.array(pucks), "tasks": np.array(tasks)}
