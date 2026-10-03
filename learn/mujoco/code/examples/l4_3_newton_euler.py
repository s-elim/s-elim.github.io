"""Lesson 4.3: Newton-Euler for one body, and conservation through a collision.

INPUT   tumbling_box.xml (one free body), two_balls.xml (two free spheres)
PROCESS (1) apply a known force and torque to the box, then compare MuJoCo's
            accelerations with Newton's and Euler's equations computed by hand;
        (2) collide the two balls at four contact damping ratios and measure total
            linear momentum and kinetic energy before and after
OUTPUT  printed comparisons

Run:  python examples/l4_3_newton_euler.py
"""

import mujoco
import numpy as np

from mjcourse import model_path


def newton_euler() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("tumbling_box")))
    data = mujoco.MjData(model)
    data.qvel[3:6] = [0.4, -1.2, 2.0]                 # body-frame angular velocity (rad/s)
    force, torque = np.array([0.3, -0.2, 0.5]), np.array([0.01, 0.02, -0.015])   # world frame, at the COM
    data.xfrc_applied[1] = np.r_[force, torque]
    mujoco.mj_forward(model, data)

    m, inertia = model.body_mass[1], np.diag(model.body_inertia[1])   # principal axes = body axes here
    r = data.xmat[1].reshape(3, 3)
    w = data.qvel[3:6]
    lin = force / m                                                   # Newton: world-frame acceleration
    ang = np.linalg.solve(inertia, r.T @ torque - np.cross(w, inertia @ w))   # Euler, in the body frame
    print(f"  linear  qacc[0:3] MuJoCo {np.round(data.qacc[0:3], 9)}  Newton {np.round(lin, 9)}")
    print(f"  angular qacc[3:6] MuJoCo {np.round(data.qacc[3:6], 9)}  Euler  {np.round(ang, 9)}")


def collision(dampratio: float) -> tuple[float, float, float, float, float]:
    """Return momentum before/after, kinetic energy before/after, and restitution."""
    xml = model_path("two_balls").read_text().replace('solref="0.01 1"', f'solref="0.01 {dampratio}"')
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    m = model.body_mass[1:3]

    def momentum_energy():
        v = np.array([data.qvel[0:3], data.qvel[6:9]])
        return (m[:, None] * v).sum(axis=0)[0], 0.5 * float((m * (v ** 2).sum(axis=1)).sum())

    p0, e0 = momentum_energy()
    approach = data.qvel[6] - data.qvel[0]                             # relative velocity of b w.r.t. a
    for _ in range(1000):                                              # 1 s: the balls meet at about t = 0.33 s
        mujoco.mj_step(model, data)
    p1, e1 = momentum_energy()
    restitution = -(data.qvel[6] - data.qvel[0]) / approach            # e = -(separation speed) / (approach speed)
    return p0, p1, e0, e1, restitution


if __name__ == "__main__":
    print("Newton-Euler for the tumbling box under an applied wrench:")
    newton_euler()
    print("head-on collision, 1 kg at +1 m/s against 1 kg at -0.5 m/s:")
    print(f"  {'dampratio':>9} {'momentum before':>16} {'after':>10} {'KE before (J)':>14} {'after (J)':>10} {'restitution':>12}")
    for z in (1.0, 0.5, 0.2, 0.05):
        p0, p1, e0, e1, rest = collision(z)
        print(f"  {z:>9.2f} {p0:>16.6f} {p1:>10.6f} {e0:>14.4f} {e1:>10.4f} {rest:>12.3f}")
