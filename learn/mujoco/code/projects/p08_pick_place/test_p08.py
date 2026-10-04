"""Project 8 tests: per-cube success on held-out layouts, honest reports, failures at the right stage."""

import numpy as np
import pick_scene as ps
import pytest

HELD_OUT_SEED, EPISODES = 11, 100                  # not the tuning seed (0)
_RESULTS: dict[str, list] = {}


@pytest.fixture
def impl_results(impl):
    """The 100 held-out episodes, run once per implementation and shared by the tests below."""
    if impl.__file__ not in _RESULTS:
        _RESULTS[impl.__file__] = ps.run_many(impl.__file__, ps.sample_states(HELD_OUT_SEED, EPISODES))
    return _RESULTS[impl.__file__]


def test_each_cube_placed_in_90_percent(impl_results):
    for cube in ps.CUBES:
        rate = np.mean([r["placed"][cube] for r in impl_results])
        assert rate >= 0.90, f"{cube} placed in {rate:.2f} of episodes"


def test_reports_are_categories_and_honest(impl_results):
    for r in impl_results:
        assert set(r["reported"]) == set(ps.CUBES)
        for cube, category in r["reported"].items():
            assert category in ps.CATEGORIES, category
            assert (category == "success") == r["placed"][cube], f"{cube}: reported {category!r}, placed {r['placed'][cube]}"
        assert r["seconds"] <= ps.EPISODE_LIMIT


def test_failures_are_reported_at_the_right_stage(impl):
    """With frictionless pads nothing can be lifted: every cube must be reported as failing at the grasp."""
    results = ps.run_many(impl.__file__, ps.sample_states(HELD_OUT_SEED + 1, 8), degraded=True)
    for r in results:
        for cube in ps.CUBES:
            assert not r["placed"][cube]
            assert r["reported"][cube] in ps.GRASP_STAGE, f"{cube}: {r['reported'][cube]!r} for a cube that moved {r['moved'][cube]:.3f} m"
