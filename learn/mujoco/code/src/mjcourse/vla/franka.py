from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import mujoco
import numpy as np

from mjcourse import spatial
from mjcourse.kinematics import site_jacobian


XML_PATH = Path(__file__).resolve().parents[1] / "models" / "franka_vla.xml"

OBJECTS = ("red_cube", "green_cube", "blue_cube")
TARGETS = ("tray", "left_zone", "right_zone")

# Home joint configuration for the 7-DOF Franka arm (pointing down towards table)
HOME_QPOS = np.array([0.0, 0.5, 0.0, 1.6, 0.0, 1.0416, 0.0])
DT = 0.002
CONTROL_HZ = 20
SUBSTEPS = int(1.0 / (CONTROL_HZ * DT))  # 25 physics steps per control step (50 ms)


@dataclass(frozen=True)
class FrankaLayout:
    cubes: tuple[tuple[float, float, float], ...]  # (x, y, yaw) for each cube


def sample_franka_layout(rng: np.random.Generator) -> FrankaLayout:
    while True:
        xy = np.column_stack([rng.uniform(0.38, 0.58, 3), rng.uniform(-0.20, 0.08, 3)])
        gaps = [np.linalg.norm(xy[a] - xy[b]) for a, b in ((0, 1), (0, 2), (1, 2))]
        if min(gaps) >= 0.09:
            break
    yaws = rng.uniform(-np.pi / 4, np.pi / 4, 3)
    coords = tuple((float(xy[i, 0]), float(xy[i, 1]), float(yaws[i])) for i in range(3))
    return FrankaLayout(cubes=coords)


class FrankaVLA:
    def __init__(self, xml_path: Path | str = XML_PATH):
        self.model = mujoco.MjModel.from_xml_path(str(xml_path))
        self.data = mujoco.MjData(self.model)
        self._renderer: mujoco.Renderer | None = None
        self.tcp_sid = self.model.site("gripper/tcp").id
        self.tray_sid = self.model.site("tray_center").id
        self.left_sid = self.model.site("left_zone").id
        self.right_sid = self.model.site("right_zone").id
        self.task: tuple[str, str] = ("red_cube", "tray")
        self.reset()

    def reset(self, seed: int | None = None, layout: FrankaLayout | None = None,
              task: tuple[str, str] | None = None) -> None:
        rng = np.random.default_rng(seed)
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.model.key("home").id)

        if layout is None:
            layout = sample_franka_layout(rng)

        for name, (x, y, yaw) in zip(OBJECTS, layout.cubes):
            jnt_id = self.model.joint(name).id
            qadr = self.model.jnt_qposadr[jnt_id]
            quat = spatial.rotvec_to_quat(np.array([0.0, 0.0, yaw]))
            self.data.qpos[qadr:qadr + 3] = [x, y, 0.02]
            self.data.qpos[qadr + 3:qadr + 7] = quat

        if task is not None:
            self.task = task
        else:
            self.task = (OBJECTS[rng.integers(3)], TARGETS[rng.integers(3)])

        mujoco.mj_forward(self.model, self.data)

    def tcp_pose(self) -> tuple[np.ndarray, np.ndarray]:
        pos = self.data.site_xpos[self.tcp_sid].copy()
        mat = self.data.site_xmat[self.tcp_sid].reshape(3, 3)
        quat = spatial.mat_to_quat(mat)
        return pos, quat

    def object_pos(self, name: str) -> np.ndarray:
        return self.data.xpos[self.model.body(name).id].copy()

    def target_pos(self, target_name: str) -> np.ndarray:
        if target_name == "tray":
            return self.data.site_xpos[self.tray_sid].copy()
        if target_name == "left_zone":
            return self.data.site_xpos[self.left_sid].copy()
        if target_name == "right_zone":
            return self.data.site_xpos[self.right_sid].copy()
        raise ValueError(f"Unknown target: {target_name}")

    def gripper_opening(self) -> float:
        ten_id = self.model.tendon("gripper/grip").id
        return float(self.data.ten_length[ten_id])

    def state(self, include_velocity: bool = False) -> np.ndarray:
        pos, quat = self.tcp_pose()
        grip = np.array([self.gripper_opening()], dtype=np.float32)
        qpos_arm = self.data.qpos[:7].astype(np.float32)
        feats = [pos.astype(np.float32), quat.astype(np.float32), grip, qpos_arm]

        if include_velocity:
            qvel_arm = self.data.qvel[:7].astype(np.float32)
            feats.append(qvel_arm)

        return np.concatenate(feats)

    def step(self, action: np.ndarray) -> dict:
        assert len(action) == 7, f"Expected 7-D action, got {len(action)}"
        dx = np.clip(action[:3], -1.0, 1.0) * 0.05
        drot = np.clip(action[3:6], -1.0, 1.0) * 0.10
        grip_cmd = float(np.clip(action[6], -1.0, 1.0))

        # Target gripper ctrl in meters [0.0, 0.04]
        target_grip = 0.04 if grip_cmd > 0.0 else 0.0

        target_pos = self.data.site_xpos[self.tcp_sid] + dx
        cur_mat = self.data.site_xmat[self.tcp_sid].reshape(3, 3)
        cur_quat = spatial.mat_to_quat(cur_mat)
        delta_quat = spatial.rotvec_to_quat(drot)
        target_quat = spatial.quat_mul(delta_quat, cur_quat)

        # Compute desired joint displacement once per control step
        jacp, jacr = site_jacobian(self.model, self.data, self.tcp_sid)
        jac = np.vstack([jacp, jacr])[:, :7]  # 6 x 7 Jacobian for the arm joints

        e_pos = target_pos - self.data.site_xpos[self.tcp_sid]
        mat_now = self.data.site_xmat[self.tcp_sid].reshape(3, 3)
        q_now = spatial.mat_to_quat(mat_now)
        e_rot = spatial.quat_to_rotvec(spatial.quat_mul(target_quat, spatial.quat_conj(q_now)))
        twist_err = np.concatenate([e_pos * 30.0, e_rot * 15.0])

        damping = 1e-3
        jjt = jac @ jac.T + damping * np.eye(6)
        qvel_des = jac.T @ np.linalg.solve(jjt, twist_err)

        # Nullspace posture regularization towards HOME_QPOS
        null = np.eye(7) - jac.T @ np.linalg.solve(jjt, jac)
        qvel_posture = (HOME_QPOS - self.data.qpos[:7]) * 1.5
        qvel_cmd = qvel_des + null @ qvel_posture
        q_target = self.data.qpos[:7] + qvel_cmd * (SUBSTEPS * DT)

        # Substep integration with joint PD and gravity bias compensation
        kp, kd = 300.0, 35.0
        for _ in range(SUBSTEPS):
            tau = kp * (q_target - self.data.qpos[:7]) - kd * self.data.qvel[:7] + self.data.qfrc_bias[:7]
            self.data.ctrl[:7] = np.clip(tau, self.model.actuator_ctrlrange[:7, 0], self.model.actuator_ctrlrange[:7, 1])
            self.data.ctrl[7] = target_grip
            mujoco.mj_step(self.model, self.data)

        obj_name, tgt_name = self.task
        obj_p = self.object_pos(obj_name)
        tgt_p = self.target_pos(tgt_name)
        dist_to_target = float(np.linalg.norm(obj_p[:2] - tgt_p[:2]))
        height = float(obj_p[2])
        success = bool(dist_to_target < 0.06 and height < 0.06)

        return {
            "success": success,
            "dist_to_target": dist_to_target,
            "object_height": height,
        }

    def render(self, camera: str = "top", width: int = 64, height: int = 64) -> np.ndarray:
        if self._renderer is None or self._renderer.width != width or self._renderer.height != height:
            self._renderer = mujoco.Renderer(self.model, height=height, width=width)
        self._renderer.update_scene(self.data, camera=camera)
        return self._renderer.render().copy()

    def close(self) -> None:
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None


