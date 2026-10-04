"""Project 9 reference solution: Project 8's state machine on cube positions estimated from the
front camera's depth and segmentation, with no privileged state."""

import math

import mujoco
import numpy as np

from mjcourse import kinematics, spatial

CUBES = ("red_cube", "green_cube", "blue_cube")
CAMERA = "front"
FLIP = np.diag([1.0, -1.0, -1.0])        # MuJoCo camera axes (x right, y up, looking along -z) -> OpenCV
OPEN, CLOSED = 0.04, 0.0
WN = 20.0
ABOVE, GRASP_Z, CARRY_Z, PLACE_Z = 0.15, 0.022, 0.15, 0.045
SLOTS = np.array([[-0.03, -0.03], [0.03, -0.03], [0.0, 0.03]])
MIN_PIXELS = 50


def back_project(model, depth, mask, cam_pos, cam_mat):
    """World points (N, 3) of the masked pixels; depth is the distance along the optical axis."""
    f = 0.5 * depth.shape[0] / math.tan(math.radians(model.cam_fovy[model.camera(CAMERA).id]) / 2)
    v, u = np.nonzero(mask)
    z = depth[v, u]
    p_cv = np.c_[(u + 0.5 - depth.shape[1] / 2) * z / f, (v + 0.5 - depth.shape[0] / 2) * z / f, z]
    return p_cv @ (cam_mat @ FLIP).T + cam_pos


def estimate_cubes(model, depth, seg, cam_pos, cam_mat) -> dict[str, np.ndarray]:
    """Centre (x, y) of every cube with at least MIN_PIXELS visible pixels."""
    out = {}
    for name in CUBES:
        mask = (seg[..., 0] == model.geom(name).id) & (seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM)
        if mask.sum() < MIN_PIXELS:
            continue
        points = back_project(model, depth, mask, cam_pos, cam_mat)
        top = points[points[:, 2] > points[:, 2].max() - 0.004][:, :2]   # the top face: one height
        # The centroid of the top face's pixels leans toward the camera (nearer pixels cover less area);
        # the midpoint of its extent along its own axes does not.
        mean = top.mean(axis=0)
        _, _, axes = np.linalg.svd(top - mean, full_matrices=False)
        along = (top - mean) @ axes.T
        out[name] = mean + 0.5 * (along.max(axis=0) + along.min(axis=0)) @ axes
    return out


class Arm:
    """Joint-space moves to IK solutions; dynamics from the routine's own copy of the robot's state."""

    def __init__(self, robot):
        self.robot, self.model = robot, robot.model
        self.sim = mujoco.MjData(self.model)           # cubes in this copy stay at the model's defaults
        self._sync()
        mass = np.zeros((self.model.nv, self.model.nv))
        mujoco.mj_fullM(self.model, self.sim, mass)
        self.kp, self.kd = np.diag(mass)[:7] * WN**2, 2 * np.diag(mass)[:7] * WN
        self.target = self.sim.qpos[:7].copy()
        self.grip_command = OPEN
        self.down = spatial.mat_to_quat(self.sim.site("gripper/tcp").xmat.reshape(3, 3))

    def _sync(self):
        self.sim.qpos[:9], self.sim.qvel[:9] = self.robot.qpos, self.robot.qvel
        mujoco.mj_forward(self.model, self.sim)

    def step(self, n=1):
        for _ in range(n):
            self._sync()
            tau = self.kp * (self.target - self.sim.qpos[:7]) - self.kd * self.sim.qvel[:7] + self.sim.qfrc_bias[:7]
            self.robot.step(np.r_[np.clip(tau, *self.model.actuator_ctrlrange[:7].T), self.grip_command])

    def move_to(self, pos, yaw, seconds) -> bool:
        quat = spatial.quat_mul(np.array([math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]), self.down)
        result, _ = kinematics.solve_ik_restarts(self.model, "gripper/tcp", np.asarray(pos), quat,
                                                 q_init=self.sim.qpos.copy(), joints=list(range(7)),
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
        self.grip_command = command
        self.step(round(seconds / self.model.opt.timestep))


def holding(robot) -> bool:
    """Both pads pressed (tactile) and the jaws stopped on something, neither open nor fully closed."""
    return bool(np.all(robot.pad_forces() > 0.5)) and 0.01 < robot.grip_opening() < 0.035


def look(robot) -> dict[str, np.ndarray]:
    return estimate_cubes(robot.model, *robot.observe())


def pick_and_place(robot) -> dict[str, str]:
    arm = Arm(robot)
    tray = arm.sim.site("tray_center").xpos[:2].copy()       # the tray is part of the fixed scene
    seen = look(robot)
    outcome = {name: "not seen" for name in CUBES if name not in seen}
    order = sorted(seen, key=lambda name: np.linalg.norm(seen[name] - tray))
    for name, slot in zip(order, SLOTS):
        xy = look(robot).get(name)                           # look again: an earlier pick may have moved it
        outcome[name] = "not seen" if xy is None else place_one(arm, robot, name, xy, tray + slot, tray)
    return outcome


def place_one(arm, robot, name, xy, goal, tray) -> str:
    arm.grip(OPEN, 0.3)
    if not (arm.move_to([*xy, ABOVE], 0.0, 1.5) and arm.move_to([*xy, GRASP_Z], 0.0, 1.0)):
        return "IK failed"
    arm.grip(CLOSED)
    if not holding(robot):
        return "grasp missed"
    if not arm.move_to([*xy, CARRY_Z], 0.0, 1.0):
        return "IK failed"
    if not holding(robot):
        return "dropped while lifting"
    if not arm.move_to([*goal, CARRY_Z], 0.0, 1.5):
        return "IK failed"
    if not holding(robot):
        return "dropped while carrying"
    if not arm.move_to([*goal, PLACE_Z], 0.0, 0.8):
        return "IK failed"
    arm.grip(OPEN, 0.5)
    arm.move_to([*goal, CARRY_Z], 0.0, 0.8)
    where = look(robot).get(name)
    if where is not None and np.all(np.abs(where - tray) < 0.045):
        return "success"
    return "missed the tray"
