"""Gymnasium environments built on the course's models (Level 12).

    import gymnasium as gym
    import mjcourse.envs                      # registers the ids below
    env = gym.make("mjcourse/Push-v0", action_mode="ee_delta", reward="shaped")
"""

from gymnasium.envs.registration import register

from mjcourse.envs.push import PushEnv
from mjcourse.envs.reach import ReachEnv

# The environments truncate themselves (max_episode_steps is an argument), so no TimeLimit wrapper is added.
register(id="mjcourse/Reach-v0", entry_point="mjcourse.envs.reach:ReachEnv")
register(id="mjcourse/Push-v0", entry_point="mjcourse.envs.push:PushEnv")

__all__ = ["PushEnv", "ReachEnv"]
