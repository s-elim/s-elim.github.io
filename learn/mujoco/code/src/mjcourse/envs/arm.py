"""Three ways for a policy to command arm7 (Lesson 12.2).

"torque"      the action is the actuator command: joint torques scaled to each
              actuator's range. Nothing between the policy and the physics, gravity
              included.
"joint_delta" the action moves joint targets by up to `joint_step` rad per environment
              step; PD with gravity compensation tracks them at the physics rate.
"ee_delta"    the action moves a target for a site by up to `ee_step` m per environment
              step (along the axes in `ee_axes`); a Cartesian impedance with the tool held
              pointing down tracks it (mjcourse.control.cartesian_impedance). With
              `max_lead`, the target never leads the site by more than that distance
              (m), which caps the force the impedance can apply (Lesson 10.3).
The arm's dofs and torque actuators are the first seven.
"""

from __future__ import annotations

import mujoco
import numpy as np
from gymnasium import spaces

from mjcourse import control, spatial

MODES = ("torque", "joint_delta", "ee_delta")


class ArmCommand:
    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData, mode: str, site: str,
                 ee_axes: tuple[int, ...] = (0, 1, 2), joint_step: float = 0.05, ee_step: float = 0.02,
                 ee_low=(0.25, -0.35, 0.02), ee_high=(0.70, 0.35, 0.55), wn: float = 20.0, max_lead: float | None = None):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.model, self.data, self.mode, self.site = model, data, mode, site
        self.ee_axes, self.joint_step, self.ee_step = list(ee_axes), joint_step, ee_step
        self.ee_low, self.ee_high = np.array(ee_low), np.array(ee_high)
        self.lo, self.hi = model.jnt_range[:7, 0], model.jnt_range[:7, 1]
        self.limit = model.actuator_ctrlrange[:7, 1]
        self.wn, self.max_lead = wn, max_lead
        size = {"torque": 7, "joint_delta": 7, "ee_delta": len(self.ee_axes)}[mode]
        self.space = spaces.Box(-1.0, 1.0, shape=(size,), dtype=np.float32)

    def reset(self) -> None:
        """Targets start where the arm is; call after the state is set."""
        d = self.data
        mass = np.zeros((self.model.nv, self.model.nv))
        mujoco.mj_fullM(self.model, d, mass)
        self.kp, self.kd = np.diag(mass)[:7] * self.wn**2, 2 * np.diag(mass)[:7] * self.wn
        self.q_target = d.qpos[:7].copy()
        self.x_target = d.site(self.site).xpos.copy()
        self.down = spatial.mat_to_quat(d.site(self.site).xmat.reshape(3, 3))
        self.q_rest = d.qpos[:7].copy()

    def apply(self, action: np.ndarray) -> None:
        if self.mode == "torque":
            self.data.ctrl[:7] = action * self.limit
        elif self.mode == "joint_delta":
            self.q_target = np.clip(self.q_target + self.joint_step * action, self.lo, self.hi)
        else:
            self.x_target[self.ee_axes] += self.ee_step * action
            self.x_target = np.clip(self.x_target, self.ee_low, self.ee_high)
            if self.max_lead is not None:
                site = self.data.site(self.site).xpos
                lead = self.x_target - site
                norm = np.linalg.norm(lead[self.ee_axes])
                if norm > self.max_lead:
                    self.x_target[self.ee_axes] = site[self.ee_axes] + lead[self.ee_axes] * self.max_lead / norm

    def control(self) -> None:
        d = self.data
        if self.mode == "torque":
            return
        mujoco.mj_forward(self.model, d)
        if self.mode == "joint_delta":
            tau = self.kp * (self.q_target - d.qpos[:7]) - self.kd * d.qvel[:7] + d.qfrc_bias[:7]
            d.ctrl[:7] = np.clip(tau, -self.limit, self.limit)
        else:
            d.ctrl[:7] = control.cartesian_impedance(self.model, d, self.site, self.x_target, self.down, 2000.0, 300.0,
                                                     q_rest=self.q_rest, k_null=20.0)
