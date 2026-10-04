"""Project 11 evaluation protocol: shared by the tests, the starter and the solution; do not edit it.

Task: mjcourse.envs.ReachEnv(action_mode="joint_delta"): move arm7's ee within 2 cm of a random target.
Budget: BUDGET environment steps per training run, the same for the main run and the ablation.
Seeds: TRAIN_SEEDS, five per variant; the seed is the unit of replication.
Evaluation: the deterministic policy (the mean action), observation statistics frozen, on 100 initial
states from reset seeds 10 000 to 10 099, which training never uses.
Report: per seed, the held-out success rate, the mean number of steps per episode, and the mean final
distance; across seeds, the mean, the interquartile mean (IQM) and a 95% percentile bootstrap interval
of the IQM; and the main-minus-ablation difference matched by seed.
"""

import importlib.util
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from mjcourse import stats
from mjcourse.envs import ReachEnv

BUDGET = 100_000
TRAIN_SEEDS = (0, 1, 2, 3, 4)
HELD_OUT = range(10_000, 10_100)
PROBES = range(20_000, 20_010)          # observations for the determinism check
VARIANTS = ("main", "ablation")


def make_env() -> ReachEnv:
    return ReachEnv(action_mode="joint_delta")


def evaluate(act, seeds=HELD_OUT) -> dict:
    env = make_env()
    success, length, distance = [], [], []
    for seed in seeds:
        obs, info = env.reset(seed=int(seed))
        done, n = False, 0
        while not done:
            obs, _, terminated, truncated, info = env.step(act(obs))
            n += 1
            done = terminated or truncated
        success.append(bool(info["is_success"]))
        length.append(n)
        distance.append(float(info["distance"]))
    return {"success": float(np.mean(success)), "length": float(np.mean(length)), "distance": float(np.mean(distance))}


def deterministic_and_frozen(act) -> bool:
    """The same observation gives the same action, before and after the policy has seen other observations."""
    env = make_env()
    probes = [env.reset(seed=s)[0] for s in PROBES]
    first = [np.array(act(o), copy=True) for o in probes]
    for _ in range(3):
        for o in probes[::-1]:
            act(o)
    return all(np.array_equal(a, np.asarray(act(o))) for a, o in zip(first, probes))


def _run(module_file: str, seed: int, variant: str) -> dict:
    import torch

    torch.set_num_threads(1)
    spec = importlib.util.spec_from_file_location("routine", module_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    act, steps = module.train(seed, variant, BUDGET)
    return {"seed": seed, "variant": variant, "steps": int(steps), **evaluate(act),
            "deterministic": deterministic_and_frozen(act)}


def run_all(module_file: str, workers: int = 10) -> list[dict]:
    """All seeds of both variants, in spawned processes (each trains with its own vector environments)."""
    jobs = [(seed, variant) for variant in VARIANTS for seed in TRAIN_SEEDS]
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        return list(pool.map(_run, [module_file] * len(jobs), *zip(*jobs)))


def summarize(results: list[dict], metric: str = "success") -> dict:
    out = {}
    for variant in VARIANTS:
        values = np.array([r[metric] for r in sorted(results, key=lambda r: r["seed"]) if r["variant"] == variant])
        _, lo, hi = stats.bootstrap_ci(values, statistic=stats.iqm, seed=0)
        out[variant] = {"per_seed": values, "mean": float(values.mean()), "iqm": stats.iqm(values), "ci": (lo, hi)}
    diff = out["main"]["per_seed"] - out["ablation"]["per_seed"]
    _, lo, hi = stats.bootstrap_ci(diff, seed=0)
    out["main_minus_ablation"] = {"mean": float(diff.mean()), "ci": (lo, hi)}
    return out
