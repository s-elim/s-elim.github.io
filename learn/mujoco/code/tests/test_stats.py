"""mjcourse.stats: interval coverage, edge cases, aggregation."""

import numpy as np
import pytest

from mjcourse import stats


def test_wilson_known_value():
    lo, hi = stats.wilson_interval(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)


def test_wilson_edges_have_width():
    lo, hi = stats.wilson_interval(10, 10)
    assert hi == 1.0 and lo < 0.8
    lo, hi = stats.wilson_interval(0, 10)
    assert lo == 0.0 and hi > 0.2


def test_wilson_coverage():
    rng = np.random.default_rng(1)
    p, n, trials, covered = 0.7, 40, 4000, 0
    for _ in range(trials):
        lo, hi = stats.wilson_interval(int(rng.binomial(n, p)), n)
        covered += lo <= p <= hi
    assert 0.93 < covered / trials < 0.97


def test_episodes_for_halfwidth():
    assert stats.episodes_for_halfwidth(0.05) == 385


def test_iqm_ignores_outliers():
    assert stats.iqm([1, 1, 1, 1, 100, -100, 1, 1]) == pytest.approx(1.0)


def test_bootstrap_brackets_mean():
    rng = np.random.default_rng(0)
    x = rng.normal(2.0, 1.0, size=200)
    est, lo, hi = stats.bootstrap_ci(x)
    assert lo < est < hi and lo < 2.0 < hi


def test_paired_difference_detects_shift():
    rng = np.random.default_rng(0)
    base = rng.normal(size=100)
    est, lo, hi = stats.paired_difference_ci(base + 0.5, base)
    assert est == pytest.approx(0.5) and lo > 0


def test_task_vs_episode_aggregation():
    s = np.array([1, 1, 1, 1, 1, 1, 1, 1, 0, 0])
    t = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 1])
    assert stats.per_episode_mean(s) == pytest.approx(0.8)
    assert stats.per_task_mean(s, t) == pytest.approx(0.5)


def test_bad_inputs():
    with pytest.raises(ValueError):
        stats.wilson_interval(3, 0)
    with pytest.raises(ValueError):
        stats.wilson_interval(5, 4)
