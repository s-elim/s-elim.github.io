"""Lesson 21.2: seeds, episodes, intervals and comparisons, on real evaluation data (Level 21).

INPUT   the point-mass task of Level 14 with random pushes (1 per second); two methods: behaviour cloning from
        20 and from 80 clean demonstrations; each trained with 8 seeds; every policy evaluated on the same 400
        held-out starts with the same pushes (a paired design)
PROCESS (1) planning: episodes for a target interval half-width (mjcourse.stats.episodes_for_halfwidth);
        (2) each method's success: per seed, a Wilson interval pooled over all 3200 episodes, and a bootstrap
            interval over the 8 seeds;
        (3) the difference between the methods: over seeds, and paired by start (each start's success averaged
            over seeds, then differenced);
        (4) small studies drawn from these data: with k seeds per method and 100 episodes per seed, how often the
            better method wins, and how often a pooled Fisher test calls the difference significant;
        (5) aggregating tasks of unequal size: the clean task (400 starts) and the pushed task (100 starts),
            per episode and per task
OUTPUT  printed tables

Run:  python examples/l21_2_methodology.py          (about 8 minutes)
"""
# requires: torch

import os

import numpy as np
from scipy.stats import fisher_exact

from mjcourse.il import bc, pointmass
from mjcourse.stats import bootstrap_ci, episodes_for_halfwidth, per_episode_mean, per_task_mean, wilson_interval

FAST = os.environ.get("MJC_FAST") == "1"
SEEDS = 2 if FAST else 8
N_EVAL = 60 if FAST else 400


def train(n_demos: int, seed: int):
    sim = pointmass.PointMass()
    starts = pointmass.sample_starts(np.random.default_rng(1), n_demos)
    runs = [sim.rollout(pointmass.expert, s) for s in starts]
    policy, _ = bc.fit(np.vstack([r.states for r in runs]), np.vstack([r.actions for r in runs]),
                       steps=500 if FAST else 3000, seed=seed)
    return policy


def outcomes(policy, starts: np.ndarray, push_rate: float) -> np.ndarray:
    """Per-start success (0/1); the i-th start's pushes come from a fixed generator, shared by all policies."""
    return np.array([r.success for r in pointmass.evaluate(policy, starts, push_rate=push_rate, seed=12)["runs"]], float)


if __name__ == "__main__":
    print("(1) episodes needed for a 95% interval of half-width h at success rate p")
    print(f"    {'':<8}" + "".join(f"{'h = ' + str(h):>10}" for h in (0.10, 0.05, 0.02)))
    for p in (0.5, 0.8, 0.95):
        print(f"    {'p = ' + str(p):<8}" + "".join(f"{episodes_for_halfwidth(h, p):>10}" for h in (0.10, 0.05, 0.02)))
    starts = pointmass.sample_starts(np.random.default_rng(4), N_EVAL)
    data = {}
    for n in (20, 80):
        data[n] = np.array([outcomes(train(n, seed), starts, 1.0) for seed in range(SEEDS)])     # (seeds, starts)
    print(f"(2) success with pushes, {SEEDS} training seeds x {N_EVAL} starts per method")
    for n, x in data.items():
        per_seed = x.mean(axis=1)
        lo, hi = wilson_interval(int(x.sum()), x.size)
        est, blo, bhi = bootstrap_ci(per_seed)
        print(f"    BC from {n} demonstrations: per seed " + " ".join(f"{v:.3f}" for v in per_seed))
        print(f"        pooled over {x.size} episodes: {x.mean():.3f}, Wilson [{lo:.3f}, {hi:.3f}]; "
              f"over seeds: {est:.3f}, bootstrap [{blo:.3f}, {bhi:.3f}]")
    print("(3) the difference, BC from 20 minus BC from 80")
    a, b = data[20].mean(axis=1), data[80].mean(axis=1)
    rng = np.random.default_rng(0)
    boot = [rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean() for _ in range(10000)]
    print(f"    over seeds: {a.mean() - b.mean():+.3f}, bootstrap [{np.percentile(boot, 2.5):+.3f}, {np.percentile(boot, 97.5):+.3f}]")
    per_start = data[20].mean(axis=0) - data[80].mean(axis=0)                                    # paired by start
    boot = [rng.choice(per_start, per_start.size).mean() for _ in range(10000)]
    print(f"    paired by start (start-level variation only; seeds averaged): {per_start.mean():+.3f}, "
          f"bootstrap [{np.percentile(boot, 2.5):+.3f}, {np.percentile(boot, 97.5):+.3f}]")
    print("(4) small studies drawn from these data: k seeds per method, 100 episodes per seed, 2000 studies each")
    better = 20 if a.mean() > b.mean() else 80
    print(f"    (the better method over all data: BC from {better} demonstrations)")
    for k in ((1, 2) if FAST else (1, 2, 3, 5)):
        wins = significant = 0
        for _ in range(2000):
            cols = rng.choice(N_EVAL, min(100, N_EVAL), replace=False)
            xa = data[20][rng.choice(SEEDS, k, replace=False)][:, cols]
            xb = data[80][rng.choice(SEEDS, k, replace=False)][:, cols]
            wins += (xa.mean() > xb.mean()) == (better == 20)
            table = [[xa.sum(), xa.size - xa.sum()], [xb.sum(), xb.size - xb.sum()]]
            significant += fisher_exact(table)[1] < 0.05
        print(f"    k={k}: the better method wins in {wins / 2000:.2f} of studies; a pooled Fisher test calls the "
              f"difference significant in {significant / 2000:.2f}")
    print("(5) two tasks of unequal size, BC from 20 demonstrations (seed 0): clean 400 starts, pushed 100 starts")
    policy = train(20, 0)
    clean = outcomes(policy, starts, 0.0)
    pushed = outcomes(policy, starts[:min(100, N_EVAL)], 1.0)
    successes = np.r_[clean, pushed]
    tasks = np.r_[np.zeros(clean.size), np.ones(pushed.size)]
    print(f"    clean {clean.mean():.3f}, pushed {pushed.mean():.3f}; mean per episode {per_episode_mean(successes):.3f}, "
          f"mean per task {per_task_mean(successes, tasks):.3f}")
