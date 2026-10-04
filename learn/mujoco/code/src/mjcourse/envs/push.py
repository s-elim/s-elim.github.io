"""Push: slide a puck to a goal with the closed gripper (Level 12 checkpoint).

Observation (float32, 21): joint positions (7), joint velocities (7), tcp position (3),
puck position xy (2), goal xy (2). Every component has a declared real-robot source in
`OBSERVATION`; Lesson 12.2's test fails the environment if one does not.
`extra_observations` appends components a real robot could not measure, for that test
to catch: "puck_velocity" (simulator state), "contact_force" (contact solver),
"puck_friction" (model parameter).
Action: see mjcourse.envs.arm; "ee_delta" moves the tcp in x and y at a fixed height.
Reward (`reward=`): "dense" minus the puck-goal distance; "shaped" adds minus half the
tcp-puck distance; "sparse" 1 on success; "contact" 1 per step in contact with the puck.
Terminated: the puck is within `success_radius` of the goal, unless `terminate_on_success`
is False (then success is judged where the puck ends). Truncated: after
`max_episode_steps` steps (0.05 s each by default).
reset(options=...) accepts "puck" and "goal" positions and, for Level 17, "puck_mass" (kg)
and "friction" (sliding coefficient of the puck and the floor); parameters not given
return to their nominal values, since model edits persist across episodes.
"""

from __future__ import annotations

import mujoco
import numpy as np
from gymnasium import spaces

from mjcourse import kinematics, spatial
from mjcourse.envs.arm import ArmCommand
from mjcourse.envs.base import MujocoEnv

OBSERVATION = (("joint_pos", 7, "joint encoders"), ("joint_vel", 7, "joint encoders, differentiated"),
               ("tcp_pos", 3, "forward kinematics of the joint encoders"), ("puck_xy", 2, "camera tracker"),
               ("goal_xy", 2, "task specification"))
PRIVILEGED = {"puck_velocity": (3, "simulator state"), "contact_force": (1, "contact solver"),
              "puck_friction": (1, "model parameter")}
REWARDS = ("dense", "shaped", "sparse", "contact")
PUSH_HEIGHT = 0.03                                   # tcp height while pushing (m)
START_TCP = np.array([0.36, 0.0, PUSH_HEIGHT])


