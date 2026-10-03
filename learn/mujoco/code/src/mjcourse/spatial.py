"""Rotations and rigid transforms in MuJoCo's conventions, written out in NumPy.

MuJoCo's conventions, which every function here follows:
  * quaternions are (w, x, y, z), w first, unit length;
  * rotation matrices act on column vectors and are stored row-major when flat;
  * Euler sequences are three characters from "xyzXYZ"; lower case means
    intrinsic (rotate about the moving axes: R = R1 R2 R3), upper case extrinsic
    (rotate about the fixed axes: R = R3 R2 R1). This matches mju_euler2Quat.

Every function is tested against MuJoCo's own mju_* implementation in
tests/test_spatial.py. They exist so the mathematics of Level 4 can be read
and changed; in production code, prefer the mju_* functions.
"""

from __future__ import annotations

import numpy as np

Array = np.ndarray


def quat_mul(a: Array, b: Array) -> Array:
    """Hamilton product a * b (apply b, then a, when both are rotations)."""
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return np.array([
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ])


def quat_conj(q: Array) -> Array:
    """Conjugate; for a unit quaternion this is the inverse rotation."""
    return np.array([q[0], -q[1], -q[2], -q[3]])


def quat_to_mat(q: Array) -> Array:
    """3x3 rotation matrix of a unit quaternion."""
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def mat_to_quat(r: Array) -> Array:
    """Unit quaternion of a rotation matrix (Shepperd's method), with w >= 0."""
    t = np.trace(r)
    if t > 0:
        s = 2.0 * np.sqrt(1.0 + t)
        q = np.array([0.25 * s, (r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s])
    else:
        i = int(np.argmax(np.diag(r)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = 2.0 * np.sqrt(1.0 + r[i, i] - r[j, j] - r[k, k])
        q = np.empty(4)
        q[0] = (r[k, j] - r[j, k]) / s
        q[1 + i] = 0.25 * s
        q[1 + j] = (r[j, i] + r[i, j]) / s
        q[1 + k] = (r[k, i] + r[i, k]) / s
    q /= np.linalg.norm(q)
    return q if q[0] >= 0 else -q


def axis_angle_to_quat(axis: Array, angle: float) -> Array:
    """Rotation by `angle` (rad) about `axis` (any non-zero length)."""
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    return np.concatenate([[np.cos(angle / 2)], np.sin(angle / 2) * axis])


def quat_to_rotvec(q: Array) -> Array:
    """Rotation vector (axis times angle, angle in [0, pi]) of a unit quaternion.

    q and -q are the same rotation; the sign is chosen so the angle is at most pi.
    """
    q = q / np.linalg.norm(q)
    if q[0] < 0:
        q = -q
    s = np.linalg.norm(q[1:])
    if s < 1e-12:
        return 2.0 * q[1:]                      # first-order expansion near the identity
    angle = 2.0 * np.arctan2(s, q[0])
    return angle * q[1:] / s


def rotvec_to_quat(v: Array) -> Array:
    """Inverse of quat_to_rotvec: exp of a rotation vector."""
    angle = np.linalg.norm(v)
    if angle < 1e-12:
        q = np.concatenate([[1.0], 0.5 * np.asarray(v, dtype=float)])
        return q / np.linalg.norm(q)
    return axis_angle_to_quat(v, angle)


def euler_to_quat(euler: Array, seq: str = "xyz") -> Array:
    """MuJoCo's Euler convention: lower case intrinsic, upper case extrinsic."""
    if len(seq) != 3 or any(c not in "xyzXYZ" for c in seq):
        raise ValueError(f"seq must be 3 characters from 'xyzXYZ', got {seq!r}")
    axes = {"x": [1.0, 0, 0], "y": [0, 1.0, 0], "z": [0, 0, 1.0]}
    q = np.array([1.0, 0, 0, 0])
    for angle, c in zip(euler, seq):
        step = axis_angle_to_quat(axes[c.lower()], angle)
        q = quat_mul(q, step) if c.islower() else quat_mul(step, q)
    return q


def geodesic_angle(q1: Array, q2: Array) -> float:
    """Angle (rad) of the rotation taking q1 to q2; insensitive to the sign of either.

    Uses atan2 on the relative quaternion rather than arccos of a dot product:
    arccos loses about half the digits near 1, i.e. for nearly equal rotations.
    """
    rel = quat_mul(quat_conj(q1 / np.linalg.norm(q1)), q2 / np.linalg.norm(q2))
    return 2.0 * float(np.arctan2(np.linalg.norm(rel[1:]), abs(rel[0])))


def hat(w: Array) -> Array:
    """Skew-symmetric matrix with hat(w) @ v == cross(w, v)."""
    return np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])


def transform(r: Array, p: Array) -> Array:
    """4x4 homogeneous transform from a rotation and a translation."""
    t = np.eye(4)
    t[:3, :3], t[:3, 3] = r, p
    return t


def transform_inv(t: Array) -> Array:
    """Inverse of a rigid transform without a general matrix inverse: (R, p) -> (R^T, -R^T p)."""
    r, p = t[:3, :3], t[:3, 3]
    return transform(r.T, -r.T @ p)
