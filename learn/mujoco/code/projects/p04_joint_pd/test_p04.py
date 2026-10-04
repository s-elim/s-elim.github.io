"""Project 4 tests: step response with compensation, steady error without, torque limits."""

import mujoco
import numpy as np

from mjcourse import model_path

STEP = 0.3


def arm_at_home():
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    return model, data


def step_response(impl, compensate, seconds):
    model, data = arm_at_home()
    kp, kd = impl.design_gains(model, data, impl.OMEGA, impl.ZETA)
    q0 = data.qpos.copy()
    q_des = q0 + STEP
    lo, hi = model.actuator_ctrlrange.T
    path = []
    for _ in range(round(seconds / model.opt.timestep)):
        tau = impl.pd_torque(model, data, q_des, kp, kd, compensate)
        assert np.all(tau >= lo) and np.all(tau <= hi), "torque outside ctrlrange"
        data.ctrl[:] = tau
        mujoco.mj_step(model, data)
        path.append(data.qpos.copy())
    return model, kp, q0, q_des, np.array(path)


def test_gains_are_positive_and_damped(impl):
    model, data = arm_at_home()
    kp, kd = impl.design_gains(model, data, impl.OMEGA, impl.ZETA)
    assert kp.shape == kd.shape == (model.nv,)
    assert np.all(kp > 0) and np.all(kd + model.dof_damping > 0)


def test_compensated_step_settles_fast_without_overshoot(impl):
    model, _, q0, q_des, path = step_response(impl, compensate=True, seconds=1.0)
    overshoot = np.max((path - q0) / STEP, axis=0) - 1
    assert np.all(overshoot < 0.05), f"overshoot {overshoot.round(3)}"
    settled_from = round(0.5 / model.opt.timestep)
    assert np.all(np.abs(path[settled_from:] - q_des) < 0.01 * STEP), "not within 1% after 0.5 s"


def test_steady_error_without_compensation_is_predicted(impl):
    model, kp, _, q_des, path = step_response(impl, compensate=False, seconds=6.0)
    measured = q_des - path[-1]
    predicted = impl.predicted_steady_error(model, q_des, kp)
    loaded = np.abs(measured) > 1e-3                   # the roll joints carry no load here
    assert loaded.sum() >= 3
    np.testing.assert_allclose(predicted[loaded], measured[loaded], rtol=0.10)


def test_compensation_removes_the_steady_error(impl):
    _, _, _, q_des, path = step_response(impl, compensate=True, seconds=2.0)
    assert np.max(np.abs(q_des - path[-1])) < 1e-4