class PushEnv(MujocoEnv):
    _start_q: np.ndarray | None = None               # shared IK solution for the start pose

    def __init__(self, action_mode: str = "ee_delta", reward: str = "shaped", frame_skip: int = 25,
                 max_episode_steps: int = 100, success_radius: float = 0.03, extra_observations: tuple[str, ...] = (),
                 terminate_on_success: bool = True, max_lead: float | None = None, **kwargs):
        super().__init__("push", frame_skip, max_episode_steps, **kwargs)
        if reward not in REWARDS:
            raise ValueError(f"reward must be one of {REWARDS}")
        self.reward_kind, self.success_radius, self.extra = reward, success_radius, tuple(extra_observations)
        self.terminate_on_success = terminate_on_success
        self.arm = ArmCommand(self.model, self.data, action_mode, "gripper/tcp", ee_axes=(0, 1),
                              ee_low=(0.25, -0.35, PUSH_HEIGHT), ee_high=(0.75, 0.35, PUSH_HEIGHT), max_lead=max_lead)
        self.action_space = self.arm.space
        self.observation_sources = {name: source for name, _, source in OBSERVATION}
        self.observation_sources |= {name: PRIVILEGED[name][1] for name in self.extra}
        size = sum(n for _, n, _ in OBSERVATION) + sum(PRIVILEGED[name][0] for name in self.extra)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(size,), dtype=np.float32)
        self.puck = self.model.body("puck").id
        self.puck_geom = self.model.geom("puck").id
        self.goal_site = self.model.site("goal").id
        self.pusher = {self.model.geom(n).id for n in ("gripper/pad_left", "gripper/pad_right",
                                                      "gripper/finger_left", "gripper/finger_right")}
        self.puck_adr = self.model.jnt_qposadr[self.model.joint("puck").id]
        self.floor_geom = self.model.geom("floor").id
        self.nominal = {"puck_mass": float(self.model.body_mass[self.puck]),
                        "puck_inertia": self.model.body_inertia[self.puck].copy(),
                        "friction": float(self.model.geom_friction[self.puck_geom, 0])}
        if PushEnv._start_q is None:
            mujoco.mj_resetDataKeyframe(self.model, self.data, self.keyframe)
            mujoco.mj_forward(self.model, self.data)
            down = spatial.mat_to_quat(self.data.site("gripper/tcp").xmat.reshape(3, 3))
            result, _ = kinematics.solve_ik_restarts(self.model, "gripper/tcp", START_TCP, down, q_init=self.data.qpos.copy(),
                                                     joints=list(range(7)), restarts=10, seed=0, tol_pos=5e-4, tol_rot=5e-3)
            PushEnv._start_q = result.qpos[:7].copy()

    def _reset_task(self, options: dict) -> None:
        d, rng, m = self.data, self.np_random, self.model
        mass = options.get("puck_mass", self.nominal["puck_mass"])
        if mass != m.body_mass[self.puck]:
            m.body_mass[self.puck] = mass
            m.body_inertia[self.puck] = self.nominal["puck_inertia"] * mass / self.nominal["puck_mass"]
            mujoco.mj_setConst(m, d)            # derived constants (inverse weights that set contact softness)
            mujoco.mj_resetDataKeyframe(m, d, self.keyframe)   # mj_setConst used d as scratch
        for g in (self.puck_geom, self.floor_geom):
            m.geom_friction[g, 0] = options.get("friction", self.nominal["friction"])
        d.qpos[:7] = PushEnv._start_q
        d.ctrl[7] = 0.0                                                    # gripper closed: a pusher
        d.qpos[7:9] = 0.0
        puck = options.get("puck", np.array([rng.uniform(0.44, 0.50), rng.uniform(-0.05, 0.05)]))
        d.qpos[self.puck_adr:self.puck_adr + 7] = [*puck, 0.02, 1, 0, 0, 0]
        goal = options.get("goal", np.array([rng.uniform(0.58, 0.66), rng.uniform(-0.15, 0.15)]))
        self.model.site_pos[self.goal_site][:2] = goal
        mujoco.mj_forward(self.model, d)
        self.arm.reset()

    def _apply_action(self, action: np.ndarray) -> None:
        self.arm.apply(action)

    def _control(self) -> None:
        self.arm.control()
        self.data.ctrl[7] = 0.0

    def puck_xy(self) -> np.ndarray:
        return self.data.xpos[self.puck][:2].copy()

    def goal_xy(self) -> np.ndarray:
        return self.model.site_pos[self.goal_site][:2].copy()

    def _distance(self) -> float:
        return float(np.linalg.norm(self.puck_xy() - self.goal_xy()))

    def _in_contact(self) -> bool:
        d = self.data
        return any((c.geom1 == self.puck_geom and c.geom2 in self.pusher) or (c.geom2 == self.puck_geom and c.geom1 in self.pusher)
                   for c in d.contact[:d.ncon])

    def _get_obs(self) -> np.ndarray:
        d = self.data
        parts = [d.qpos[:7], d.qvel[:7], d.site("gripper/tcp").xpos, self.puck_xy(), self.goal_xy()]
        for name in self.extra:
            if name == "puck_velocity":
                velocity = np.zeros(6)                                     # [angular; linear] in the world frame
                mujoco.mj_objectVelocity(self.model, d, mujoco.mjtObj.mjOBJ_BODY, self.puck, velocity, 0)
                parts.append(velocity[3:])
            elif name == "contact_force":
                total, f = 0.0, np.zeros(6)
                for i in range(d.ncon):
                    if self.puck_geom in (d.contact[i].geom1, d.contact[i].geom2):
                        mujoco.mj_contactForce(self.model, d, i, f)
                        total += f[0]
                parts.append([total])
            elif name == "puck_friction":
                parts.append([self.model.geom_friction[self.puck_geom, 0]])
        return np.concatenate(parts).astype(np.float32)

    def _reward(self, action: np.ndarray) -> float:
        if self.reward_kind == "dense":
            return -self._distance()
        if self.reward_kind == "shaped":
            return -self._distance() - 0.5 * float(np.linalg.norm(self.data.site("gripper/tcp").xpos[:2] - self.puck_xy()))
        if self.reward_kind == "sparse":
            return float(self._distance() < self.success_radius)
        return float(self._in_contact())

    def _terminal(self) -> bool:
        return self.terminate_on_success and self._distance() < self.success_radius

    def _get_info(self) -> dict:
        return {"distance": self._distance(), "is_success": self._distance() < self.success_radius,
                "contact": self._in_contact()}
