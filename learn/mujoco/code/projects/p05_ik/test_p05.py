"""Project 5 tests: accuracy on reachable poses, honesty on unreachable ones, limits, posture."""

import mujoco
import numpy as np
import pytest

from mjcourse import model_path

POS_TOL, ROT_TOL = 1e-3, np.radians(1.0)


@pytest.fixture(scope="module")
def arm():
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    return model, model.key("home").qpos.copy()


def site_pose(model, q):
    data = mujoco.MjData(model)
    data.qpos[:] = q
    mujoco.mj_kinematics(model, data)
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, data.site("ee").xmat)
    return data.site("ee").xpos.copy(), quat


def reachable_targets(model, n, seed):
    """Reachable by construction: forward kinematics of random joint vectors inside the limits."""
    rng = np.random.default_rng(seed)
    return [site_pose(model, rng.uniform(*model.jnt_range.T)) for _ in range(n)]


def reached(model, q, pos, quat):
    """Checked independently of the solver: angle between orientations from the quaternion dot product."""
    p, qt = site_pose(model, q)
    angle = 2 * np.arccos(min(1.0, abs(float(qt @ quat))))
    return np.linalg.norm(p - pos) < POS_TOL and angle < ROT_TOL


def test_pose_error(impl, arm):
    model, home = arm
    data = mujoco.MjData(model)
    data.qpos[:] = home
    mujoco.mj_kinematics(model, data)
    pos, quat = site_pose(model, home)
    np.testing.assert_allclose(impl.pose_error(model, data, "ee", pos, quat), 0, atol=1e-9)
    shifted = impl.pose_error(model, data, "ee", pos + [0.01, 0, 0], quat)
    np.testing.assert_allclose(shifted[:3], [0.01, 0, 0], atol=1e-12)
    turned = site_pose(model, home + np.r_[0.1, np.zeros(6)])[1]        # 0.1 rad about the base z axis
    for q in (turned, -turned):
        err = impl.pose_error(model, data, "ee", pos, q)
        assert np.linalg.norm(err[3:]) == pytest.approx(0.1, abs=1e-6)


def test_reaches_100_reachable_poses_inside_limits(impl, arm):
    model, home = arm
    lo, hi = model.jnt_range.T
    for pos, quat in reachable_targets(model, 100, seed=2026):        # a seed the reference was not tuned on
        q, ok = impl.solve(model, "ee", pos, quat, home)
        assert ok, "a reachable pose was reported unreachable"
        assert np.all(q >= lo) and np.all(q <= hi), "joint limit violated"
        assert reached(model, q, pos, quat), "success claimed for a pose that was not reached"


def test_negated_target_quaternions(impl, arm):
    model, home = arm
    for pos, quat in reachable_targets(model, 20, seed=7):
        q, ok = impl.solve(model, "ee", pos, -quat, home)
        assert ok and reached(model, q, pos, quat)


UNREACHABLE = [
    ([1.5, 0.0, 0.5], [0.0, 1.0, 0.0, 0.0]),         # beyond the arm's 1.05 m reach from the shoulder
    ([0.0, 0.0, 2.0], [0.0, 1.0, 0.0, 0.0]),
    ([0.0, 0.0, -0.5], [0.0, 1.0, 0.0, 0.0]),        # below the floor the base stands on
    ([-0.9, 0.9, 0.3], [0.0, 1.0, 0.0, 0.0]),
    ([0.0, 0.0, 1.33], [0.0, 1.0, 0.0, 0.0]),        # position reachable pointing up (top is 1.38 m), not pointing down
]


@pytest.mark.parametrize("pos, quat", UNREACHABLE)
def test_reports_failure_when_unreachable(impl, arm, pos, quat):
    model, home = arm
    _, ok = impl.solve(model, "ee", np.array(pos), np.array(quat), home)
    assert not ok


def test_posture_term_selects_the_solution(impl, arm):
    model, home = arm
    pos, quat = site_pose(model, home)
    start = np.clip(home + 0.3, *model.jnt_range.T)
    q, ok = impl.solve(model, "ee", pos, quat, start, posture=home)
    assert ok
    assert np.max(np.abs(q - home)) < 1e-3, "among the solutions, the one at the posture should win"
