"""Lesson 14.2: demonstrations as a dataset: format, coverage, and why validation loss is not evaluation.

INPUT   mjcourse.il.pointmass (task, expert), mjcourse.il.bc (cloning)
PROCESS (1) write 20 expert episodes recorded with pushes in a documented episode format
            (one .npz per episode, metadata.json), read them back, validate them, and replay
            each episode's actions from its start: with the recorded pushes and without;
        (2) three datasets of 20 episodes each: starts on one side of the obstacle only, starts
            everywhere, and starts everywhere with pushes; two coverage measures; clones
            trained on each (3 seeds) evaluated on 100 held-out starts with and without pushes;
        (3) validation loss against closed-loop success: clones of the last two datasets saved
            after 250 to 5 000 training steps (2 seeds), each scored by its validation error on
            5 held-out demonstrations and by closed-loop success; their rank correlation
OUTPUT  a dataset directory and printed tables

Run:  python examples/l14_2_offline_datasets.py
"""
# requires: torch

import hashlib
import inspect
import json
import os
import tempfile
from multiprocessing import Pool
from pathlib import Path

import mujoco
import numpy as np
import torch
from scipy.stats import spearmanr

from mjcourse.il import bc
from mjcourse.il import pointmass as pm
from mjcourse.paths import model_path

FAST = os.environ.get("MJC_FAST") == "1"
PUSH = 1.0
HELD_OUT = pm.sample_starts(np.random.default_rng(999), 30 if FAST else 100)


class RecordingPushes:
    """A random generator that remembers when pushes happened, so an episode can record them."""

    def __init__(self, seed):
        self.rng, self.log, self.calls, self.pending = np.random.default_rng(seed), [], 0, None

    def random(self):
        self.calls += 1
        return self.rng.random()

    def uniform(self, low, high):
        angle = self.rng.uniform(low, high)
        self.log.append((self.calls - 1, angle))                 # the step index at which it fired
        return angle


def record_episode(start, seed, push_rate) -> dict:
    sim, rng = pm.PointMass(), RecordingPushes(seed)
    run = sim.rollout(pm.expert, start, push_rate=push_rate, rng=rng)
    pushes = np.array([[step, 0.4 * np.cos(a), 0.4 * np.sin(a)] for step, a in rng.log]).reshape(-1, 3)
    rewards = -np.linalg.norm(run.states[:, :2] - pm.GOAL, axis=1) * sim.model.opt.timestep
    return {"states": run.states, "actions": run.actions, "rewards": rewards, "pushes": pushes, "start": np.asarray(start),
            "terminated": np.array(run.success), "truncated": np.array(not run.success), "seed": np.array(seed)}


def replay(episode: dict, with_pushes: bool) -> float:
    """Largest position difference (m) between the recorded states and a replay of the actions."""
    m = mujoco.MjModel.from_xml_path(str(model_path("point_mass")))
    d = mujoco.MjData(m)
    d.qpos[:] = episode["start"]
    mujoco.mj_forward(m, d)
    kicks = {int(step): dv for step, *dv in episode["pushes"]} if with_pushes else {}
    worst = 0.0
    for t, action in enumerate(episode["actions"]):
        if t in kicks:
            d.qvel[:] += kicks[t]
        worst = max(worst, float(np.abs(d.qpos - episode["states"][t, :2]).max()))
        d.ctrl[:] = action
        mujoco.mj_step(m, d)
    return worst


