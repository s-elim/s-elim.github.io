"""Project 10 tests: the course's environment checks for each action mode, plus task semantics."""

import mujoco
import numpy as np
import pytest

from mjcourse import capstone, model_path

MODES = ("torque", "joint_target", "ee_delta")
TCP = slice(14, 17)


@pytest.mark.parametrize("mode", MODES)
def test_passes_the_environment_checks(impl, mode):
    results = capstone.check(lambda: impl.PushEnv(action_mode=mode, max_episode_steps=20), object_body="puck")
    failed = {name: detail for name, (ok, detail) in results.items() if not ok}
    assert failed == {}


def test_success_terminates_and_is_not_truncation(impl):
    env = impl.PushEnv(action_mode="ee_delta")
    obs, _ = env.reset(seed=0, options={"puck": [0.6, 0.1], "goal": [0.6, 0.1]})
    np.testing.assert_allclose(obs[17:21], [0.6, 0.1, 0.6, 0.1], atol=1e-6)
    _, reward, terminated, truncated, _ = env.step(np.zeros(2, np.float32))
    assert terminated and not truncated and reward > -0.03


def test_the_first_observation_describes_the_new_episode(impl):
    """Stale observations after reset: reset after an episode must equal reset of a fresh environment."""
    used = impl.PushEnv(action_mode="ee_delta")
    used.reset(seed=1)
    for _ in range(15):
        used.step(np.array([1.0, 0.5], np.float32))
    np.testing.assert_array_equal(used.reset(seed=3)[0], impl.PushEnv(action_mode="ee_delta").reset(seed=3)[0])


@pytest.mark.parametrize("mode", MODES)
def test_tool_position_matches_the_joints(impl, mode):
    """A stale observation (no mj_forward after reset, no mj_kinematics after mj_step) disagrees with
    forward kinematics of the joint angles it reports alongside."""
    model = mujoco.MjModel.from_xml_path(str(model_path("push")))
    data = mujoco.MjData(model)
    env = impl.PushEnv(action_mode=mode)
    obs = env.reset(seed=2)[0]
    rng = np.random.default_rng(0)
    for k in range(6):
        data.qpos[:7] = obs[:7]
        mujoco.mj_kinematics(model, data)
        np.testing.assert_allclose(obs[TCP], data.site("gripper/tcp").xpos, atol=2e-5, err_msg=f"step {k}")
        obs = env.step(rng.uniform(-1, 1, env.action_space.shape).astype(np.float32))[0]


def test_seeds_change_the_layout(impl):
    env = impl.PushEnv()
    layouts = {tuple(np.round(env.reset(seed=s)[0][17:21], 6)) for s in range(5)}
    assert len(layouts) == 5


def test_actions_mean_what_the_docstring_says(impl):
    env = impl.PushEnv(action_mode="ee_delta")
    tcp0 = env.reset(seed=0)[0][TCP]
    for _ in range(10):
        obs = env.step(np.array([1.0, 0.0], np.float32))[0]
    moved = obs[TCP] - tcp0
    assert 0.06 < moved[0] < 0.12 and abs(moved[1]) < 0.01 and abs(moved[2]) < 0.01
    env = impl.PushEnv(action_mode="joint_target")
    q0 = env.reset(seed=0)[0][0]
    for _ in range(5):
        obs = env.step(np.r_[1.0, np.zeros(6)].astype(np.float32))[0]
    assert 0.1 < obs[0] - q0 <= 0.25 + 1e-6
    env = impl.PushEnv(action_mode="torque")
    q0 = env.reset(seed=0)[0][:7]
    for _ in range(20):
        obs = env.step(np.zeros(7, np.float32))[0]
    assert np.max(np.abs(obs[:7] - q0)) < 0.02, "a zero torque action should hold the arm (gravity compensated)"
