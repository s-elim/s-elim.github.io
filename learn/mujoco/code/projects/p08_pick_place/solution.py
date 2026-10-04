"""Project 8 reference solution: a three-cube pick-and-place state machine with checks at every step."""

import math

import mujoco
import numpy as np

from mjcourse import kinematics, spatial

OPEN, CLOSED = 0.04, 0.0      # gripper half-opening commands, m
WN = 20.0                     # joint tracking bandwidth, rad/s
ABOVE, GRASP_Z, CARRY_Z, PLACE_Z = 0.15, 0.022, 0.15, 0.045   # tcp heights, m
SLOTS = np.array([[-0.03, -0.03], [0.03, -0.03], [0.0, 0.03]])  # place points relative to the tray centre, m


class Arm:
    """Joint-space minimum-jerk moves to IK solutions, tracked by PD with gravity compensation."""

    def __init__(self, model, data):
        self.model, self.data = model, data
        mujoco.mj_forward(model, data)
        mass = np.zeros((model.nv, model.nv))
        mujoco.mj_fullM(model, data, mass)
        self.kp, self.kd = np.diag(mass)[:7] * WN**2, 2 * np.diag(mass)[:7] * WN
        self.target = data.qpos[:7].copy()
        self.down = spatial.mat_to_quat(data.site("gripper/tcp").xmat.reshape(3, 3))   # tool down at home

    def step(self, n=1):
        m, d = self.model, self.data
        for _ in range(n):
            mujoco.mj_forward(m, d)
            tau = self.kp * (self.target - d.qpos[:7]) - self.kd * d.qvel[:7] + d.qfrc_bias[:7]
            d.ctrl[:7] = np.clip(tau, *m.actuator_ctrlrange[:7].T)
            mujoco.mj_step(m, d)

    def move_to(self, pos, yaw, seconds) -> bool:
        quat = spatial.quat_mul(np.array([math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]), self.down)
        result, _ = kinematics.solve_ik_restarts(self.model, "gripper/tcp", np.asarray(pos), quat,
                                                 q_init=self.data.qpos.copy(), joints=list(range(7)),
                                                 restarts=5, seed=0, tol_pos=5e-4, tol_rot=5e-3)
        if not result.success:
            return False
        start, goal = self.target.copy(), result.qpos[:7].copy()
        n = round(seconds / self.model.opt.timestep)
        for k in range(n):
            s = (k + 1) / n
            self.target = start + (goal - start) * (10 * s**3 - 15 * s**4 + 6 * s**5)
            self.step()
        self.step(round(0.2 / self.model.opt.timestep))
        return True

    def grip(self, command, seconds=0.6):
        self.data.ctrl[7] = command
        self.step(round(seconds / self.model.opt.timestep))


def holding(model, data, cube) -> bool:
    """Both pads touch the cube and the jaws stopped on it, neither open nor fully closed."""
    geom = model.geom(cube).id
    pads = {model.geom("gripper/pad_left").id, model.geom("gripper/pad_right").id}
    touching = {c.geom1 if c.geom2 == geom else c.geom2 for c in data.contact[:data.ncon] if geom in (c.geom1, c.geom2)}
    return pads <= touching and 0.01 < data.ten_length[0] < 0.035


def tipped(data, cube) -> bool:
    return data.body(cube).xmat[8] < math.cos(math.pi / 4)


def pick_and_place(model, data) -> dict[str, str]:
    arm = Arm(model, data)
    tray = data.site("tray_center").xpos.copy()
    outcome = {}
    cubes = sorted(("red_cube", "green_cube", "blue_cube"), key=lambda c: np.linalg.norm(data.body(c).xpos[:2] - tray[:2]))
    for cube, slot in zip(cubes, SLOTS):
        outcome[cube] = place_one(model, data, arm, cube, tray[:2] + slot)
        arm.grip(OPEN, 0.3)
    return outcome


def place_one(model, data, arm, cube, goal) -> str:
    xy = data.body(cube).xpos[:2].copy()
    yaw = math.atan2(data.body(cube).xmat[3], data.body(cube).xmat[0])
    yaw = (yaw + math.pi / 4) % (math.pi / 2) - math.pi / 4      # a cube looks the same every 90 degrees
    arm.grip(OPEN, 0.3)
    if not (arm.move_to([*xy, ABOVE], yaw, 1.5) and arm.move_to([*xy, GRASP_Z], yaw, 1.0)):
        return "IK failed"
    if tipped(data, cube):
        return "knocked over"
    arm.grip(CLOSED)
    if not holding(model, data, cube):
        return "grasp missed"
    if not arm.move_to([*xy, CARRY_Z], yaw, 1.0):
        return "IK failed"
    if not holding(model, data, cube):
        return "dropped while lifting"
    if not arm.move_to([*goal, CARRY_Z], 0.0, 1.5):
        return "IK failed"
    if not holding(model, data, cube):
        return "dropped while carrying"
    if not arm.move_to([*goal, PLACE_Z], 0.0, 0.8):
        return "IK failed"
    arm.grip(OPEN, 0.5)
    arm.move_to([*goal, CARRY_Z], 0.0, 0.8)
    p, tray = data.body(cube).xpos, data.site("tray_center").xpos
    if abs(p[0] - tray[0]) < 0.05 and abs(p[1] - tray[1]) < 0.05 and p[2] < 0.06:
        return "success"
    return "knocked over" if tipped(data, cube) else "missed the tray"
