"""Project 1 starter: write your own pendulum simulator.

Fill in the two functions below. The tests compare your simulator with MuJoCo's
pendulum.xml, step by step. Run them with:

    MJC_IMPL=starter pytest projects/p01_pendulum
"""

import numpy as np

# Parameters of models/pendulum.xml: point mass m at distance L, plus a small rotor inertia.
M, L, I_C, G = 1.0, 0.5, 1e-4, 9.81
I_PIVOT = M * L * L + I_C


def acceleration(theta: float, omega: float, damping: float = 0.0, torque: float = 0.0) -> float:
    """Angular acceleration (rad/s^2) of the pendulum; theta = 0 is hanging straight down.

    Mind the sign convention of pendulum.xml: its hinge axis is +y.
    """
    raise NotImplementedError


def simulate(theta0: float, omega0: float, h: float, steps: int, method: str = "euler",
             damping: float = 0.0) -> np.ndarray:
    """Return an array of shape (steps + 1, 2) with (theta, omega) after each step.

    method "euler": semi-implicit Euler (velocity first, then position with the new velocity),
    which is what MuJoCo's Euler integrator does when there is no joint damping.
    method "rk4": classical fourth-order Runge-Kutta.
    """
    raise NotImplementedError
