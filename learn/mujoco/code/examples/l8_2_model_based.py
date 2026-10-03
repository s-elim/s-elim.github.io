"""Lesson 8.2: gravity compensation, feedforward and computed torque on the 7-DOF arm.

INPUT   arm7.xml (torque motors with limits); a controller model whose link masses and
        inertias are scaled by s (s = 1 is the true model), sharing the true armature
PROCESS track q*(t) = home + A sin(2 pi f t) for 4 s with four controllers that use the
        same feedback bandwidth:
          PD                  tau = Kp e + Kd edot
          PD + gravity        ... + qfrc_bias of the controller model (current state)
          PD + feedforward    ... + inverse dynamics of the plan, M(q*) qdd* + c(q*, qd*) + b qd*
          computed torque     tau = M(q) (qdd* + wn^2 e + 2 wn edot) + c(q, qdot) + b qdot
        for s = 1, 0.5 and 1.5, and report RMS and peak joint error after the first second
OUTPUT  a table of tracking errors and torque saturation

Run:  python examples/l8_2_model_based.py
"""

import mujoco
import numpy as np

from mjcourse import model_path

WN, ZETA = 20.0, 1.0                                     # feedback bandwidth (rad/s) and damping ratio
AMP = np.array([0.3, 0.2, 0.3, 0.3, 0.4, 0.3, 0.5])      # rad
FREQ, DURATION, SKIP = 0.5, 4.0, 1.0                     # Hz, s, s (error statistics start after SKIP)


def controller_model(scale: float) -> tuple[mujoco.MjModel, mujoco.MjData]:
    """arm7 with every link's mass and inertia scaled; armature and damping are the motors' and stay."""
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    model.body_mass[1:] *= scale
    model.body_inertia[1:] *= scale
    data = mujoco.MjData(model)
    mujoco.mj_setConst(model, data)
    return model, data


def plan(home: np.ndarray, t: float):
    w = 2 * np.pi * FREQ
    return home + AMP * np.sin(w * t), AMP * w * np.cos(w * t), -AMP * w**2 * np.sin(w * t)


def full_mass(model, data) -> np.ndarray:
    m = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, m)
    return m


def home_inertia(home: np.ndarray) -> np.ndarray:
    """Diagonal of the true mass matrix at home: each joint's inertia with the others held."""
    model, data = controller_model(1.0)
    data.qpos[:] = home
    mujoco.mj_forward(model, data)
    return np.diag(full_mass(model, data))


def track(kind: str, scale: float) -> tuple[float, float, float]:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    home = model.key_qpos[model.key("home").id].copy()
    cmodel, cdata = controller_model(scale)
    m_home = home_inertia(home)
    kp, kd = m_home * WN**2, 2 * ZETA * m_home * WN          # per-joint gains from the home inertia
    damping = model.dof_damping
    data.qpos[:] = home
    data.qvel[:] = plan(home, 0.0)[1]
    limit = model.actuator_ctrlrange[:, 1]
    errors, saturated, h = [], 0, model.opt.timestep
    for k in range(round(DURATION / h)):
        t = k * h
        q_d, qd_d, qdd_d = plan(home, t)
        e, edot = q_d - data.qpos, qd_d - data.qvel
        if kind == "PD":
            tau = kp * e + kd * edot
        elif kind == "PD + gravity":
            cdata.qpos[:], cdata.qvel[:] = data.qpos, data.qvel
            mujoco.mj_forward(cmodel, cdata)
            tau = kp * e + kd * edot + cdata.qfrc_bias
        elif kind == "PD + feedforward":
            cdata.qpos[:], cdata.qvel[:] = q_d, qd_d             # the model evaluated along the plan
            mujoco.mj_forward(cmodel, cdata)
            tau = kp * e + kd * edot + full_mass(cmodel, cdata) @ qdd_d + cdata.qfrc_bias + damping * qd_d
        else:                                                    # computed torque
            cdata.qpos[:], cdata.qvel[:] = data.qpos, data.qvel
            mujoco.mj_forward(cmodel, cdata)
            v = qdd_d + WN**2 * e + 2 * ZETA * WN * edot
            tau = full_mass(cmodel, cdata) @ v + cdata.qfrc_bias + damping * data.qvel
        saturated += int(np.any(np.abs(tau) > limit))
        data.ctrl[:] = tau
        mujoco.mj_step(model, data)
        if t >= SKIP:
            errors.append(plan(home, t + h)[0] - data.qpos)
    err = np.array(errors)
    return float(np.sqrt(np.mean(err**2))), float(np.abs(err).max()), saturated * h


if __name__ == "__main__":
    print(f"track home + A sin(2 pi {FREQ} t), A = {AMP.tolist()} rad, for {DURATION} s; feedback bandwidth "
          f"{WN} rad/s, damping ratio {ZETA}; errors after the first {SKIP} s")
    print(f"  {'controller':<18}{'model scale':>12}{'RMS error (mrad)':>18}{'peak error (mrad)':>19}{'time saturated (s)':>20}")
    for kind in ("PD", "PD + gravity", "PD + feedforward", "computed torque"):
        for scale in ((1.0,) if kind == "PD" else (1.0, 0.5, 1.5)):
            rms, peak, sat = track(kind, scale)
            label = "-" if kind == "PD" else f"{scale:g}"
            print(f"  {kind:<18}{label:>12}{1000 * rms:>18.2f}{1000 * peak:>19.2f}{sat:>20.3f}")
