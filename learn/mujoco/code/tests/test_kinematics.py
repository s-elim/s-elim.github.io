"""Kinematics helpers: Jacobians against finite differences, IK against targets made by FK."""

import mujoco
import numpy as np
import pytest

from mjcourse import kinematics, model_path, spatial


@pytest.fixture(scope="module")
def arm7():
    return mujoco.MjModel.from_xml_path(str(model_path("arm7")))


def _targets(model, n, seed):
    data = mujoco.MjData(model)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        data.qpos[:] = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        mujoco.mj_kinematics(model, data)
        out.append((data.site("ee").xpos.copy(), spatial.mat_to_quat(data.site("ee").xmat.reshape(3, 3))))
    return out


def test_site_jacobian_matches_finite_differences(arm7):
    data = mujoco.MjData(arm7)
    data.qpos[:] = [0.3, 0.6, -0.4, 1.4, 0.2, 0.9, 0.1]
    mujoco.mj_kinematics(arm7, data)
    mujoco.mj_comPos(arm7, data)
    jp, jr = kinematics.site_jacobian(arm7, data, "ee")
    fp, fr = kinematics.fd_site_jacobian(arm7, data, "ee")
    assert np.abs(jp - fp).max() < 1e-8
    assert np.abs(jr - fr).max() < 1e-8


def test_ik_with_restarts_reaches_fk_targets_within_limits(arm7):
    home = arm7.key_qpos[arm7.key("home").id]
    for pos, quat in _targets(arm7, 15, seed=3):
        result, _ = kinematics.solve_ik_restarts(arm7, "ee", pos, quat, q_init=home, restarts=10)
        assert result.success
        assert np.all(result.qpos >= arm7.jnt_range[:, 0] - 1e-12)
        assert np.all(result.qpos <= arm7.jnt_range[:, 1] + 1e-12)
        assert result.pos_error < 1e-4 and result.rot_error < 1e-3


def test_nullspace_term_does_not_prevent_convergence(arm7):
    home = arm7.key_qpos[arm7.key("home").id]
    mid = arm7.jnt_range.mean(axis=1)
    plain = posture = 0
    for pos, quat in _targets(arm7, 20, seed=4):
        plain += kinematics.solve_ik(arm7, "ee", pos, quat, q_init=home, max_iters=300).success
        posture += kinematics.solve_ik(arm7, "ee", pos, quat, q_init=home, max_iters=300,
                                       nullspace_gain=0.1, q_rest=mid).success
    assert posture >= plain - 3          # the damped-inverse projector dropped this to about 40%


def test_ik_reports_failure_for_unreachable_target(arm7):
    result = kinematics.solve_ik(arm7, "ee", np.array([2.0, 0.0, 0.5]), max_iters=100)
    assert not result.success
    assert result.pos_error > 0.5
