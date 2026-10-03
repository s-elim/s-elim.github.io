"""Project 1 tests: your simulator against MuJoCo and against physics."""

import mujoco
import numpy as np
import pytest

from mjcourse import model_path


def mujoco_rollout(theta0, h, steps, integrator):
    model = mujoco.MjModel.from_xml_path(str(model_path("pendulum")))
    model.opt.timestep, model.opt.integrator = h, integrator
    data = mujoco.MjData(model)
    data.qpos[0] = theta0
    out = [(data.qpos[0], data.qvel[0])]
    for _ in range(steps):
        mujoco.mj_step(model, data)
        out.append((data.qpos[0], data.qvel[0]))
    return np.array(out)


def test_acceleration_sign(impl):
    assert impl.acceleration(0.3, 0.0) < 0           # pulled back toward hanging
    assert impl.acceleration(0.0, 0.0) == pytest.approx(0.0)


def test_matches_mujoco_euler(impl):
    ours = impl.simulate(1.0, 0.0, 0.002, 1000, "euler")
    ref = mujoco_rollout(1.0, 0.002, 1000, mujoco.mjtIntegrator.mjINT_EULER)
    np.testing.assert_allclose(ours, ref, atol=1e-9)


def test_matches_mujoco_rk4(impl):
    ours = impl.simulate(1.0, 0.0, 0.002, 1000, "rk4")
    ref = mujoco_rollout(1.0, 0.002, 1000, mujoco.mjtIntegrator.mjINT_RK4)
    np.testing.assert_allclose(ours, ref, atol=1e-8)


def test_rk4_conserves_energy(impl):
    traj = impl.simulate(2.0, 0.0, 0.001, 10_000, "rk4")
    q, w = traj[:, 0], traj[:, 1]
    energy = 0.5 * impl.I_PIVOT * w**2 - impl.M * impl.G * impl.L * np.cos(q)
    assert np.ptp(energy) < 1e-6


def test_small_angle_period(impl):
    traj = impl.simulate(0.01, 0.0, 0.0005, 8000, "rk4")
    crossings = np.where(np.diff(np.sign(traj[:, 0])) != 0)[0]
    period = 2 * np.mean(np.diff(crossings)) * 0.0005
    expected = 2 * np.pi * np.sqrt(impl.I_PIVOT / (impl.M * impl.G * impl.L))
    assert period == pytest.approx(expected, rel=2e-3)


def test_damping_dissipates(impl):
    traj = impl.simulate(1.0, 0.0, 0.002, 5000, "euler", damping=0.2)
    assert abs(traj[-1, 0]) < 0.05
