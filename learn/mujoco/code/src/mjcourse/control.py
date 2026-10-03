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
                      xd_des: np.ndarray, kp: float, kd: float, q_rest: np.ndarray | None = None,
                      k_null: float = 0.0) -> np.ndarray:
    """Position-only operational-space control of a site, with null-space posture control.

    F = Lambda (kp (x_des - x) + kd (xd_des - xdot)); tau = J^T F + c + N^T tau_null,
    Lambda = (J M^-1 J^T)^-1. Orientation is left free; Level 8.3 adds it.
    """
    n = model.nu
    jacp, _ = site_jacobian(model, data, site)
    j = jacp[:, :n]
    m_full = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, m_full)
    m_inv = np.linalg.inv(m_full[:n, :n])
    lam = np.linalg.inv(j @ m_inv @ j.T + 1e-6 * np.eye(3))
    x = data.site(site).xpos
    xdot = j @ data.qvel[:n]
    force = lam @ (kp * (x_des - x) + kd * (xd_des - xdot))
    tau = j.T @ force + data.qfrc_bias[:n]
    if k_null > 0 and q_rest is not None:
        j_bar = m_inv @ j.T @ lam                       # dynamically consistent pseudo-inverse
        null = np.eye(n) - j.T @ j_bar.T
        tau_null = k_null * (q_rest - data.qpos[:n]) - 2 * np.sqrt(k_null) * data.qvel[:n]
        tau = tau + null @ tau_null
    return clip_to_ctrlrange(model, tau)
