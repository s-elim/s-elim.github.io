"""Every model in the library compiles, holds still where it should, and the
generated models match their sources."""

from pathlib import Path

import mujoco
import numpy as np
import pytest

from mjcourse import MODELS_DIR, model_builder

MODELS = sorted(p.stem for p in MODELS_DIR.glob("*.xml") if p.stem != "gripper" and not p.stem.startswith("broken_"))
# Scenes that attach an arm inherit its keyframes; "home" is keyframe 1 there.
HOME_KEY = {"arm7": 1, "arm7_gripper": 1, "arm7_peg": 1, "reach": 1, "push": 1, "pick_place": 1,
            "peg_insert": 1, "articulated": 1, "bimanual": 0}


@pytest.mark.parametrize("name", MODELS)
def test_compiles_and_steps(name):
    m = mujoco.MjModel.from_xml_path(str(MODELS_DIR / f"{name}.xml"))
    d = mujoco.MjData(m)
    if name in HOME_KEY:
        mujoco.mj_resetDataKeyframe(m, d, HOME_KEY[name])
    for _ in range(200):
        mujoco.mj_step(m, d)
    assert np.all(np.isfinite(d.qpos)), f"{name}: non-finite state after 200 steps"
    bad = [w.number for w in d.warning]
    assert bad[mujoco.mjtWarning.mjWARN_BADQACC] == 0, f"{name}: unstable (bad qacc)"


@pytest.mark.parametrize("name", [n for n in HOME_KEY if n != "bimanual"])
def test_no_contacts_involving_robot_at_home(name):
    m = mujoco.MjModel.from_xml_path(str(MODELS_DIR / f"{name}.xml"))
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, HOME_KEY[name])
    mujoco.mj_forward(m, d)
    robot_bodies = {m.body(f"link{i}").id for i in range(8)}
    for c in d.contact[: d.ncon]:
        b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
        assert b1 not in robot_bodies and b2 not in robot_bodies, (
            f"{name}: robot in contact at home ({m.geom(c.geom1).name}, {m.geom(c.geom2).name})")


def test_generated_models_are_current(tmp_path: Path):
    """Fails if someone edited arm7.xml or gripper.xml without regenerating."""
    fresh = model_builder.write_all(tmp_path)
    for name, xml in fresh.items():
        committed = (MODELS_DIR / name).read_text()
        assert committed == xml, f"{name} is stale: run `python -m mjcourse.model_builder`"


def test_home_pose_points_tool_down():
    m = mujoco.MjModel.from_xml_path(str(MODELS_DIR / "arm7.xml"))
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 1)
    mujoco.mj_forward(m, d)
    z_axis = d.site("ee").xmat.reshape(3, 3)[:, 2]
    np.testing.assert_allclose(z_axis, [0, 0, -1], atol=1e-4)
