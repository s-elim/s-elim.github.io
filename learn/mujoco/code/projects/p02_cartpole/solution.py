"""Project 2 reference solution: LQR on MuJoCo's finite-difference linearization."""

import mujoco
import numpy as np
import scipy.linalg


def linearize(model: mujoco.MjModel, qpos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    data = mujoco.MjData(model)
    data.qpos[:] = qpos
    mujoco.mj_forward(model, data)
    a = np.zeros((2 * model.nv, 2 * model.nv))
    b = np.zeros((2 * model.nv, model.nu))
    mujoco.mjd_transitionFD(model, data, 1e-6, True, a, b, None, None)
    return a, b


def lqr_gain(a: np.ndarray, b: np.ndarray, q: np.ndarray, r: np.ndarray) -> np.ndarray:
    p = scipy.linalg.solve_discrete_are(a, b, q, r)
    return np.linalg.solve(r + b.T @ p @ b, b.T @ p @ a)


def controller(k: np.ndarray, data: mujoco.MjData) -> float:
    x = np.concatenate([data.qpos, data.qvel])
    return float(-(k @ x)[0])
