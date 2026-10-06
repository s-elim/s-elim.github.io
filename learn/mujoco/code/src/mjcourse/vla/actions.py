from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from mjcourse import kinematics, spatial
from mjcourse.paths import model_path

REPRESENTATIONS = ("torque", "joint_position", "joint_delta", "joint_velocity", "cartesian_delta", "cartesian_pose")
FRAME_SKIP, STEPS, MOVE_STEPS = 25, 40, 30            # 20 Hz policy, 2 s episodes, 1.5 s reference motion
BOX_LOW, BOX_HIGH = np.array([0.35, -0.25, 0.15]), np.array([0.60, 0.25, 0.45])
YAW_RANGE = 0.6
JOINT_STEP, JOINT_SPEED, EE_STEP, YAW_STEP = 0.05, 1.0, 0.02, 0.1
SUCCESS_POS, SUCCESS_YAW = 0.015, 0.1
OBS_DIM = 24


@dataclass(frozen=True)
class Target:
    pos: np.ndarray
    yaw: float


def sample_target(rng: np.random.Generator, low=BOX_LOW, high=BOX_HIGH) -> Target:
    return Target(rng.uniform(low, high), float(rng.uniform(-YAW_RANGE, YAW_RANGE)))


def _yaw_of(mat: np.ndarray) -> float:
    return float(np.arctan2(mat[1, 0], mat[0, 0]))


class ArmReach:
    def __init__(self, representation: str, payload: float = 0.0, frame_skip: int = FRAME_SKIP):
        if representation not in REPRESENTATIONS:
            raise ValueError(representation)
        self.rep, self.frame_skip = representation, frame_skip
        spec = mujoco.MjSpec.from_file(str(model_path("arm7")))
        if payload:
            body = spec.body("link7")
            body.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.03, 0, 0], pos=[0, 0, 0.1], mass=payload,
                          contype=0, conaffinity=0, rgba=[0.9, 0.6, 0.1, 1])
        self.model = spec.compile()
        self.data = mujoco.MjData(self.model)
        # Gravity compensation uses the nominal arm, as a real controller with a fixed model would: a payload
        # is something the controller does not know about.
        self.nominal = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
        self.nominal_data = mujoco.MjData(self.nominal)
        m = self.model
        self.site = m.site("ee").id
        self.lo, self.hi = m.jnt_range[:7].T
        self.limit = m.actuator_ctrlrange[:7, 1]
        mujoco.mj_resetDataKeyframe(m, self.data, m.key("home").id)
        mujoco.mj_forward(m, self.data)
        self.home = self.data.qpos[:7].copy()
        self.down = spatial.mat_to_quat(self.data.site_xmat[self.site].reshape(3, 3))     # tool down, yaw of home
        self.home_yaw = _yaw_of(self.data.site_xmat[self.site].reshape(3, 3))
        mass = np.zeros((m.nv, m.nv))
        mujoco.mj_fullM(m, self.data, mass)
        inertia = np.diag(mass)[:7]
        self.kp, self.kd = inertia * 400.0, inertia * 40.0

    # ------------------------------------------------------------------ state and observation
    def reset(self, q0: np.ndarray, target: Target) -> None:
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:7] = q0
        mujoco.mj_forward(self.model, self.data)
        self.target = target
        self.q_target = q0.copy()
        self.x_target = self.data.site_xpos[self.site].copy()
        self.yaw_target = self.yaw()

    def yaw(self) -> float:
        raw = _yaw_of(self.data.site_xmat[self.site].reshape(3, 3)) - self.home_yaw
        return float((raw + np.pi) % (2 * np.pi) - np.pi)

    def obs(self) -> np.ndarray:
        d, y, ty = self.data, self.yaw(), self.target.yaw
        return np.concatenate([d.qpos[:7], d.qvel[:7], d.site_xpos[self.site], [np.sin(y), np.cos(y)],
                               self.target.pos, [np.sin(ty), np.cos(ty)]]).astype(np.float32)

    def errors(self) -> tuple[float, float]:
        pos = float(np.linalg.norm(self.data.site_xpos[self.site] - self.target.pos))
        yaw = abs((self.yaw() - self.target.yaw + np.pi) % (2 * np.pi) - np.pi)
        return pos, yaw

    def success(self) -> bool:
        pos, yaw = self.errors()
        return pos < SUCCESS_POS and yaw < SUCCESS_YAW

    # ------------------------------------------------------------------ executing one action
    def _tool_quat(self, yaw: float) -> np.ndarray:
        return spatial.quat_mul(np.array([np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]), self.down)

    def _ik(self, pos: np.ndarray, yaw: float) -> np.ndarray:
        result = kinematics.solve_ik(self.model, "ee", pos, self._tool_quat(yaw), q_init=np.r_[self.q_target],
                                     joints=list(range(7)), max_iters=20)
        return np.clip(result.qpos[:7], self.lo, self.hi)

    def step(self, action: np.ndarray) -> None:
        a = np.clip(np.asarray(action, dtype=float), -1.0, 1.0)
        rep = self.rep
        if rep == "joint_position":
            self.q_target = self.lo + (a + 1) / 2 * (self.hi - self.lo)
        elif rep == "joint_delta":
            self.q_target = np.clip(self.q_target + JOINT_STEP * a, self.lo, self.hi)
        elif rep == "cartesian_delta":
            self.x_target = np.clip(self.x_target + EE_STEP * a[:3], BOX_LOW - 0.05, BOX_HIGH + 0.05)
            self.yaw_target = self.yaw_target + YAW_STEP * a[3]
            self.q_target = self._ik(self.x_target, self.yaw_target)
        elif rep == "cartesian_pose":
            self.x_target = BOX_LOW - 0.05 + (a[:3] + 1) / 2 * (BOX_HIGH - BOX_LOW + 0.1)
            self.yaw_target = a[3] * YAW_RANGE * 1.2
            self.q_target = self._ik(self.x_target, self.yaw_target)
        m, d, nd = self.model, self.data, self.nominal_data
        for _ in range(self.frame_skip):
            mujoco.mj_forward(m, d)
            nd.qpos[:], nd.qvel[:] = d.qpos[:7], d.qvel[:7]
            mujoco.mj_forward(self.nominal, nd)
            bias = nd.qfrc_bias[:7]                                        # the nominal model's gravity and Coriolis
            if rep == "torque":
                tau = a * self.limit
            elif rep == "joint_velocity":
                tau = bias + self.kd * 2 * (JOINT_SPEED * a - d.qvel[:7])
            else:
                tau = bias + self.kp * (self.q_target - d.qpos[:7]) - self.kd * d.qvel[:7]
            d.ctrl[:7] = np.clip(tau, -self.limit, self.limit)
            mujoco.mj_step(m, d)

    @property
    def action_dim(self) -> int:
        return 4 if self.rep.startswith("cartesian") else 7


