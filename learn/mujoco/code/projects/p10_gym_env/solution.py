"""Project 10 reference solution: a push environment written from scratch on push.xml."""

from typing import ClassVar

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from mjcourse import kinematics, model_path, spatial

OBSERVATION = (("joint_pos", 7, "joint encoders"), ("joint_vel", 7, "joint encoders, differentiated"),
               ("tcp_pos", 3, "forward kinematics of the joint encoders"), ("puck_xy", 2, "camera tracker"),
               ("goal_xy", 2, "task specification"))
START_TCP = np.array([0.36, 0.0, 0.03])    # m: the closed gripper just above the floor, behind the puck
JOINT_STEP, EE_STEP = 0.05, 0.01           # rad and m per step at action 1
SUCCESS_RADIUS = 0.03                      # m


class PushEnv(gym.Env):
    metadata: ClassVar[dict] = {"render_modes": ["rgb_array"], "render_fps": 20}

    def __init__(self, action_mode: str = "ee_delta", max_episode_steps: int = 100, frame_skip: int = 25,
                 render_mode: str | None = None):
        if action_mode not in ("torque", "joint_target", "ee_delta"):
            raise ValueError(f"unknown action_mode {action_mode!r}")
        self.model = mujoco.MjModel.from_xml_path(str(model_path("push")))
        self.data = mujoco.MjData(self.model)
        self.action_mode, self.max_episode_steps, self.frame_skip = action_mode, max_episode_steps, frame_skip
        self.render_mode, self._renderer = render_mode, None
        self.observation_sources = {name: source for name, _, source in OBSERVATION}
        size = sum(n for _, n, _ in OBSERVATION)
        self.observation_space = spaces.Box(-np.inf, np.inf, (size,), np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, (2 if action_mode == "ee_delta" else 7,), np.float32)
        self._tcp = self.model.site("gripper/tcp").id
        self._puck = self.model.jnt_qposadr[self.model.joint("puck").id]
        self._limits = self.model.jnt_range[:7].copy()
        self._torque_limit = self.model.actuator_ctrlrange[:7, 1].copy()
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.model.key("home").id)
        mujoco.mj_forward(self.model, self.data)
        self._down = spatial.mat_to_quat(self.data.site_xmat[self._tcp].reshape(3, 3))
        result = kinematics.solve_ik(self.model, "gripper/tcp", START_TCP, self._down, q_init=self.data.qpos.copy(),
                                     joints=list(range(7)))
        if not result.success:
            raise RuntimeError("no IK solution for the start pose")
        self._q_start = result.qpos[:7].copy()
        self.data.qpos[:7] = self._q_start
        mujoco.mj_forward(self.model, self.data)
        mass = np.zeros((self.model.nv, self.model.nv))
        mujoco.mj_fullM(self.model, self.data, mass)
        self._kp, self._kd = np.diag(mass)[:7] * 400.0, np.diag(mass)[:7] * 40.0
        self.goal = np.zeros(2)
        self._steps = 0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        options = options or {}
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[:7] = self._q_start
        d.ctrl[7] = 0.0                                      # gripper closed: it is the pusher
        puck = np.asarray(options.get("puck", [0.45 + self.np_random.uniform(-0.03, 0.03), self.np_random.uniform(-0.05, 0.05)]))
        self.goal = np.asarray(options.get("goal", [0.62 + self.np_random.uniform(-0.05, 0.05), self.np_random.uniform(-0.12, 0.12)]),
                               dtype=float)
        d.qpos[self._puck:self._puck + 7] = [*puck, 0.02, 1, 0, 0, 0]
        m.site_pos[m.site("goal").id, :2] = self.goal            # the marker only, for rendering
        self._q_target, self._tcp_target = self._q_start.copy(), START_TCP.copy()
        self._steps = 0
        mujoco.mj_forward(m, d)                                  # the first observation must describe this state
        return self._get_obs(), self._get_info()

    def step(self, action):
        a = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        if self.action_mode == "joint_target":
            self._q_target = np.clip(self._q_target + JOINT_STEP * a, *self._limits.T)
        elif self.action_mode == "ee_delta":
            self._tcp_target[:2] += EE_STEP * a
            self._q_target = self._ik_step(self._tcp_target)
        for _ in range(self.frame_skip):
            mujoco.mj_forward(self.model, self.data)
            bias = self.data.qfrc_bias[:7]
            if self.action_mode == "torque":
                tau = bias + a * self._torque_limit
            else:
                tau = bias + self._kp * (self._q_target - self.data.qpos[:7]) - self._kd * self.data.qvel[:7]
            self.data.ctrl[:7] = np.clip(tau, -self._torque_limit, self._torque_limit)
            mujoco.mj_step(self.model, self.data)
        self._steps += 1
        mujoco.mj_kinematics(self.model, self.data)              # positions are one step stale after mj_step
        distance = self._distance()
        terminated = distance < SUCCESS_RADIUS
        truncated = self._steps >= self.max_episode_steps and not terminated
        return self._get_obs(), -distance, terminated, truncated, self._get_info()

    def _ik_step(self, target):
        """One damped least-squares step from the current joint target toward the tcp target, tool down."""
        sim = mujoco.MjData(self.model)
        sim.qpos[:7] = self._q_target
        mujoco.mj_kinematics(self.model, sim)
        mujoco.mj_comPos(self.model, sim)
        jacp, jacr = np.zeros((3, self.model.nv)), np.zeros((3, self.model.nv))
        mujoco.mj_jacSite(self.model, sim, jacp, jacr, self._tcp)
        current = spatial.mat_to_quat(sim.site_xmat[self._tcp].reshape(3, 3))
        err = np.r_[target - sim.site_xpos[self._tcp], spatial.quat_to_rotvec(spatial.quat_mul(self._down, spatial.quat_conj(current)))]
        jac = np.vstack([jacp, jacr])[:, :7]
        dq = jac.T @ np.linalg.solve(jac @ jac.T + 1e-4 * np.eye(6), err)
        return np.clip(self._q_target + dq, *self._limits.T)

    def _distance(self) -> float:
        return float(np.linalg.norm(self.data.qpos[self._puck:self._puck + 2] - self.goal))

    def _get_obs(self) -> np.ndarray:
        d = self.data
        return np.concatenate([d.qpos[:7], d.qvel[:7], d.site_xpos[self._tcp], d.qpos[self._puck:self._puck + 2],
                               self.goal]).astype(np.float32)

    def _get_info(self) -> dict:
        distance = self._distance()
        return {"distance": distance, "success": distance < SUCCESS_RADIUS}

    def render(self):
        if self.render_mode != "rgb_array":
            return None
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, 240, 320)
        self._renderer.update_scene(self.data, "overview")
        return self._renderer.render().copy()

    def close(self):
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
