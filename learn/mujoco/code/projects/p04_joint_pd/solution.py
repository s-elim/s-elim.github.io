"""Project 4 reference solution: PD and PD + gravity compensation with per-joint gains."""

import mujoco
import numpy as np

OMEGA = 18.0
ZETA = 1.0


def design_gains(model, data, omega, zeta):
    mujoco.mj_forward(model, data)
    mass = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, mass)
    inertia = np.diag(mass)                           # includes armature
    return inertia * omega**2, 2 * zeta * inertia * omega - model.dof_damping


def pd_torque(model, data, q_des, kp, kd, compensate):
    mujoco.mj_forward(model, data)                    # derived fields are one step stale after mj_step
    tau = kp * (q_des - data.qpos) - kd * data.qvel
    if compensate:
        tau = tau + data.qfrc_bias
    lo, hi = model.actuator_ctrlrange.T
    return np.clip(tau, lo, hi)


def _bias(model, q):
    data = mujoco.MjData(model)
    data.qpos[:] = q
    mujoco.mj_forward(model, data)
    return data.qfrc_bias.copy()                      # at rest this is the load: gravity only


def predicted_steady_error(model, q_des, kp):
    # At rest kp (q_des - q) = load(q), with q = q_des - e. The load must be taken at the sagged pose:
    # iterate the fixed point instead of evaluating it once at q_des.
    error = _bias(model, q_des) / kp
    for _ in range(100):
        new = _bias(model, q_des - error) / kp
        if np.max(np.abs(new - error)) < 1e-12:
            break
        error = new
    return new
