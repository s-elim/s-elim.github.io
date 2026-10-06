from pathlib import Path
import sys

_code_dir = str(Path(__file__).resolve().parents[1])
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

import pytest
from capstones.a_drawer.env import DrawerEnv
from capstones.a_drawer.policy import ScriptedDrawerPolicy
from mjcourse import capstone
from mjcourse.envs.drawer import DrawerEnv as ReExportedDrawerEnv


@pytest.mark.parametrize("mode", ["ee_delta", "joint_delta", "torque"])
def test_drawer_env_passes_capstone_check(mode: str) -> None:
    results = capstone.check(
        lambda: DrawerEnv(action_mode=mode, max_episode_steps=20),
        object_body="drawer",
    )
    for name, (ok, detail) in results.items():
        assert ok, f"{mode}: check {name} failed: {detail}"


def test_reexported_drawer_env_matches() -> None:
    results = capstone.check(
        lambda: ReExportedDrawerEnv(action_mode="ee_delta", max_episode_steps=20),
        object_body="drawer",
    )
    assert all(ok for ok, _ in results.values()), results


def test_drawer_leak_fails_checks() -> None:
    results = capstone.check(
        lambda: DrawerEnv(
            action_mode="ee_delta",
            max_episode_steps=20,
            extra_observations=("drawer_velocity",),
        ),
        object_body="drawer",
    )
    assert not results["observation sources are sensors"][0]
    assert not results["no privileged quantity leaks"][0]


def test_scripted_policy_short_evaluation() -> None:
    env = DrawerEnv(action_mode="ee_delta", max_episode_steps=100)
    policy = ScriptedDrawerPolicy(ee_step=env.ee_step)
    successes = 0
    seeds = [1001, 1002, 1003, 1004, 1005]
    for seed in seeds:
        obs, info = env.reset(seed=seed)
        policy.reset()
        for _ in range(100):
            obs, reward, terminated, truncated, info = env.step(policy(obs))
            if terminated or truncated:
                break
        if info["success"]:
            successes += 1
    assert successes == len(seeds)


def test_constant_action_fails() -> None:
    env = DrawerEnv(action_mode="ee_delta", max_episode_steps=30)
    obs, info = env.reset(seed=42)
    zero_action = env.action_space.sample() * 0.0
    for _ in range(30):
        obs, reward, terminated, truncated, info = env.step(zero_action)
        if terminated or truncated:
            break
    assert not info["success"]
    assert env.drawer_pos() < 0.03
