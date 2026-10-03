"""The course's Gymnasium environments pass gymnasium's checker and the checks it does not make
(Lessons 12.1 and 12.2; the Level 12 checkpoint's leakage test is test_push_observations_are_real)."""

import warnings

import pytest
from gymnasium.utils.env_checker import check_env

from mjcourse.envs import PushEnv, ReachEnv
from mjcourse.envs import checks

MODES = ("torque", "joint_delta", "ee_delta")
ENVS = [(cls, mode) for cls in (ReachEnv, PushEnv) for mode in MODES]


@pytest.mark.parametrize("cls,mode", ENVS, ids=lambda x: getattr(x, "__name__", x))
def test_check_env(cls, mode):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                      # infinite observation bounds are deliberate
        check_env(cls(action_mode=mode), skip_render_check=True)


@pytest.mark.parametrize("cls,mode", ENVS, ids=lambda x: getattr(x, "__name__", x))
def test_observations_are_copies(cls, mode):
    assert checks.observations_are_copies(cls(action_mode=mode))


@pytest.mark.parametrize("cls", (ReachEnv, PushEnv))
def test_truncation_is_reported(cls):
    assert checks.truncation_is_reported(cls(action_mode="joint_delta", max_episode_steps=10))


@pytest.mark.parametrize("cls", (ReachEnv, PushEnv))
def test_reproducible(cls):
    assert checks.reproducible(lambda: cls(action_mode="joint_delta"))


def test_push_observations_are_real():
    env = PushEnv(action_mode="ee_delta")
    assert checks.undeclared_sources(env) == []
    assert checks.perturbation_leaks(env) == []


@pytest.mark.parametrize("extra", ("puck_velocity", "contact_force", "puck_friction"))
def test_leaks_are_caught(extra):
    env = PushEnv(action_mode="ee_delta", extra_observations=(extra,))
    assert checks.undeclared_sources(env)
    assert checks.perturbation_leaks(env)


def test_mislabelled_leak_is_caught_by_perturbation():
    env = PushEnv(action_mode="ee_delta", extra_observations=("puck_velocity",))
    env.observation_sources["puck_velocity"] = "camera tracker"     # a false declaration
    assert checks.undeclared_sources(env) == []
    assert "object velocity" in checks.perturbation_leaks(env)
