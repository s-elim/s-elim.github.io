"""Lesson 0.1: drop two balls of different mass and time their fall.

INPUT   ball_drop.xml: a 2.0 kg and a 0.1 kg ball, centres released at z = 1.0 m
PROCESS step until each ball's first contact with the floor, then let them settle
OUTPUT  touchdown time and speed per ball, the analytic values for comparison,
        and the resting penetration depth of each ball into the floor

Run:  python examples/l0_1_ball_drop.py
"""

import math

import mujoco

from mjcourse import model_path

G, DROP = 9.81, 0.95   # the ball's lowest point falls 1.0 - 0.05 m before touching


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("ball_drop")))
    data = mujoco.MjData(model)
    floor = model.geom("floor").id
    touchdown = {}
    while len(touchdown) < 2:
        speeds = {name: -data.joint(f"{name}_free").qvel[2] for name in ("heavy", "light")}
        mujoco.mj_step(model, data)
        for c in data.contact[: data.ncon]:
            if floor in (c.geom1, c.geom2):
                other = c.geom2 if c.geom1 == floor else c.geom1
                name = model.geom(other).name.removesuffix("_geom")
                # Report the time and speed at the start of the step in which contact appeared.
                touchdown.setdefault(name, (data.time - model.opt.timestep, speeds[name]))
    t_exact, v_exact = math.sqrt(2 * DROP / G), math.sqrt(2 * G * DROP)
    print(f"analytic: t = {t_exact:.4f} s, v = {v_exact:.3f} m/s")
    for name, (t, v) in touchdown.items():
        print(f"{name:>5}: t = {t:.4f} s, v = {v:.3f} m/s")

    for _ in range(1500):                     # 3 s more: let both balls come to rest
        mujoco.mj_step(model, data)
    for name in ("heavy", "light"):
        z = data.body(name).xpos[2]
        print(f"{name:>5} at rest: centre z = {z:.5f} m, penetration = {1e3 * (0.05 - z):.3f} mm")


if __name__ == "__main__":
    main()
