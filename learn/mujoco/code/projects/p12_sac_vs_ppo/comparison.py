"""Project 12 comparison protocol: shared by the tests, the starter, the solution and tune.py; do not edit it.

Task: Project 11's (ReachEnv, joint-delta actions). Both methods get exactly BUDGET environment steps per
run and the same five seeds. BUDGET and EVAL_POINTS are multiples of the course PPO's iteration (16 x 128 =
2048 steps), so both methods can be measured at the same step counts. Each run reports a checkpoint at every
point of EVAL_POINTS: deterministic success on CURVE_STATES (20). The final policy is evaluated deterministically on HELD_OUT
(100 states). Tuning uses TUNING_SEED and TUNING_STATES only, which the comparison never uses, and each
method gets the same number of tuning runs.
"""

import importlib.util
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from mjcourse import stats
from mjcourse.envs import ReachEnv

BUDGET = 30_720                                          # 15 PPO iterations
SEEDS = (0, 1, 2, 3, 4)
METHODS = ("ppo", "sac")
EVAL_POINTS = (6_144, 12_288, 18_432, 24_576, 30_720)    # every 3 PPO iterations
CURVE_STATES = range(10_100, 10_120)
HELD_OUT = range(10_000, 10_100)
TUNING_SEED, TUNING_STATES = 100, range(30_000, 30_020)
PROBES = range(20_000, 20_010)


def make_env() -> ReachEnv:
    return ReachEnv(action_mode="joint_delta")


def success(act, seeds) -> float:
    env = make_env()
    ok = []
    for seed in seeds:
        obs, info = env.reset(seed=int(seed))
        done = False
        while not done:
            obs, _, terminated, truncated, info = env.step(act(obs))
            done = terminated or truncated
        ok.append(bool(info["is_success"]))
    return float(np.mean(ok))


def deterministic(act) -> bool:
    env = make_env()
    probes = [env.reset(seed=s)[0] for s in PROBES]
    first = [np.array(act(o), copy=True) for o in probes]
    for o in probes[::-1]:
        act(o)
    return all(np.array_equal(a, np.asarray(act(o))) for a, o in zip(first, probes))


def _load(module_file):
    spec = importlib.util.spec_from_file_location("routine", module_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(module_file: str, method: str, seed: int, curve_states=CURVE_STATES, final_states=HELD_OUT) -> dict:
    import torch

    torch.set_num_threads(1)
    curve, evaluating = [], [0.0]

    def checkpoint(n, act):
        start = time.perf_counter()
        curve.append((int(n), success(act, curve_states)))
        evaluating[0] += time.perf_counter() - start

    start = time.perf_counter()
    act, steps = _load(module_file).train(method, seed, BUDGET, checkpoint)
    seconds = time.perf_counter() - start - evaluating[0]          # training only
    return {"method": method, "seed": seed, "steps": int(steps), "curve": curve, "train_seconds": seconds,
            "final": success(act, final_states), "deterministic": deterministic(act)}


def run_all(module_file: str, workers: int = 10) -> list[dict]:
    jobs = [(m, s) for m in METHODS for s in SEEDS]
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        return list(pool.map(_run, [module_file] * len(jobs), *zip(*jobs)))


def curve_at(run: dict, point: int) -> float | None:
    """The run's checkpoint at exactly `point` environment steps, or None."""
    return dict(run["curve"]).get(point)


def summarize(results: list[dict]) -> dict:
    out = {}
    for method in METHODS:
        runs = sorted((r for r in results if r["method"] == method), key=lambda r: r["seed"])
        final = np.array([r["final"] for r in runs])
        _, lo, hi = stats.bootstrap_ci(final, statistic=stats.iqm, seed=0)
        curve = {}
        for p in EVAL_POINTS:
            values = np.array([curve_at(r, p) for r in runs], dtype=float)
            mean, clo, chi = stats.bootstrap_ci(values, seed=0)
            curve[p] = (mean, clo, chi)
        out[method] = {"final": final, "iqm": stats.iqm(final), "ci": (lo, hi), "curve": curve}
    return out
