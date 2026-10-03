"""Controllers written out in NumPy on top of MuJoCo's dynamics quantities.

Every controller is a plain function of (model, data, ...) returning joint torques
(nv,) or actuator controls (nu,), so it can be called inside any stepping loop:

    data.ctrl[:] = joint_pd_gravity(model, data, q_des, kp, kd)
    mujoco.mj_step(model, data)

They assume torque actuators (`motor`, gear 1) mapped one-to-one onto the first
nu degrees of freedom, as in arm2.xml and arm7.xml. Level 8 derives each one.
"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from mjcourse import spatial
from mjcourse.kinematics import site_jacobian


@dataclass(frozen=True)
class Gains:
    kp: np.ndarray            # N m/rad per joint
    kd: np.ndarray            # N m s/rad per joint

    @staticmethod
    def critical(kp: np.ndarray, inertia: np.ndarray) -> "Gains":
        """Damping for a critically damped response of each joint treated alone: kd = 2 sqrt(kp I)."""
        return Gains(np.asarray(kp, float), 2.0 * np.sqrt(np.asarray(kp, float) * np.asarray(inertia, float)))


def clip_to_ctrlrange(model: mujoco.MjModel, u: np.ndarray) -> np.ndarray:
    lo, hi = model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1]
    limited = model.actuator_ctrllimited.astype(bool)
    return np.where(limited, np.clip(u, lo, hi), u)


def joint_pd(model: mujoco.MjModel, data: mujoco.MjData, q_des: np.ndarray, kp, kd,
             qd_des: np.ndarray | None = None) -> np.ndarray:
    """tau = Kp (q_des - q) - Kd (qdot - qdot_des), no model knowledge."""
    n = model.nu
    qd_des = np.zeros(n) if qd_des is None else qd_des
    tau = kp * (q_des - data.qpos[:n]) + kd * (qd_des - data.qvel[:n])
    return clip_to_ctrlrange(model, tau)


def joint_pd_gravity(model: mujoco.MjModel, data: mujoco.MjData, q_des: np.ndarray, kp, kd,
                     qd_des: np.ndarray | None = None) -> np.ndarray:
    """PD plus compensation of bias forces (gravity, Coriolis, centrifugal) from data.qfrc_bias.

    qfrc_bias is computed by mj_forward / mj_step's velocity stage for the current state.
    Passive forces (joint damping, springs) are not compensated.
    """
    n = model.nu
    qd_des = np.zeros(n) if qd_des is None else qd_des
    tau = kp * (q_des - data.qpos[:n]) + kd * (qd_des - data.qvel[:n]) + data.qfrc_bias[:n]
    return clip_to_ctrlrange(model, tau)


def computed_torque(model: mujoco.MjModel, data: mujoco.MjData, q_des: np.ndarray, qd_des: np.ndarray,
                    qdd_des: np.ndarray, kp, kd) -> np.ndarray:
    """tau = M(q) (qdd_des + Kp e + Kd edot) + c(q, qdot): feedback linearization in joint space."""
    n = model.nu
    m_full = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, m_full)
    e, edot = q_des - data.qpos[:n], qd_des - data.qvel[:n]
    v = qdd_des + kp * e + kd * edot
    tau = m_full[:n, :n] @ v + data.qfrc_bias[:n]
    return clip_to_ctrlrange(model, tau)


def operational_space(model: mujoco.MjModel, data: mujoco.MjData, site: str, x_des: np.ndarray,
                      xd_des: np.ndarray, kp: float, kd: float, xdd_des: np.ndarray | None = None,
                      q_rest: np.ndarray | None = None, k_null: float = 0.0,
                      dyn: tuple[mujoco.MjModel, mujoco.MjData] | None = None) -> np.ndarray:
    """Position-only operational-space control of a site, with null-space posture control.

    F = Lambda (xdd_des + kp e + kd edot - Jdot qdot),  Lambda = (J M^-1 J^T)^-1,
    tau = J^T F + c + b qdot + N^T (k_null (q_rest - q) - 2 sqrt(k_null) qdot),
    N^T = I - J^T Jbar^T with the dynamically consistent inverse Jbar = M^-1 J^T Lambda.
    kp and kd act on a unit mass (Lambda scales them), so kp = wn^2 and kd = 2 wn give
    bandwidth wn. Kinematics (J, Jdot, x) come from `data`, which must be current
    (call mj_forward first). M and c come from `dyn` = (controller model, its data) if
    given, for model-mismatch studies, otherwise from the true model. Orientation is
    left free; Lesson 8.3's impedance controller adds it.
    """
    n = model.nu
    sid = model.site(site).id
    jacp, _ = site_jacobian(model, data, sid)
    j = jacp[:, :n]
    jdot = np.zeros((3, model.nv))
    mujoco.mj_jacDot(model, data, jdot, None, data.site_xpos[sid], model.site_bodyid[sid])
    if dyn is None:
        m_full, bias = np.zeros((model.nv, model.nv)), data.qfrc_bias
        mujoco.mj_fullM(model, data, m_full)
    else:
        cmodel, cdata = dyn
        cdata.qpos[:], cdata.qvel[:] = data.qpos, data.qvel
        mujoco.mj_forward(cmodel, cdata)
        m_full, bias = np.zeros((cmodel.nv, cmodel.nv)), cdata.qfrc_bias
        mujoco.mj_fullM(cmodel, cdata, m_full)
    m_inv = np.linalg.inv(m_full[:n, :n])
    lam = np.linalg.inv(j @ m_inv @ j.T)
    xdd = np.zeros(3) if xdd_des is None else xdd_des
    x, xdot = data.site_xpos[sid], j @ data.qvel[:n]
    force = lam @ (xdd + kp * (x_des - x) + kd * (xd_des - xdot) - jdot[:, :n] @ data.qvel[:n])
    tau = j.T @ force + bias[:n] + model.dof_damping[:n] * data.qvel[:n]
    if k_null > 0 and q_rest is not None:
        j_bar = m_inv @ j.T @ lam                       # dynamically consistent pseudo-inverse
        null = np.eye(n) - j.T @ j_bar.T
        tau = tau + null @ (k_null * (q_rest - data.qpos[:n]) - 2 * np.sqrt(k_null) * data.qvel[:n])
    return clip_to_ctrlrange(model, tau)


def cartesian_impedance(model: mujoco.MjModel, data: mujoco.MjData, site: str, x_des: np.ndarray,
                        quat_des: np.ndarray, k_pos, k_rot: float, *, n: int = 7,
                        xd_des: np.ndarray | None = None, f_ff: np.ndarray | None = None,
                        mass: float = 2.0, inertia: float = 0.05, q_rest: np.ndarray | None = None,
                        k_null: float = 0.0) -> np.ndarray:
    """Cartesian impedance of a site with gravity compensation and no force sensing.

    wrench = [K (x_des - x) + D (xd_des - xdot) + f_ff ; k_rot e_rot - d_rot omega],
    tau = J^T wrench + c + b qdot + N^T (k_null (q_rest - q) - 2 sqrt(k_null) qdot),
    where e_rot is the rotation vector taking the current orientation to quat_des.
    k_pos is a scalar or a 3-vector of stiffnesses along the world axes (N/m); the
    damping D is critical for an effective `mass` (kg), d_rot for an effective
    `inertia` (kg m^2). Held still against an obstacle, the site pushes with
    K (x_des - x) + f_ff, so stiffness sets contact force, not just tracking.
    The arm's dofs are the first n and its torque actuators the first n; data must
    be current (mj_forward). Returns the n torques, clipped to their ctrlrange.
    """
    sid = model.site(site).id
    jacp, jacr = site_jacobian(model, data, sid)
    jac = np.vstack([jacp[:, :n], jacr[:, :n]])
    qvel = data.qvel[:n]
    k = np.broadcast_to(np.asarray(k_pos, float), (3,))
    d = 2.0 * np.sqrt(k * mass)
    d_rot = 2.0 * np.sqrt(k_rot * inertia)
    x, xdot, omega = data.site_xpos[sid], jacp[:, :n] @ qvel, jacr[:, :n] @ qvel
    cur = spatial.mat_to_quat(data.site_xmat[sid].reshape(3, 3))
    e_rot = spatial.quat_to_rotvec(spatial.quat_mul(quat_des, spatial.quat_conj(cur)))
    xd = np.zeros(3) if xd_des is None else xd_des
    force = k * (x_des - x) + d * (xd - xdot) + (0.0 if f_ff is None else f_ff)
    wrench = np.r_[force, k_rot * e_rot - d_rot * omega]
    tau = jac.T @ wrench + data.qfrc_bias[:n] + model.dof_damping[:n] * qvel
    if k_null > 0 and q_rest is not None:
        m_full = np.zeros((model.nv, model.nv))
        mujoco.mj_fullM(model, data, m_full)
        m_inv = np.linalg.inv(m_full[:n, :n])
        lam = np.linalg.inv(jac @ m_inv @ jac.T)
        null = np.eye(n) - jac.T @ (m_inv @ jac.T @ lam).T
        tau = tau + null @ (k_null * (q_rest[:n] - data.qpos[:n]) - 2 * np.sqrt(k_null) * qvel)
    lo, hi = model.actuator_ctrlrange[:n, 0], model.actuator_ctrlrange[:n, 1]
    return np.clip(tau, lo, hi)
