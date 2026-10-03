"""mjcourse.spatial agrees with MuJoCo's own mju_* functions."""

import mujoco
import numpy as np
import pytest

from mjcourse import spatial

RNG = np.random.default_rng(0)


def random_quat():
    q = RNG.normal(size=4)
    return q / np.linalg.norm(q)


@pytest.mark.parametrize("trial", range(20))
def test_quat_mul_and_mat(trial):
    a, b = random_quat(), random_quat()
    ref = np.zeros(4)
    mujoco.mju_mulQuat(ref, a, b)
    np.testing.assert_allclose(spatial.quat_mul(a, b), ref, atol=1e-12)
    mat = np.zeros(9)
    mujoco.mju_quat2Mat(mat, a)
    np.testing.assert_allclose(spatial.quat_to_mat(a), mat.reshape(3, 3), atol=1e-12)


@pytest.mark.parametrize("trial", range(20))
def test_mat_to_quat_roundtrip(trial):
    q = random_quat()
    back = spatial.mat_to_quat(spatial.quat_to_mat(q))
    assert spatial.geodesic_angle(q, back) < 1e-7
    ref = np.zeros(4)
    mujoco.mju_mat2Quat(ref, spatial.quat_to_mat(q).ravel())
    assert spatial.geodesic_angle(ref, back) < 1e-7


@pytest.mark.parametrize("seq", ["xyz", "XYZ", "zyx", "ZYX", "zxz", "xYz"])
def test_euler_matches_mujoco(seq):
    for _ in range(10):
        e = RNG.uniform(-np.pi, np.pi, size=3)
        ref = np.zeros(4)
        mujoco.mju_euler2Quat(ref, e, seq)
        assert spatial.geodesic_angle(spatial.euler_to_quat(e, seq), ref) < 1e-9


def test_rotvec_roundtrip_and_axis_angle():
    for _ in range(20):
        axis = RNG.normal(size=3)
        v = axis / np.linalg.norm(axis) * RNG.uniform(0.01, 3.1)   # angles below pi map back uniquely
        q = spatial.rotvec_to_quat(v)
        np.testing.assert_allclose(spatial.quat_to_rotvec(q), v, atol=1e-9)
        ref = np.zeros(4)
        mujoco.mju_axisAngle2Quat(ref, v / np.linalg.norm(v), np.linalg.norm(v))
        np.testing.assert_allclose(q, ref, atol=1e-12)


def test_double_cover():
    q = random_quat()
    np.testing.assert_allclose(spatial.quat_to_mat(q), spatial.quat_to_mat(-q), atol=1e-12)
    assert spatial.geodesic_angle(q, -q) < 1e-7


def test_transform_inverse():
    t = spatial.transform(spatial.quat_to_mat(random_quat()), RNG.normal(size=3))
    np.testing.assert_allclose(spatial.transform_inv(t) @ t, np.eye(4), atol=1e-12)


def test_hat_is_cross():
    w, v = RNG.normal(size=3), RNG.normal(size=3)
    np.testing.assert_allclose(spatial.hat(w) @ v, np.cross(w, v), atol=1e-12)


def test_bad_sequence():
    with pytest.raises(ValueError):
        spatial.euler_to_quat([0, 0, 0], "xyw")
