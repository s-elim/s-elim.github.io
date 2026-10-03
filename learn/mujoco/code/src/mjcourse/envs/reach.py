"""Reach: move arm7's `ee` site to a random target (Lessons 12.1 and 13.x).

Observation (float32, 23): joint positions (7), joint velocities (7), ee position (3,
forward kinematics of the joint positions), target position (3), target minus ee (3).
Action: see mjcourse.envs.arm (torque, joint_delta or ee_delta).
Reward: minus the distance from ee to target (m) per step.
Terminated: the ee is within `success_radius` of the target. Truncated: after
`max_episode_steps` steps (0.05 s each by default).
"""

from __future__ import annotations

import mujoco
import numpy as np
from gymnasium import spaces

from mjcourse.envs.arm import ArmCommand
from mjcourse.envs.base import MujocoEnv

TARGET_LOW, TARGET_HIGH = np.array([0.30, -0.30, 0.15]), np.array([0.60, 0.30, 0.50])


class ReachEnv(MujocoEnv):
    def __init__(self, action_mode: str = "joint_delta", frame_skip: int = 25, max_episode_steps: int = 100,
                 success_radius: float = 0.02, joint_noise: float = 0.1, **kwargs):
        super().__init__("reach", frame_skip, max_episode_steps, **kwargs)
        self.arm = ArmCommand(self.model, self.data, action_mode, "ee")
        self.action_space = self.arm.space
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(23,), dtype=np.float32)
        self.success_radius, self.joint_noise = success_radius, joint_noise

    def _reset_task(self, options: dict) -> None:
        d = self.data
        d.qpos[:7] += self.np_random.uniform(-self.joint_noise, self.joint_noise, 7)
        d.mocap_pos[0] = options.get("target", self.np_random.uniform(TARGET_LOW, TARGET_HIGH))
        mujoco.mj_forward(self.model, d)
        self.arm.reset()

    def _apply_action(self, action: np.ndarray) -> None:
        self.arm.apply(action)

    def _control(self) -> None:
        self.arm.control()

    def _distance(self) -> float:
        return float(np.linalg.norm(self.data.site("ee").xpos - self.data.mocap_pos[0]))

    def _get_obs(self) -> np.ndarray:
        d = self.data
        ee, target = d.site("ee").xpos, d.mocap_pos[0]
        return np.concatenate([d.qpos[:7], d.qvel[:7], ee, target, target - ee]).astype(np.float32)

    def _reward(self, action: np.ndarray) -> float:
        return -self._distance()

    def _terminal(self) -> bool:
        return self._distance() < self.success_radius

    def _get_info(self) -> dict:
        return {"distance": self._distance(), "is_success": self._distance() < self.success_radius}
