"""Statistics for reporting simulation experiments honestly.

Success rates are binomial proportions; returns from several seeds are small
samples. These functions give intervals rather than single numbers, and help
choose how many episodes and seeds an experiment needs before running it.
"""

from __future__ import annotations

from math import ceil, sqrt
from typing import Callable

import numpy as np
from scipy import stats as _st


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Preferred over the normal ("Wald") interval, which is too narrow for small n
    and collapses to zero width at 0% or 100% success.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= successes <= n:
        raise ValueError("successes must be in [0, n]")
    z = _st.norm.ppf(0.5 + confidence / 2)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    lo, hi = max(0.0, centre - half), min(1.0, centre + half)
    # The exact bound at 0 or n successes is 0 or 1; rounding can leave 1 - 1e-16.
    return (0.0 if successes == 0 else lo), (1.0 if successes == n else hi)


def episodes_for_halfwidth(halfwidth: float, p: float = 0.5, confidence: float = 0.95) -> int:
    """Episodes needed so a normal-approximation interval has the given half-width at rate p.

    p = 0.5 is the worst case. Example: +-5 points at 95% needs 385 episodes.
    """
    z = _st.norm.ppf(0.5 + confidence / 2)
    return int(ceil(z * z * p * (1 - p) / (halfwidth * halfwidth)))


def iqm(values) -> float:
    """Interquartile mean: the mean of the middle 50% of values (robust to outlier seeds)."""
    v = np.sort(np.asarray(values, dtype=float).ravel())
    n = len(v)
    lo, hi = int(np.floor(0.25 * n)), int(np.ceil(0.75 * n))
    return float(v[lo:hi].mean())


def bootstrap_ci(values, statistic: Callable = np.mean, n_boot: int = 10_000, confidence: float = 0.95,
                 seed: int = 0) -> tuple[float, float, float]:
    """Percentile bootstrap interval: returns (estimate, low, high)."""
    v = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(n_boot, len(v)))
    boots = np.array([statistic(v[i]) for i in idx])
    alpha = (1 - confidence) / 2
    return float(statistic(v)), float(np.quantile(boots, alpha)), float(np.quantile(boots, 1 - alpha))


def paired_difference_ci(a, b, n_boot: int = 10_000, confidence: float = 0.95, seed: int = 0) -> tuple[float, float, float]:
    """Bootstrap interval for mean(a - b) when a[i] and b[i] share an initial state (paired design)."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    return bootstrap_ci(d, np.mean, n_boot, confidence, seed)


def per_task_mean(successes: np.ndarray, tasks: np.ndarray) -> float:
    """Mean over tasks of each task's success rate (each task weighted equally)."""
    s, t = np.asarray(successes, dtype=float), np.asarray(tasks)
    return float(np.mean([s[t == k].mean() for k in np.unique(t)]))


def per_episode_mean(successes: np.ndarray) -> float:
    """Mean over all episodes (tasks with more episodes weigh more)."""
    return float(np.mean(np.asarray(successes, dtype=float)))
