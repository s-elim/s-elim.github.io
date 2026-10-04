"""Project 3 tests: a clean compile, the required parts, a stiff enough hold, contact-free poses, units."""

import re

import mujoco
import numpy as np
import pytest

HINGE, SLIDE = mujoco.mjtJoint.mjJNT_HINGE, mujoco.mjtJoint.mjJNT_SLIDE


def compile_capturing_warnings(xml):
    warnings = []
    previous = mujoco.get_mju_user_warning()
    mujoco.set_mju_user_warning(warnings.append)
    try:
        model = mujoco.MjModel.from_xml_string(xml)
    finally:
        mujoco.set_mju_user_warning(previous)
    return model, warnings


@pytest.fixture
def model(impl):
    return compile_capturing_warnings(impl.model_xml())[0]


def test_compiles_without_warnings(impl):
    _, warnings = compile_capturing_warnings(impl.model_xml())
    assert warnings == []


def test_required_parts(model):
    hinges = [j for j in range(model.njnt) if model.jnt_type[j] == HINGE]
    slides = [j for j in range(model.njnt) if model.jnt_type[j] == SLIDE]
    assert len(hinges) == 3 and len(slides) == 2, "three hinges for the arm, two slides for the fingers"
    assert all(model.jnt_limited[j] for j in hinges + slides), "every joint needs a range"
    # Ranges in radians: a range written in degrees under angle="radian" spans tens of radians.
    assert np.all(np.abs(model.jnt_range[hinges]) <= 2 * np.pi)
    assert model.nu >= 4
    for a in range(model.nu):                                   # position servos: force = kp (ctrl - q) - kv qdot
        assert model.actuator_biastype[a] == mujoco.mjtBias.mjBIAS_AFFINE
        assert model.actuator_biasprm[a, 1] == pytest.approx(-model.actuator_gainprm[a, 0])
        assert model.actuator_ctrllimited[a]
    assert model.camera("workspace").id >= 0
    assert model.key("home").id >= 0


def test_holds_keyframe_for_five_seconds(model):
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    arm = [model.jnt_qposadr[j] for j in range(model.njnt) if model.jnt_type[j] == HINGE]
    start = data.qpos[arm].copy()
    worst = 0.0
    for _ in range(round(5.0 / model.opt.timestep)):
        mujoco.mj_step(model, data)
        worst = max(worst, np.max(np.abs(data.qpos[arm] - start)))
    assert np.degrees(worst) < 1.0
    assert all(w.number == 0 for w in data.warning), "MuJoCo raised a runtime warning"


def test_named_poses_are_contact_free(impl, model):
    assert len(impl.POSES) >= 3
    finger = [model.jnt_qposadr[j] for j in range(model.njnt) if model.jnt_type[j] == SLIDE]
    closed = model.jnt_range[[j for j in range(model.njnt) if model.jnt_type[j] == SLIDE], 0]
    assert any(np.allclose(q[finger], closed, atol=1e-4) for q in impl.POSES.values()), \
        "one pose must have the gripper fully closed"
    for name, qpos in impl.POSES.items():
        data = mujoco.MjData(model)
        data.qpos[:] = qpos
        lo, hi = model.jnt_range[:, 0], model.jnt_range[:, 1]
        assert np.all(qpos >= lo - 1e-9) and np.all(qpos <= hi + 1e-9), f"{name} is outside the joint limits"
        mujoco.mj_forward(model, data)
        pairs = [(model.geom(c.geom1).name, model.geom(c.geom2).name) for c in data.contact[:data.ncon]]
        assert data.ncon == 0, f"{name}: contacts {pairs}"


def test_gripper_follows_its_command(model):
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    grip = next(a for a in range(model.nu) if model.jnt_type[model.actuator_trnid[a, 0]] == SLIDE)
    finger = model.jnt_qposadr[model.actuator_trnid[grip, 0]]
    for target in model.actuator_ctrlrange[grip]:
        data.ctrl[grip] = target
        for _ in range(round(1.0 / model.opt.timestep)):
            mujoco.mj_step(model, data)
        assert data.qpos[finger] == pytest.approx(target, abs=2e-3)


NUMERIC_ATTRIBUTE = re.compile(r'\b\w+="\s*-?[\d.]+(?:[eE][-+]?\d+)?(?:\s+-?[\d.]+(?:[eE][-+]?\d+)?)*\s*"')


def test_every_number_has_a_unit_comment(impl):
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group().count("\n"), impl.model_xml(), flags=re.DOTALL)
    lines_with_comments = {i for i, line in enumerate(impl.model_xml().splitlines()) if "<!--" in line}
    missing = [line.strip() for i, line in enumerate(text.splitlines())
               if NUMERIC_ATTRIBUTE.search(line) and i not in lines_with_comments]
    assert missing == [], f"lines without a unit comment: {missing[:3]}"
