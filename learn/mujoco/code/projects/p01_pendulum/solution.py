"""Project 1 reference solution: a pendulum simulator that matches MuJoCo."""

import numpy as np

M, L, I_C, G = 1.0, 0.5, 1e-4, 9.81
I_PIVOT = M * L * L + I_C


def acceleration(theta: float, omega: float, damping: float = 0.0, torque: float = 0.0) -> float:
    # Gravity torque about +y for a bob at (-L sin q, 0, -L cos q): -m g L sin(q) (Lesson 0.1, pendulum.xml).
    return (-M * G * L * np.sin(theta) - damping * omega + torque) / I_PIVOT


def simulate(theta0: float, omega0: float, h: float, steps: int, method: str = "euler",
             damping: float = 0.0) -> np.ndarray:
    out = np.empty((steps + 1, 2))
    out[0] = theta0, omega0
    q, w = theta0, omega0
    for k in range(steps):
        if method == "euler":
            w = w + h * acceleration(q, w, damping)
            q = q + h * w
        elif method == "rk4":
            def f(state):
                return np.array([state[1], acceleration(state[0], state[1], damping)])
            s = np.array([q, w])
            k1 = f(s)
            k2 = f(s + 0.5 * h * k1)
            k3 = f(s + 0.5 * h * k2)
            k4 = f(s + h * k3)
            q, w = s + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        else:
            raise ValueError(method)
        out[k + 1] = q, w
    return out
