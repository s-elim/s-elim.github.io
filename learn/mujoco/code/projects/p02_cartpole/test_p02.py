"""Project 2 tests: linearization, closed-loop stability, limits and robustness."""

import mujoco
import numpy as np

from mjcourse import model_path

Q = np.diag([1.0, 10.0, 0.1, 0.1])
R = np.diag([0.01])


def gains(impl):
    model = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
    a, b = impl.linearize(model, np.zeros(model.nq))
    return model, a, b, impl.lqr_gain(a, b, Q, R)


def test_linearization_predicts_one_step(impl):
    model, a, b, _ = gains(impl)
    data = mujoco.MjData(model)
    dx = np.array([0.01, 0.02, -0.01, 0.03])
    data.qpos[:], data.qvel[:] = dx[:2], dx[2:]
    data.ctrl[0] = 0.5
    mujoco.mj_step(model, data)
    predicted = a @ dx + b @ np.array([0.5])
    np.testing.assert_allclose(np.r_[data.qpos, data.qvel], predicted, atol=2e-5)


def test_closed_loop_eigenvalues_inside_unit_circle(impl):
    _, a, b, k = gains(impl)
    assert np.max(np.abs(np.linalg.eigvals(a - b @ k))) < 1.0


def balance(impl, k, model, angle, seconds=10.0):
    data = mujoco.MjData(model)
    data.qpos[1] = angle
    worst_angle = worst_force = worst_cart = 0.0
    for _ in range(round(seconds / model.opt.timestep)):
        u = impl.controller(k, data)
        data.ctrl[0] = u
        worst_force = max(worst_force, abs(u))
        mujoco.mj_step(model, data)
        worst_angle = max(worst_angle, abs(data.qpos[1]))
        worst_cart = max(worst_cart, abs(data.qpos[0]))
    return data, worst_angle, worst_force, worst_cart


def test_balances_from_tilt(impl):
    model, _, _, k = gains(impl)
    data, worst_angle, worst_force, worst_cart = balance(impl, k, model, 0.15)
    assert worst_angle < 0.2 and worst_cart < 1.4
    assert worst_force <= 20.0                         # within the actuator's ctrlrange
    assert abs(data.qpos[1]) < 1e-3 and abs(data.qpos[0]) < 1e-2


def test_robust_to_heavier_pole(impl):
    model, _, _, k = gains(impl)                       # gains designed for the nominal pole
    model.body_mass[model.body("pole").id] *= 1.5     # the "real" pole is 50% heavier
    mujoco.mj_setConst(model, mujoco.MjData(model))
    _, worst_angle, _, worst_cart = balance(impl, k, model, 0.1)
    assert worst_angle < 0.2 and worst_cart < 1.4
