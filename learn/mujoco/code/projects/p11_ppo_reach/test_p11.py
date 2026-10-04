"""Project 11 tests: success on held-out states over five seeds, equal budgets, a fair evaluation."""

import numpy as np
import pytest
import rl_protocol as rp

pytestmark = [pytest.mark.slow, pytest.mark.torch]
_RESULTS: dict[str, list] = {}


@pytest.fixture
def results(impl):
    if impl.__file__ not in _RESULTS:
        _RESULTS[impl.__file__] = rp.run_all(impl.__file__)
    return _RESULTS[impl.__file__]


def test_the_ablation_is_declared(impl):
    assert impl.ABLATION.strip(), "say what the ablation changes"


def test_main_runs_succeed_on_held_out_states(results):
    summary = rp.summarize(results)["main"]
    assert summary["mean"] > 0.90, f"mean held-out success over seeds {summary['per_seed']}"


def test_both_variants_get_the_same_budget(results):
    steps = {(r["variant"], r["seed"]): r["steps"] for r in results}
    assert all(0.9 * rp.BUDGET <= s <= rp.BUDGET for s in steps.values()), steps
    assert all(steps[("main", s)] == steps[("ablation", s)] for s in rp.TRAIN_SEEDS), steps


def test_policies_are_evaluated_deterministically(results):
    assert all(r["deterministic"] for r in results), "act() must be deterministic and must not update statistics"


def test_report_has_an_iqm_and_an_interval(results):
    summary = rp.summarize(results)
    for variant in rp.VARIANTS:
        lo, hi = summary[variant]["ci"]
        assert len(summary[variant]["per_seed"]) == len(rp.TRAIN_SEEDS)
        assert lo <= summary[variant]["iqm"] <= hi
    assert np.isfinite(summary["main_minus_ablation"]["mean"])
