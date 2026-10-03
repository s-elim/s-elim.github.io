"""Kinematics on top of MuJoCo: Jacobians, finite-difference checks, inverse kinematics.

Shapes follow MuJoCo: a translational or rotational Jacobian is (3, nv), mapping
generalized velocities qvel (nv,) to a world-frame linear or angular velocity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import mujoco
import numpy as np

from mjcourse import spatial


def site_jacobian(model: mujoco.MjModel, data: mujoco.MjData, site: int | str) -> tuple[np.ndarray, np.ndarray]:
    """World-frame translational and rotational Jacobians (each 3 x nv) of a site.

    Valid for the configuration last processed by mj_forward or mj_kinematics + mj_comPos.
    """
    sid = model.site(site).id
    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))
    mujoco.mj_jacSite(model, data, jacp, jacr, sid)
    return jacp, jacr


def fd_site_jacobian(model: mujoco.MjModel, data: mujoco.MjData, site: int | str,
                     eps: float = 1e-6) -> tuple[np.ndarray, np.ndarray]:
    """Central finite-difference Jacobians of a site's position and orientation.

    Perturbs each degree of freedom with mj_integratePos (so free and ball joints
    are handled on the manifold) and differences the site pose. Leaves `data`
    as it found it (position-dependent quantities recomputed).
    """
    sid = model.site(site).id
    q0 = data.qpos.copy()
    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))
    scratch = mujoco.MjData(model)
    for k in range(model.nv):
        poses = []
        for sign in (+1.0, -1.0):
            dq = np.zeros(model.nv)
            dq[k] = sign * eps
            scratch.qpos[:] = q0
            mujoco.mj_integratePos(model, scratch.qpos, dq, 1.0)
            mujoco.mj_kinematics(model, scratch)
            poses.append((scratch.site_xpos[sid].copy(), scratch.site_xmat[sid].reshape(3, 3).copy()))
        (p_plus, r_plus), (p_minus, r_minus) = poses
        jacp[:, k] = (p_plus - p_minus) / (2 * eps)
        # world-frame angular change: log(R_minus^T R_plus) expressed in world = R log(...)
        rel = spatial.mat_to_quat(r_minus.T @ r_plus)
        jacr[:, k] = r_minus @ spatial.quat_to_rotvec(rel) / (2 * eps)
    return jacp, jacr


@dataclass(frozen=True)
class IKResult:
    qpos: np.ndarray
    success: bool
    iterations: int
    pos_error: float              # m
    rot_error: float              # rad
    history: list[float] = field(default_factory=list)
    max_step: float = 0.0         # largest joint step before step_limit clipped it (rad)


def solve_ik(model: mujoco.MjModel, site: str, target_pos: np.ndarray,
             target_quat: np.ndarray | None = None, q_init: np.ndarray | None = None,
             damping: float = 1e-2, max_iters: int = 200, tol_pos: float = 1e-4, tol_rot: float = 1e-3,
             step_limit: float = 0.2, joints: list[int] | None = None, nullspace_gain: float = 0.0,
             q_rest: np.ndarray | None = None, projector: str = "exact") -> IKResult:
    """Damped-least-squares inverse kinematics for one site.

    Solves for qpos so that the site reaches target_pos (and target_quat if given),
    iterating dq = J^T (J J^T + damping^2 I)^-1 e, clamping joints to their ranges.
    `joints` restricts the solve to the given dof indices (default: all dofs of
    hinge and slide joints). A null-space term pulls redundant arms toward q_rest,
    projected with the exact null-space projector; projector="damped" builds it from
    the damped inverse instead, which leaks into the task (kept to demonstrate that).
    Works on a private MjData; `model` is not modified.
    """
    data = mujoco.MjData(model)
    if q_init is not None:
        data.qpos[:] = q_init
    dofs = np.array(joints if joints is not None else
                    [model.jnt_dofadr[j] for j in range(model.njnt) if model.jnt_type[j] in (2, 3)])
    qadr = np.array([model.jnt_qposadr[model.dof_jntid[d]] for d in dofs])
    lo = np.array([model.jnt_range[model.dof_jntid[d]][0] if model.jnt_limited[model.dof_jntid[d]] else -np.inf for d in dofs])
    hi = np.array([model.jnt_range[model.dof_jntid[d]][1] if model.jnt_limited[model.dof_jntid[d]] else np.inf for d in dofs])
    sid = model.site(site).id
    history: list[float] = []
    pos_err = rot_err = np.inf
    max_step = 0.0
    for it in range(1, max_iters + 1):
        mujoco.mj_kinematics(model, data)
        mujoco.mj_comPos(model, data)
        e_pos = target_pos - data.site_xpos[sid]
        jacp, jacr = site_jacobian(model, data, sid)
        if target_quat is not None:
            cur = spatial.mat_to_quat(data.site_xmat[sid].reshape(3, 3))
            e_rot = spatial.quat_to_rotvec(spatial.quat_mul(target_quat, spatial.quat_conj(cur)))  # world frame
            err = np.r_[e_pos, e_rot]
            jac = np.vstack([jacp, jacr])[:, dofs]
            rot_err = float(np.linalg.norm(e_rot))
        else:
            err, jac, rot_err = e_pos, jacp[:, dofs], 0.0
        pos_err = float(np.linalg.norm(e_pos))
        history.append(pos_err)
        if pos_err < tol_pos and rot_err < tol_rot:
            return IKResult(data.qpos.copy(), True, it, pos_err, rot_err, history, max_step)
        jjt = jac @ jac.T + damping**2 * np.eye(jac.shape[0])
        dq = jac.T @ np.linalg.solve(jjt, err)
        if nullspace_gain > 0 and q_rest is not None:
            # Exact projector onto the null space of J, I - V_r V_r^T. Building it from the
            # damped inverse instead leaks the posture term into the task (Lesson 6.3).
            if projector == "damped":
                null = np.eye(len(dofs)) - jac.T @ np.linalg.solve(jjt, jac)
            else:
                _, sv, vt = np.linalg.svd(jac)
                rank = int(np.sum(sv > 1e-6 * sv[0]))
                null = np.eye(len(dofs)) - vt[:rank].T @ vt[:rank]
            dq += null @ (nullspace_gain * (q_rest[qadr] - data.qpos[qadr]))
        norm = np.linalg.norm(dq)
        max_step = max(max_step, float(norm))
        if norm > step_limit:
            dq *= step_limit / norm
        data.qpos[qadr] = np.clip(data.qpos[qadr] + dq, lo, hi)
    return IKResult(data.qpos.copy(), False, max_iters, pos_err, rot_err, history, max_step)


def solve_ik_restarts(model: mujoco.MjModel, site: str, target_pos: np.ndarray,
                      target_quat: np.ndarray | None = None, q_init: np.ndarray | None = None,
                      restarts: int = 10, seed: int = 0, **kwargs) -> tuple[IKResult, int]:
    """solve_ik from q_init, then from up to `restarts` random configurations inside the
    joint ranges. Returns the first success (or the last attempt) and the number of
    restarts used. Clamping at joint limits creates local minima; restarts escape them.
    """
    result = solve_ik(model, site, target_pos, target_quat, q_init=q_init, **kwargs)
    rng = np.random.default_rng(seed)
    lo, hi = model.jnt_range[:, 0], model.jnt_range[:, 1]
    used = 0
    while not result.success and used < restarts:
        used += 1
        q0 = np.zeros(model.nq) if q_init is None else np.array(q_init, dtype=float)
        limited = model.jnt_limited.astype(bool)
        for j in np.flatnonzero(limited & np.isin(model.jnt_type, (2, 3))):
            q0[model.jnt_qposadr[j]] = rng.uniform(lo[j], hi[j])
        result = solve_ik(model, site, target_pos, target_quat, q_init=q0, **kwargs)
    return result, used


def manipulability(jac: np.ndarray) -> float:
    """Yoshikawa's manipulability sqrt(det(J J^T)); zero at singular configurations."""
    return float(np.sqrt(max(np.linalg.det(jac @ jac.T), 0.0)))
