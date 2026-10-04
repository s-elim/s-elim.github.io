"""Project 5 reference solution: 6D damped-least-squares IK with limits and a null-space posture term."""

import mujoco
import numpy as np

POS_TOL = 1e-3                  # m, the acceptance tolerance
ROT_TOL = np.radians(1.0)       # rad
MAX_STEP = 0.2                  # rad per iteration on any joint
POSTURE_GAIN = 0.1


def pose_error(model, data, site, target_pos, target_quat):
    """[position error, rotation-vector error], both in the world frame, from the current site pose."""
    sid = model.site(site).id
    current = np.zeros(4)
    mujoco.mju_mat2Quat(current, data.site_xmat[sid])
    diff = np.zeros(4)
    mujoco.mju_mulQuat(diff, target_quat, current * [1, -1, -1, -1])    # target * current^-1
    if diff[0] < 0:                                   # q and -q are the same rotation; take the short way
        diff = -diff
    rotvec = np.zeros(3)
    mujoco.mju_quat2Vel(rotvec, diff, 1.0)
    return np.r_[target_pos - data.site_xpos[sid], rotvec]


def _converge(model, data, sid, target_pos, target_quat, posture, damping, iters):
    lo, hi = model.jnt_range.T
    jacp, jacr = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    for _ in range(iters):
        mujoco.mj_kinematics(model, data)
        mujoco.mj_comPos(model, data)                 # mj_jacSite reads cdof and subtree_com, set here
        err = pose_error(model, data, sid, target_pos, target_quat)
        mujoco.mj_jacSite(model, data, jacp, jacr, sid)
        jac = np.vstack([jacp, jacr])
        # Exact null-space projector. The damped one, I - J^T (J J^T + l^2 I)^-1 J, leaks into the task.
        null_step = (np.eye(model.nv) - np.linalg.pinv(jac, rcond=1e-6) @ jac) @ (POSTURE_GAIN * (posture - data.qpos))
        task_done = np.linalg.norm(err[:3]) < 0.1 * POS_TOL and np.linalg.norm(err[3:]) < 0.1 * ROT_TOL
        if task_done and np.linalg.norm(null_step) < 1e-6:
            break                                     # on target and the posture can improve no further
        dq = jac.T @ np.linalg.solve(jac @ jac.T + damping**2 * np.eye(6), err) + null_step
        dq *= min(1.0, MAX_STEP / max(np.abs(dq).max(), 1e-12))
        data.qpos[:] = np.clip(data.qpos + dq, lo, hi)
    mujoco.mj_kinematics(model, data)
    err = pose_error(model, data, sid, target_pos, target_quat)
    return np.linalg.norm(err[:3]) < 0.1 * POS_TOL and np.linalg.norm(err[3:]) < 0.1 * ROT_TOL


def solve(model, site, target_pos, target_quat, q_init, posture=None, restarts=20, damping=0.05, iters=200, seed=0):
    """Returns (q, success). On failure q is the last attempt and must not be used as an answer."""
    data = mujoco.MjData(model)
    sid = model.site(site).id
    posture = np.asarray(q_init if posture is None else posture, dtype=float)
    rng = np.random.default_rng(seed)
    lo, hi = model.jnt_range.T
    start = np.asarray(q_init, dtype=float)
    for _ in range(restarts + 1):
        data.qpos[:] = np.clip(start, lo, hi)
        if _converge(model, data, sid, target_pos, target_quat, posture, damping, iters):
            return data.qpos.copy(), True
        start = rng.uniform(lo, hi)
    return data.qpos.copy(), False
