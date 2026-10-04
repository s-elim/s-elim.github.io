"""Project 7 tests: held-out success with a Wilson bound, the corners of the randomization, limits."""

import itertools

import grasp_scene as gs
import numpy as np

from mjcourse import stats

HELD_OUT_SEED, N_HELD_OUT = 7, 400          # not the tuning seed (0)


def test_controls_stay_inside_ctrlrange(impl):
    model = gs.make_model()
    lo, hi = model.actuator_ctrlrange.T
    for state in gs.sample_states(HELD_OUT_SEED + 1, 5):
        data = gs.reset(model, state)
        controller = impl.make_controller(model, data)
        for t in np.arange(0, gs.EPISODE_SECONDS, 0.05):
            u = controller(t, data)
            assert u.shape == (4,) and np.all(u >= lo - 1e-9) and np.all(u <= hi + 1e-9)


def test_corners_of_the_randomization(impl):
    """All 32 combinations of the range ends: the heavy, slippery, 45-degree, far-corner cube included."""
    model = gs.make_model()
    corners = itertools.product([-0.2, 0.2], [-0.2, 0.2], [-np.pi / 4, np.pi / 4], [0.05, 0.5], [0.4, 1.2])
    failed = [c for c in corners if not gs.run_episode(model, np.array(c), impl.make_controller)["success"]]
    assert failed == [], f"{len(failed)} corner states failed, e.g. {np.round(failed[0], 3)}"


def test_held_out_success_rate(impl):
    model = gs.make_model()
    ok = [gs.run_episode(model, s, impl.make_controller)["success"] for s in gs.sample_states(HELD_OUT_SEED, N_HELD_OUT)]
    lower, _ = stats.wilson_interval(sum(ok), len(ok))
    assert np.mean(ok) >= 0.95 and lower > 0.90, f"success {np.mean(ok):.3f}, Wilson lower bound {lower:.3f}"
