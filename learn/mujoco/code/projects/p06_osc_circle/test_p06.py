"""Project 6 tests: the reference circle, dynamic consistency, tracking, elbow, model mismatch."""

import mujoco
import numpy as np
import pytest

from mjcourse import model_path

SECONDS, FIRST_CYCLE = 6.0, 2.0


def arm():
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    return model, data


def halved_masses():
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    model.body_mass[1:] *= 0.5
    model.body_inertia[1:] *= 0.5
    data = mujoco.MjData(model)
    mujoco.mj_setConst(model, data)
    return model, data


def track(impl, controller=None):
    model, data = arm()
    start, q0, elbow0 = data.site("ee").xpos.copy(), data.qpos.copy(), data.body("link4").xpos[2]
    h = model.opt.timestep
    errors, elbow = [], []
    for k in range(round(SECONDS / h)):
        x, v, a = impl.circle(k * h, start)
        tau = impl.osc_torque(model, data, "ee", x, v, a, q0, controller)
        assert np.all(np.abs(tau) <= model.actuator_ctrlrange[:, 1] + 1e-9)
        data.ctrl[:] = tau
        mujoco.mj_step(model, data)
        mujoco.mj_kinematics(model, data)          # site_xpos after mj_step alone is the pre-step pose
        errors.append(np.linalg.norm(data.site("ee").xpos - impl.circle((k + 1) * h, start)[0]))
        elbow.append(data.body("link4").xpos[2] - elbow0)
    after_first = round(FIRST_CYCLE / h)
    return np.sqrt(np.mean(np.square(errors[after_first:]))), np.max(np.abs(elbow))


def test_circle(impl):
    start = np.array([0.4, 0.1, 0.6])
    pos, vel, _ = impl.circle(0.0, start)
    np.testing.assert_allclose(pos, start, atol=1e-12)
    assert vel[1] > 0 and abs(vel[2]) < 1e-12
    w = 2 * np.pi * impl.FREQUENCY
    np.testing.assert_allclose(impl.circle(1 / impl.FREQUENCY, start)[0], start, atol=1e-12)
    for t in np.linspace(0, 2, 7):
        pos, vel, acc = impl.circle(t, start)
        centre = start - [impl.RADIUS, 0, 0]
        assert np.linalg.norm(pos - centre) == pytest.approx(impl.RADIUS)
        assert np.linalg.norm(vel) == pytest.approx(impl.RADIUS * w)
        np.testing.assert_allclose(acc, -w**2 * (pos - centre), atol=1e-12)


def test_null_space_projector_is_dynamically_consistent(impl):
    model, data = arm()
    rng = np.random.default_rng(0)
    for _ in range(5):
        data.qpos[:] = rng.uniform(*model.jnt_range.T)
        mujoco.mj_forward(model, data)
        jac = np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, jac, None, model.site("ee").id)
        mass = np.zeros((model.nv, model.nv))
        mujoco.mj_fullM(model, data, mass)
        null = impl.null_space_projector(jac, mass)
        # A torque through N^T must not accelerate the task: J M^-1 N^T = 0.
        np.testing.assert_allclose(jac @ np.linalg.solve(mass, null), 0, atol=1e-9)
        tau0 = rng.normal(size=model.nv)
        np.testing.assert_allclose(null @ (null @ tau0), null @ tau0, atol=1e-9)   # a projector


def test_tracks_the_circle_with_the_elbow_up(impl):
    rms, elbow = track(impl)
    assert rms < 5e-3, f"RMS error {rms * 1000:.2f} mm after the first cycle"
    assert elbow < 0.02, f"elbow moved {elbow * 100:.1f} cm"


def test_controller_uses_its_own_model(impl):
    exact, _ = track(impl)
    mismatched, _ = track(impl, halved_masses())
    assert np.isfinite(mismatched)
    assert mismatched > exact + 1e-3, "halving the controller's masses changed nothing: is `controller` used?"
