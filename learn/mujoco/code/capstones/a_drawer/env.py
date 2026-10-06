from __future__ import annotations

from typing import ClassVar
import gymnasium as gym
from gymnasium import spaces
import mujoco
import numpy as np

from mjcourse import control, spatial
from mjcourse.envs.base import MujocoEnv
from mjcourse.paths import model_path

OBSERVATION = (
    ("joint_pos", 7, "joint encoders"),
    ("joint_vel", 7, "joint encoders, differentiated"),
    ("tcp_pos", 3, "forward kinematics of the joint encoders"),
    ("gripper_pos", 1, "joint encoders"),
    ("handle_pos", 3, "camera tracker"),
    ("drawer_pos", 1, "joint encoders"),
    ("target_open", 1, "task specification"),
)

PRIVILEGED = {
    "drawer_velocity": (1, "simulator state"),
    "drawer_mass": (1, "simulator state"),
    "drawer_friction": (1, "model parameter"),
}

MODES = ("torque", "joint_delta", "ee_delta")
REWARDS = ("dense", "shaped", "sparse")

START_Q = np.array([-1.37, 1.8, 1.0445, 2.0603, -0.7601, -0.881, 0.4346], dtype=np.float64)
START_TCP = np.array([0.55, -0.14, 0.10], dtype=np.float64)
R_FRONT_BAR = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], dtype=np.float64)


