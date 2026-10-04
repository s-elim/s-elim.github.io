"""Project 10 starter: a Gymnasium environment for the push task, written from scratch on push.xml.

Do not subclass mjcourse.envs. Follow the course's conventions so mjcourse.capstone can check it:
attributes `model`, `data`, `max_episode_steps`, `observation_sources` ({component: real sensor}) and a
method `_get_obs()` that computes the observation from `data`.

    MJC_IMPL=starter pytest projects/p10_gym_env
"""

import gymnasium as gym
import numpy as np


class PushEnv(gym.Env):
    """Push the puck onto the goal with the closed gripper.

    action_mode "torque": 7 joint torques in [-1, 1] times each motor's limit (add gravity compensation).
    action_mode "joint_target": 7 joint-target increments in [-1, 1] times 0.05 rad, tracked inside the step.
    action_mode "ee_delta": 2 tool increments in x, y in [-1, 1] times 0.01 m, tool kept down at a fixed height.
    Observation (float32): joint positions (7), joint velocities (7), tool position (3), puck xy (2), goal xy (2).
    Reward: minus the puck-goal distance. Terminated: the puck within 0.03 m of the goal.
    Truncated: after max_episode_steps steps (0.05 s each). reset(options=) accepts "puck" and "goal" (x, y).
    """

    def __init__(self, action_mode: str = "ee_delta", max_episode_steps: int = 100, frame_skip: int = 25,
                 render_mode: str | None = None):
        raise NotImplementedError

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        raise NotImplementedError

    def step(self, action):
        raise NotImplementedError

    def _get_obs(self) -> np.ndarray:
        raise NotImplementedError
