"""Lesson 0.1: measure MuJoCo's integration error for a falling ball.

INPUT   free_fall.xml (one ball, gravity only) and a list of timesteps
PROCESS step each model to t = 0.3 s and compare z with z0 - g t^2 / 2
OUTPUT  a table of position error per timestep, next to the error predicted
        for the semi-implicit Euler integrator: -g h t / 2

Run:  python examples/l0_1_free_fall.py
"""

import mujoco

from mjcourse import model_path

G, Z0, T_END = 9.81, 1.0, 0.3


def error_at(timestep: float) -> tuple[float, float]:
    model = mujoco.MjModel.from_xml_path(str(model_path("free_fall")))
    model.opt.timestep = timestep
    data = mujoco.MjData(model)
    for _ in range(round(T_END / timestep)):
        mujoco.mj_step(model, data)
    exact = Z0 - 0.5 * G * data.time**2
    measured = data.qpos[2] - exact          # qpos = [x, y, z, qw, qx, qy, qz]
    predicted = -0.5 * G * timestep * data.time
    return measured, predicted


if __name__ == "__main__":
    print(f"{'timestep (s)':>12} {'error (mm)':>11} {'-g h t / 2 (mm)':>16}")
    for h in (0.0005, 0.001, 0.002, 0.005, 0.01):
        measured, predicted = error_at(h)
        print(f"{h:>12.4f} {1e3 * measured:>11.4f} {1e3 * predicted:>16.4f}")