def part1(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    starts = pm.sample_starts(np.random.default_rng(3), 20)
    episodes = [record_episode(s, seed=100 + i, push_rate=PUSH) for i, s in enumerate(starts)]
    meta = {"format": "one npz per episode", "task": "point mass around an obstacle (mjcourse.il.pointmass)",
            "mujoco": mujoco.__version__, "timestep": 0.01,
            "expert_sha256": hashlib.sha256(inspect.getsource(pm.expert).encode()).hexdigest(),
            "model_sha256": hashlib.sha256(Path(model_path("point_mass")).read_bytes()).hexdigest(),
            "push": {"rate_per_s": PUSH, "speed_m_s": 0.4},
            "arrays": {"states": "(T, 4) x, y, vx, vy before each action", "actions": "(T, 2) force (N), in [-1, 1]",
                       "rewards": "(T,) minus distance to the goal times the timestep",
                       "pushes": "(P, 3) step index, dvx, dvy: disturbances that are not actions",
                       "start": "(2,)", "terminated": "reached the goal", "truncated": "ran out of time", "seed": "push generator seed"}}
    (root / "metadata.json").write_text(json.dumps(meta, indent=1))
    for i, ep in enumerate(episodes):
        np.savez_compressed(root / f"episode_{i:03d}.npz", **ep)
    loaded = [dict(np.load(p)) for p in sorted(root.glob("episode_*.npz"))]
    problems = []
    for i, ep in enumerate(loaded):
        t = len(ep["states"])
        if ep["actions"].shape != (t, 2) or ep["rewards"].shape != (t,):
            problems.append(f"{i}: lengths")
        if np.abs(ep["actions"]).max() > 1.0:
            problems.append(f"{i}: action range")
        if bool(ep["terminated"]) == bool(ep["truncated"]):
            problems.append(f"{i}: terminal flags")
    with_p = [replay(ep, True) for ep in loaded]
    without_p = [replay(ep, False) for ep in loaded]
    lengths = [len(ep["states"]) for ep in loaded]
    print(f"  20 episodes, {sum(lengths)} steps ({min(lengths)} to {max(lengths)} per episode), "
          f"{sum(len(ep['pushes']) for ep in loaded)} pushes, {sum(bool(ep['terminated']) for ep in loaded)} reached the goal")
    print(f"  validation: {'no problems' if not problems else problems}")
    print(f"  replaying the actions from each start: largest position error with the recorded pushes {max(with_p):.1e} m; "
          f"without them {np.median(without_p):.3f} m median, {max(without_p):.3f} m worst")


def dataset(kind: str, seed: int, n: int = 20) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng([seed, {"narrow": 1, "broad": 2, "broad with pushes": 3}[kind]])
    starts = pm.sample_starts(rng, n)
    if kind == "narrow":
        starts[:, 1] = rng.uniform(0.10, 0.25, n)                  # one side of the obstacle only
    rate = PUSH if kind == "broad with pushes" else 0.0
    sim = pm.PointMass()
    runs = [sim.rollout(pm.expert, s, push_rate=rate, rng=np.random.default_rng([seed, 9, i])) for i, s in enumerate(starts)]
    return np.vstack([r.states for r in runs]), np.vstack([r.actions for r in runs]), starts


def coverage(states: np.ndarray, reference: np.ndarray, scale: np.ndarray) -> tuple[float, float]:
    """(fraction of free 2 cm cells in the arena visited; fraction of reference states within
    0.5 standard deviations of some dataset state)."""
    cells = {(int((x + 0.5) // 0.02), int((y + 0.5) // 0.02)) for x, y in states[:, :2]}
    xs = (np.arange(50) + 0.5) * 0.02 - 0.5
    free = sum(1 for x in xs for y in xs if np.hypot(x, y) > 0.125 and abs(x) < 0.475 and abs(y) < 0.475)
    a, b = reference / scale, states / scale
    near = np.zeros(len(a), bool)
    for i in range(0, len(a), 1000):
        near[i:i + 1000] = np.sqrt(((a[i:i + 1000, None] - b[None]) ** 2).sum(-1)).min(1) < 0.5
    return len(cells) / free, float(near.mean())


def train_and_score(job) -> dict:
    kind, seed = job
    torch.set_num_threads(1)
    states, actions, _ = dataset(kind, seed)
    policy, _ = bc.fit(states, actions, seed=seed)
    clean = pm.evaluate(policy, HELD_OUT)["success"]
    pushed = pm.evaluate(policy, HELD_OUT, push_rate=PUSH)["success"]
    return {"kind": kind, "seed": seed, "clean": clean, "pushed": pushed}


def part2() -> None:
    kinds = ("narrow", "broad", "broad with pushes")
    reference = np.vstack([r.states for r in pm.evaluate(pm.expert, HELD_OUT, push_rate=PUSH)["runs"]])
    scale = reference.std(axis=0)
    print(f"  {'dataset (20 episodes)':<22}{'states':>8}{'cells covered':>15}{'test states covered':>21}")
    for kind in kinds:
        states, _, _ = dataset(kind, 0)
        cells, near = coverage(states, reference, scale)
        print(f"  {kind:<22}{len(states):>8d}{cells:>15.1%}{near:>21.1%}")
    jobs = [(k, s) for k in kinds for s in range(1 if FAST else 3)]
    if FAST:
        results = [train_and_score(j) for j in jobs]
    else:
        with Pool(len(jobs)) as pool:
            results = pool.map(train_and_score, jobs)
    print("  clones, success on 100 held-out starts per seed:")
    for kind in kinds:
        rows = [r for r in results if r["kind"] == kind]
        print(f"    {kind:<22} without pushes {', '.join(f'{r['clean']:.2f}' for r in rows)};   "
              f"with pushes {', '.join(f'{r['pushed']:.2f}' for r in rows)}")


def checkpoint_scores(job) -> list[dict]:
    kind, seed = job
    torch.set_num_threads(1)
    states, actions, _ = dataset(kind, seed)
    val_s, val_a, _ = dataset(kind, seed + 100, n=5)               # 5 more demonstrations, same distribution
    rows = []
    for steps in ((100, 500) if FAST else (250, 500, 1000, 2000, 3000, 5000)):
        policy, info = bc.fit(states, actions, steps=steps, seed=seed, validation=(val_s, val_a))
        rows.append({"kind": kind, "seed": seed, "steps": steps, "val": info["val_mse"],
                     "success": pm.evaluate(policy, HELD_OUT, push_rate=PUSH)["success"]})
    return rows


def part3() -> None:
    jobs = [(k, s) for k in ("broad", "broad with pushes") for s in range(1 if FAST else 2)]
    if FAST:
        rows = [r for j in jobs for r in checkpoint_scores(j)]
    else:
        with Pool(len(jobs)) as pool:
            rows = [r for out in pool.map(checkpoint_scores, jobs) for r in out]
    print(f"  {'dataset':<20}{'seed':>5}  validation MSE / success with pushes at 250, 500, 1000, 2000, 3000, 5000 steps")
    for k, s in jobs:
        sel = [r for r in rows if r["kind"] == k and r["seed"] == s]
        print(f"  {k:<20}{s:>5}  " + ", ".join(f"{r['val']:.3f}/{r['success']:.2f}" for r in sel))
    rho, p = spearmanr([r["val"] for r in rows], [r["success"] for r in rows])
    print(f"  across all {len(rows)} checkpoints: Spearman correlation of validation MSE with success {rho:.2f} (p = {p:.2g})")
    for k in ("broad", "broad with pushes"):
        sel = [r for r in rows if r["kind"] == k]
        rho_k, p_k = spearmanr([r["val"] for r in sel], [r["success"] for r in sel])
        print(f"  within '{k}': {rho_k:.2f} (p = {p_k:.2g})")


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}, torch {torch.__version__}; pushes {PUSH} per second, 0.4 m/s")
    print("(1) an episode format, validated and replayed")
    part1(Path(tempfile.gettempdir()) / "mjcourse_l14_2")
    print("(2) coverage and closed-loop success")
    part2()
    print("(3) validation loss against closed-loop success, per checkpoint")
    part3()
