"""Project 2 starter: balance the cart-pole with LQR on MuJoCo's own linearization.

Fill in the three functions. Run the tests with:

    MJC_IMPL=starter pytest projects/p02_cartpole
"""

import mujoco
import numpy as np


def linearize(model: mujoco.MjModel, qpos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Discrete-time A (2nv x 2nv) and B (2nv x nu) of one mj_step at (qpos, qvel = 0, ctrl = 0).

    Hint: mujoco.mjd_transitionFD.
    """
    raise NotImplementedError


def lqr_gain(a: np.ndarray, b: np.ndarray, q: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Discrete-time infinite-horizon LQR gain K, so that u = -K x. Hint: scipy.linalg.solve_discrete_are."""
    raise NotImplementedError


def controller(k: np.ndarray, data: mujoco.MjData) -> float:
    """Return the cart force for the current state, x = [qpos, qvel]."""
    raise NotImplementedError
