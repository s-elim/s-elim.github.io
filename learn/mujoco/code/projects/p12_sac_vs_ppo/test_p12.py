"""Project 12 tests: a fair comparison (steps, checkpoints, evaluation, tuning effort) and a complete report."""

import comparison as cp
import numpy as np
import pytest

pytestmark = [pytest.mark.slow, pytest.mark.torch]
_RESULTS: dict[str, list] = {}


@pytest.fixture
def results(impl):
    if impl.__file__ not in _RESULTS:
        _RESULTS[impl.__file__] = cp.run_all(impl.__file__)
    return _RESULTS[impl.__file__]


def test_equal_tuning_effort_is_documented(impl):
    counts = {m: len(impl.TUNING.get(m, [])) for m in cp.METHODS}
    assert min(counts.values()) >= 2 and len(set(counts.values())) == 1, counts
    assert all(np.isfinite(e["tuning_success"]) for m in cp.METHODS for e in impl.TUNING[m])


def test_both_methods_use_exactly_the_budget(results):
    assert {r["steps"] for r in results} == {cp.BUDGET}, sorted({(r["method"], r["steps"]) for r in results})


def test_checkpoints_at_the_same_step_counts(results):
    for r in results:
        assert [n for n, _ in r["curve"]] == list(cp.EVAL_POINTS), (r["method"], r["seed"], r["curve"])


def test_both_evaluated_deterministically(results):
    assert all(r["deterministic"] for r in results)


def test_report_has_intervals_and_learning_happened(results):
    summary = cp.summarize(results)
    for method in cp.METHODS:
        lo, hi = summary[method]["ci"]
        assert lo <= summary[method]["iqm"] <= hi
        assert all(np.isfinite(v).all() for v in summary[method]["curve"].values())
    assert max(summary[m]["final"].mean() for m in cp.METHODS) >= 0.5