def franka_expert_action(env: FrankaVLA) -> np.ndarray:
    obj_name, tgt_name = env.task
    obj_pos = env.object_pos(obj_name)
    tgt_pos = env.target_pos(tgt_name)
    tcp_pos, _ = env.tcp_pose()
    opening = env.gripper_opening()

    grasp_z = 0.035
    approach_z = 0.12
    lift_z = 0.16

    # State machine phases based on spatial geometry
    is_holding = obj_pos[2] > 0.05 and opening < 0.025

    if not is_holding:
        # Phase 1: Move above object
        xy_err = obj_pos[:2] - tcp_pos[:2]
        if np.linalg.norm(xy_err) > 0.015:
            dxy = xy_err / (np.linalg.norm(xy_err) + 1e-6)
            dz = np.clip(approach_z - tcp_pos[2], -1.0, 1.0)
            return np.array([dxy[0], dxy[1], dz, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)

        # Phase 2: Descend to grasp
        z_err = grasp_z - tcp_pos[2]
        if abs(z_err) > 0.008:
            return np.array([0.0, 0.0, np.clip(z_err * 10.0, -1.0, 1.0), 0.0, 0.0, 0.0, 1.0], dtype=np.float32)

        # Phase 3: Close gripper to grasp
        return np.array([0.0, 0.0, -0.2, 0.0, 0.0, 0.0, -1.0], dtype=np.float32)

    # Phase 4: Holding object -> lift
    if tcp_pos[2] < lift_z - 0.02:
        return np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, -1.0], dtype=np.float32)

    # Phase 5: Carry to target
    target_xy_err = tgt_pos[:2] - tcp_pos[:2]
    if np.linalg.norm(target_xy_err) > 0.02:
        dxy = target_xy_err / (np.linalg.norm(target_xy_err) + 1e-6)
        return np.array([dxy[0], dxy[1], 0.0, 0.0, 0.0, 0.0, -1.0], dtype=np.float32)

    # Phase 6: Release over target
    return np.array([0.0, 0.0, -0.5, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)