def min_jerk(s: float) -> float:
    s = min(max(s, 0.0), 1.0)
    return 10 * s**3 - 15 * s**4 + 6 * s**5


class Expert:
    def __init__(self, env: ArmReach):
        self.env = env

    def plan(self) -> None:
        env = self.env
        x0, y0 = env.data.site_xpos[env.site].copy(), env.yaw()
        q = env.data.qpos[:7].copy()
        self.x_ref, self.yaw_ref, self.q_ref = [], [], []
        saved = env.q_target.copy()
        for k in range(STEPS + 2):
            s = min_jerk(k / MOVE_STEPS)
            x = x0 + s * (env.target.pos - x0)
            yaw = y0 + s * ((env.target.yaw - y0 + np.pi) % (2 * np.pi) - np.pi)
            env.q_target = q
            q = env._ik(x, yaw)
            self.x_ref.append(x)
            self.yaw_ref.append(yaw)
            self.q_ref.append(q)
        env.q_target = saved
        self.k = 0

    def act(self) -> np.ndarray:
        env, k = self.env, self.k
        self.k += 1
        q_next, x_next, y_next = self.q_ref[k + 1], self.x_ref[k + 1], self.yaw_ref[k + 1]
        dt = env.frame_skip * env.model.opt.timestep
        rep = env.rep
        if rep == "joint_position":
            a = 2 * (q_next - env.lo) / (env.hi - env.lo) - 1
        elif rep == "joint_delta":
            a = (q_next - env.q_target) / JOINT_STEP
        elif rep == "joint_velocity":
            a = ((q_next - env.data.qpos[:7]) / dt) / JOINT_SPEED
        elif rep == "cartesian_delta":
            a = np.r_[(x_next - env.x_target) / EE_STEP, (y_next - env.yaw_target) / YAW_STEP]
        elif rep == "cartesian_pose":
            a = np.r_[2 * (x_next - (BOX_LOW - 0.05)) / (BOX_HIGH - BOX_LOW + 0.1) - 1, y_next / (YAW_RANGE * 1.2)]
        else:                                                               # torque: computed torque on the reference
            m, d = env.model, env.data
            mujoco.mj_forward(m, d)
            mass = np.zeros((m.nv, m.nv))
            mujoco.mj_fullM(m, d, mass)
            qd_ref = (q_next - self.q_ref[k]) / dt
            acc = 225.0 * (q_next - d.qpos[:7]) + 30.0 * (qd_ref - d.qvel[:7])    # 15 rad/s: a 20 Hz torque loop cannot be stiffer
            a = (mass[:7, :7] @ acc + d.qfrc_bias[:7]) / env.limit
        return np.clip(a, -1.0, 1.0)


def start_pose(rng: np.random.Generator, home: np.ndarray) -> np.ndarray:
    return home + rng.uniform(-0.15, 0.15, 7)
