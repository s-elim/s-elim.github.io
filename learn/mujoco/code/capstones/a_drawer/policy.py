from __future__ import annotations

import numpy as np


class ScriptedDrawerPolicy:
    def __init__(self, ee_step: float = 0.015) -> None:
        self.ee_step = float(ee_step)
        self.phase = 0
        self.grasp_count = 0

    def reset(self) -> None:
        self.phase = 0
        self.grasp_count = 0

    def __call__(self, obs: np.ndarray) -> np.ndarray:
        # Observation indices:
        # 14:17 = tcp_pos (x, y, z)
        # 18:21 = handle_pos (x, y, z)
        # 21 = drawer_pos
        # 22 = target_open
        tcp_pos = obs[14:17]
        handle_pos = obs[18:21]
        drawer_pos = obs[21]
        target_open = obs[22]

        if self.phase == 0:
            err = handle_pos - tcp_pos
            dist = float(np.linalg.norm(err))
            if dist < 0.012:
                self.phase = 1
                self.grasp_count = 0
                return np.array([0.0, 0.0, 0.0, -1.0], dtype=np.float32)
            act_xyz = np.clip(err / self.ee_step, -1.0, 1.0)
            return np.array([act_xyz[0], act_xyz[1], act_xyz[2], 1.0], dtype=np.float32)

        if self.phase == 1:
            self.grasp_count += 1
            if self.grasp_count >= 10:
                self.phase = 2
            err = handle_pos - tcp_pos
            act_xyz = np.clip(err / self.ee_step, -0.2, 0.2)
            return np.array([act_xyz[0], act_xyz[1], act_xyz[2], -1.0], dtype=np.float32)

        if self.phase == 2:
            if drawer_pos >= target_open:
                self.phase = 3
                return np.array([0.0, 0.0, 0.0, -1.0], dtype=np.float32)
            return np.array([-1.0, 0.0, 0.0, -1.0], dtype=np.float32)

        return np.array([0.0, 0.0, 0.0, -1.0], dtype=np.float32)
