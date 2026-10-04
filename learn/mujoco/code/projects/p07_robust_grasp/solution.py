"""Project 7 reference solution: a grasp-and-lift routine that reads the cube pose at the start."""

import mujoco
import numpy as np

OPEN, CLOSED = 0.04, 0.0      # m, half-opening command
HIGH = 0.0                    # gz with the tcp 0.35 m above the floor
GRASP = -0.335                # gz with the tcp at the height of the cube centre
LIFT = 0.15                   # m
TIMES = {"move": 1.0, "descend": 1.0, "close": 0.6, "lift": 1.5}


def min_jerk(s: float) -> float:
    s = min(max(s, 0.0), 1.0)
    return 10 * s**3 - 15 * s**4 + 6 * s**5


def make_controller(model: mujoco.MjModel, data: mujoco.MjData):
    cube = data.xpos[model.body("cube").id].copy()     # read once, at the start (privileged, allowed here)
    start = data.qpos[:3].copy()
    t_move, t_descend, t_close = np.cumsum(list(TIMES.values()))[:3]

    def controller(t: float, data: mujoco.MjData) -> np.ndarray:
        xy = start[:2] + min_jerk(t / t_move) * (cube[:2] - start[:2])
        if t < t_move:
            return np.array([*xy, HIGH, OPEN])
        if t < t_descend:
            return np.array([*xy, HIGH + min_jerk((t - t_move) / TIMES["descend"]) * (GRASP - HIGH), OPEN])
        if t < t_close:
            return np.array([*xy, GRASP, CLOSED])
        return np.array([*xy, GRASP + min_jerk((t - t_close) / TIMES["lift"]) * LIFT, CLOSED])

    return controller
