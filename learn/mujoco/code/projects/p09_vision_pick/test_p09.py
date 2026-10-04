"""Project 9 tests: estimate accuracy, pick success without privileged state, honest reports."""

import numpy as np
import pytest
import vision_scene as vs

pytestmark = pytest.mark.render

HELD_OUT_SEED, EPISODES = 13, 100
PROJECT_8_RATE = 1.00                 # Project 8's reference: 300 of 300 cubes on its held-out layouts
_RESULTS: dict[str, list] = {}


def test_estimates_within_5_mm_on_95_percent_of_frames(impl):
    pairs = vs.estimate_many(impl.__file__, vs.sample_states(HELD_OUT_SEED, EPISODES))
    errors = [np.linalg.norm(estimate[c] - truth[c]) if c in estimate else np.inf
              for estimate, truth in pairs for c in vs.CUBES]       # an unseen cube counts as a miss
    within = np.mean(np.array(errors) <= 0.005)
    assert within >= 0.95, f"{within:.3f} of {len(errors)} cube estimates within 5 mm"


@pytest.fixture
def episodes(impl):
    if impl.__file__ not in _RESULTS:
        _RESULTS[impl.__file__] = vs.run_many(impl.__file__, vs.sample_states(HELD_OUT_SEED, EPISODES))
    return _RESULTS[impl.__file__]


def test_success_within_10_points_of_project_8(episodes):
    for cube in vs.CUBES:
        rate = np.mean([r["placed"][cube] for r in episodes])
        assert rate >= PROJECT_8_RATE - 0.10, f"{cube} placed in {rate:.2f} of episodes"


def test_reports_are_honest(episodes):
    for r in episodes:
        assert set(r["reported"]) == set(vs.CUBES) and r["seconds"] <= vs.EPISODE_LIMIT
        for cube, category in r["reported"].items():
            assert category in vs.CATEGORIES
            assert (category == "success") == r["placed"][cube], f"{cube}: reported {category!r}"


def test_failures_are_reported_at_the_right_stage(impl):
    for r in vs.run_many(impl.__file__, vs.sample_states(HELD_OUT_SEED + 1, 6), degraded=True):
        for cube in vs.CUBES:
            assert not r["placed"][cube] and r["reported"][cube] in vs.GRASP_STAGE, r["reported"][cube]