class DrawerEnv(MujocoEnv):
    metadata: ClassVar[dict] = {"render_modes": ["rgb_array"], "render_fps": 20}

    def __init__(
        self,
        action_mode: str = "ee_delta",
        reward: str = "shaped",
        frame_skip: int = 25,
        max_episode_steps: int = 100,
        target_open: float = 0.12,
        success_threshold: float = 0.10,
        include_gripper: bool = True,
        extra_observations: tuple[str, ...] = (),
        terminate_on_success: bool = True,
        render_mode: str | None = None,
        camera: str | int = "overview",
        width: int = 320,
        height: int = 240,
    ) -> None:
        super().__init__(
            model="articulated",
            frame_skip=frame_skip,
            max_episode_steps=max_episode_steps,
            keyframe="home",
            render_mode=render_mode,
            camera=camera,
            width=width,
            height=height,
        )
        if action_mode not in MODES:
            raise ValueError(f"action_mode must be one of {MODES}")
        if reward not in REWARDS:
            raise ValueError(f"reward must be one of {REWARDS}")

        self.action_mode = action_mode
        self.reward_kind = reward
        self.target_open = float(target_open)
        self.success_threshold = float(success_threshold)
        self.include_gripper = bool(include_gripper)
        self.extra = tuple(extra_observations)
        self.terminate_on_success = bool(terminate_on_success)

        self._q_start = START_Q.copy()
        self._tcp_start = START_TCP.copy()
        self.quat_front = spatial.mat_to_quat(R_FRONT_BAR)

        self.lo = self.model.jnt_range[:7, 0].copy()
        self.hi = self.model.jnt_range[:7, 1].copy()
        self.torque_limit = self.model.actuator_ctrlrange[:7, 1].copy()

        self.ee_step = 0.015
        self.joint_step = 0.05
        self.ee_low = np.array([0.45, -0.30, 0.02], dtype=np.float64)
        self.ee_high = np.array([0.75, 0.10, 0.35], dtype=np.float64)

        if action_mode == "ee_delta":
            dim = 4 if self.include_gripper else 3
        elif action_mode == "joint_delta":
            dim = 8 if self.include_gripper else 7
        else:
            dim = 8 if self.include_gripper else 7
        self.action_space = spaces.Box(-1.0, 1.0, shape=(dim,), dtype=np.float32)

        self.observation_sources = {name: src for name, _, src in OBSERVATION}
        self.observation_sources |= {name: PRIVILEGED[name][1] for name in self.extra}
        obs_dim = sum(n for _, n, _ in OBSERVATION) + sum(PRIVILEGED[name][0] for name in self.extra)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(obs_dim,), dtype=np.float32)

        self._drawer_body = self.model.body("drawer").id
        self._drawer_geom = self.model.geom("drawer").id
        self._drawer_joint = self.model.joint("drawer").id
        self._drawer_qposadr = self.model.jnt_qposadr[self._drawer_joint]
        self._tcp_site = self.model.site("gripper/tcp").id
        self._handle_site = self.model.site("drawer_handle").id

        mass = np.zeros((self.model.nv, self.model.nv), dtype=np.float64)
        mujoco.mj_fullM(self.model, self.data, mass)
        wn = 20.0
        self.kp = np.diag(mass)[:7] * (wn**2)
        self.kd = 2.0 * np.diag(mass)[:7] * wn

        self.x_target = self._tcp_start.copy()
        self.q_target = self._q_start.copy()
        self.torque_action = np.zeros(7, dtype=np.float64)
        self.grip_target = 0.04

    def _reset_task(self, options: dict) -> None:
        d = self.data
        rng = self.np_random

        q_noise = options.get("q_noise", 0.01)
        if q_noise > 0.0:
            d.qpos[:7] = self._q_start + rng.uniform(-q_noise, q_noise, size=7)
        else:
            d.qpos[:7] = self._q_start.copy()

        d.qpos[7:9] = 0.04
        d.ctrl[7] = 0.04
        self.grip_target = 0.04

        drawer_init = float(options.get("drawer_init", rng.uniform(0.0, 0.015)))
        d.qpos[self._drawer_qposadr] = drawer_init
        d.qpos[self.model.jnt_qposadr[self.model.joint("door").id]] = 0.0

        d.qvel[:] = 0.0

        mujoco.mj_forward(self.model, d)

        self.x_target = d.site("gripper/tcp").xpos.copy()
        self.q_target = d.qpos[:7].copy()
        self.torque_action = np.zeros(7, dtype=np.float64)

    def _apply_action(self, action: np.ndarray) -> None:
        act = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        if self.action_mode == "ee_delta":
            delta = act[:3] * self.ee_step
            self.x_target = np.clip(self.x_target + delta, self.ee_low, self.ee_high)
            if self.include_gripper and len(act) >= 4:
                self.grip_target = float(np.clip(0.02 * (1.0 + act[3]), 0.0, 0.04))
        elif self.action_mode == "joint_delta":
            delta = act[:7] * self.joint_step
            self.q_target = np.clip(self.q_target + delta, self.lo, self.hi)
            if self.include_gripper and len(act) >= 8:
                self.grip_target = float(np.clip(0.02 * (1.0 + act[7]), 0.0, 0.04))
        else:
            self.torque_action = act[:7].copy()
            if self.include_gripper and len(act) >= 8:
                self.grip_target = float(np.clip(0.02 * (1.0 + act[7]), 0.0, 0.04))

    def _control(self) -> None:
        d = self.data
        mujoco.mj_forward(self.model, d)
        if self.action_mode == "torque":
            tau = d.qfrc_bias[:7] + self.torque_action * self.torque_limit
        elif self.action_mode == "joint_delta":
            tau = self.kp * (self.q_target - d.qpos[:7]) - self.kd * d.qvel[:7] + d.qfrc_bias[:7]
        else:
            tau = control.cartesian_impedance(
                self.model,
                d,
                "gripper/tcp",
                self.x_target,
                self.quat_front,
                2000.0,
                300.0,
                q_rest=self._q_start,
                k_null=20.0,
            )
        d.ctrl[:7] = np.clip(tau, -self.torque_limit, self.torque_limit)
        d.ctrl[7] = self.grip_target

    def drawer_pos(self) -> float:
        return float(self.data.qpos[self._drawer_qposadr])

    def tcp_pos(self) -> np.ndarray:
        return self.data.site_xpos[self._tcp_site].copy()

    def handle_pos(self) -> np.ndarray:
        return self.data.site_xpos[self._handle_site].copy()

    def _get_obs(self) -> np.ndarray:
        d = self.data
        parts = [
            d.qpos[:7].astype(np.float32),
            d.qvel[:7].astype(np.float32),
            self.tcp_pos().astype(np.float32),
            np.array([d.qpos[7]], dtype=np.float32),
            self.handle_pos().astype(np.float32),
            np.array([self.drawer_pos()], dtype=np.float32),
            np.array([self.target_open], dtype=np.float32),
        ]
        for name in self.extra:
            if name == "drawer_velocity":
                dof = self.model.body_dofadr[self._drawer_body]
                parts.append(d.qvel[dof : dof + 1].astype(np.float32))
            elif name == "drawer_mass":
                parts.append(np.array([self.model.body_mass[self._drawer_body]], dtype=np.float32))
            elif name == "drawer_friction":
                parts.append(np.array([self.model.geom_friction[self._drawer_geom, 0]], dtype=np.float32))
        return np.concatenate(parts).astype(np.float32)

    def _terminal(self) -> bool:
        if not self.terminate_on_success:
            return False
        return self.drawer_pos() >= self.success_threshold

    def _reward(self, action: np.ndarray) -> float:
        open_pos = self.drawer_pos()
        if self.reward_kind == "sparse":
            return 1.0 if open_pos >= self.success_threshold else 0.0

        dist = float(np.linalg.norm(self.tcp_pos() - self.handle_pos()))
        reach_reward = -dist
        pull_reward = 10.0 * open_pos
        ctrl_penalty = -1e-3 * float(np.sum(action**2))
        success_bonus = 5.0 if open_pos >= self.success_threshold else 0.0

        if self.reward_kind == "dense":
            return reach_reward + pull_reward + ctrl_penalty
        return reach_reward + pull_reward + ctrl_penalty + success_bonus

    def _get_info(self) -> dict:
        pos = self.drawer_pos()
        success = pos >= self.success_threshold
        dist = float(np.linalg.norm(self.tcp_pos() - self.handle_pos()))
        return {
            "drawer_pos": pos,
            "success": success,
            "dist_to_handle": dist,
            "steps": self._steps,
        }
