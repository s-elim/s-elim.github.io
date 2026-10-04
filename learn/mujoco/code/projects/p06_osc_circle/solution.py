"""Project 6 reference solution: operational-space circle tracking with a null-space elbow posture."""

import mujoco
import numpy as np

RADIUS = 0.10          # m
FREQUENCY = 0.5        # Hz
KP, KD = 400.0, 40.0   # task-space gains on unit mass: natural frequency 20 rad/s, critically damped
K_NULL = 50.0          # null-space posture stiffness, N m/rad per unit joint inertia


def circle(t: float, start: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Desired position, velocity and acceleration on a horizontal circle through `start` at t = 0."""
    w = 2 * np.pi * FREQUENCY
    centre = start - np.array([RADIUS, 0.0, 0.0])
    c, s = np.cos(w * t), np.sin(w * t)
    return (centre + RADIUS * np.array([c, s, 0.0]),
            RADIUS * w * np.array([-s, c, 0.0]),
            -RADIUS * w**2 * np.array([c, s, 0.0]))


def null_space_projector(jac: np.ndarray, mass: np.ndarray) -> np.ndarray:
    """N^T = I - J^T Jbar^T with Jbar = M^-1 J^T Lambda: torques through it cause no task acceleration."""
    m_inv = np.linalg.inv(mass)
    lam = np.linalg.inv(jac @ m_inv @ jac.T)
    return np.eye(mass.shape[0]) - jac.T @ (m_inv @ jac.T @ lam).T


def osc_torque(model, data, site, x_des, v_des, a_des, q_posture, controller=None):
    """Joint torques for position-only OSC of `site`, posture control in the null space.

    Kinematics come from the true state in `data`; the mass matrix and bias forces come from
    `controller` = (model, data) when given, the controller's possibly wrong copy of the robot.
    """
    mujoco.mj_forward(model, data)                    # derived fields are one step stale after mj_step
    sid = model.site(site).id
    jac = np.zeros((3, model.nv))
    mujoco.mj_jacSite(model, data, jac, None, sid)
    jdot = np.zeros((3, model.nv))
    mujoco.mj_jacDot(model, data, jdot, None, data.site_xpos[sid], model.site_bodyid[sid])
    cmodel, cdata = controller if controller is not None else (model, data)
    if controller is not None:
        cdata.qpos[:], cdata.qvel[:] = data.qpos, data.qvel
        mujoco.mj_forward(cmodel, cdata)
    mass = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(cmodel, cdata, mass)
    m_inv = np.linalg.inv(mass)
    lam = np.linalg.inv(jac @ m_inv @ jac.T)          # task-space inertia; fine away from singularities
    x, v = data.site_xpos[sid], jac @ data.qvel
    force = lam @ (a_des + KP * (x_des - x) + KD * (v_des - v) - jdot @ data.qvel)
    tau = jac.T @ force + cdata.qfrc_bias + model.dof_damping * data.qvel
    inertia = np.diag(mass)
    tau += null_space_projector(jac, mass) @ (inertia * (K_NULL * (q_posture - data.qpos) - 2 * np.sqrt(K_NULL) * data.qvel))
    return np.clip(tau, *model.actuator_ctrlrange.T)
