"""Project 5 starter: six-dimensional IK for arm7.xml by damped least squares.

Fill in the two functions. Run the tests with:

    MJC_IMPL=starter pytest projects/p05_ik
"""

import mujoco
import numpy as np


def pose_error(model: mujoco.MjModel, data: mujoco.MjData, site: str | int,
               target_pos: np.ndarray, target_quat: np.ndarray) -> np.ndarray:
    """6-vector [target position - site position, rotation vector taking the site orientation to the target],
    both in the world frame, from the site pose currently in `data` (call mj_kinematics first).

    target_quat is (w, x, y, z); q and -q describe the same orientation and must give the same error.
    """
    raise NotImplementedError


def solve(model: mujoco.MjModel, site: str, target_pos: np.ndarray, target_quat: np.ndarray,
          q_init: np.ndarray, posture: np.ndarray | None = None) -> tuple[np.ndarray, bool]:
    """Joint angles that put `site` at the target pose within 1 mm and 1 degree, inside the joint limits.

    Returns (q, True) on success and (anything, False) when no solution was found: never claim success
    for a pose you did not reach. Among the solutions, prefer the one closest to `posture`
    (default q_init) through a null-space term.
    """
    raise NotImplementedError
