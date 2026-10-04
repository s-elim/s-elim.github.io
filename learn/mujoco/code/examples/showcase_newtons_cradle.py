"""Showcase: a Newton's cradle, and what it takes from a soft-contact engine to reproduce the toy.

INPUT   five 0.26 kg balls of radius 2 cm, each on a 0.2 m pendulum, in a row along x, frictionless contacts
        (condim 1); the first ball lifted by 30 degrees and released
PROCESS (1) two balls colliding head-on at 1 m/s: the restitution each contact setting gives;
        (2) the cradle with three contact settings and three gaps between neighbouring balls, timestep 0.1 ms:
            each ball's velocity 30 ms after the first impact, as a fraction of the incoming speed, and the
            mechanical energy (kinetic + gravitational) left, as a fraction of the release energy;
        (3) two balls lifted together, with the setting that works
OUTPUT  printed tables

Run:  python examples/showcase_newtons_cradle.py          (about 30 seconds)
"""

import math

import mujoco
import numpy as np

R, LENGTH, N, MASS = 0.02, 0.2, 5, 0.26
SETTINGS = {"default soft contact, solref (0.02, 1)": "0.02 1",
            "less damping, solref (0.02, 0.1)": "0.02 0.1",
            "stiff spring, solref (-1e7, -10)": "-1e7 -10"}


def cradle(solref: str, gap: float, dt: float = 1e-4) -> mujoco.MjModel:
    balls = "".join(f"""
    <body name="b{i}" pos="{i * (2 * R + gap):.6f} 0 0.3">
      <joint type="hinge" axis="0 1 0"/>
      <geom type="capsule" fromto="0 0 0 0 0 {-LENGTH + R}" size="0.0015" mass="0" contype="0" conaffinity="0"/>
      <geom name="g{i}" type="sphere" pos="0 0 {-LENGTH}" size="{R}" mass="{MASS}" condim="1" solref="{solref}"/>
    </body>""" for i in range(N))
    return mujoco.MjModel.from_xml_string(f"""<mujoco><option timestep="{dt}"><flag energy="enable"/></option>
  <worldbody>{balls}</worldbody></mujoco>""")


def energy(data) -> float:
    return float(data.energy[0] + data.energy[1])


def release(model, lifted: int = 1, angle: float = 30.0, after: float = 0.03) -> tuple[np.ndarray, float]:
    """Velocities along +x (fraction of the incoming speed) `after` s past the first impact, and energy left."""
    data = mujoco.MjData(model)
    data.qpos[:lifted] = math.radians(angle)           # a positive hinge angle swings the bob toward -x
    mujoco.mj_forward(model, data)
    rest = mujoco.MjData(model)
    mujoco.mj_forward(model, rest)
    e_rest = energy(rest)
    e0 = energy(data) - e_rest
    incoming = math.sqrt(2 * 9.81 * LENGTH * (1 - math.cos(math.radians(angle))))
    first, second = model.geom(f"g{lifted - 1}").id, model.geom(f"g{lifted}").id
    hit = None
    while hit is None or data.time < hit + after:
        mujoco.mj_step(model, data)
        if hit is None and any({data.contact[i].geom1, data.contact[i].geom2} == {first, second} for i in range(data.ncon)):
            hit = data.time
        if not np.isfinite(data.qvel).all() or data.time > 2.0:
            return np.full(N, np.nan), float("nan")
    return -data.qvel * LENGTH / incoming, (energy(data) - e_rest) / e0


def head_on(solref: str, dt: float = 1e-4) -> tuple[float, float]:
    model = mujoco.MjModel.from_xml_string(f"""<mujoco><option timestep="{dt}" gravity="0 0 0"/><worldbody>
    <body><joint type="slide" axis="1 0 0"/><geom type="sphere" size="{R}" mass="{MASS}" condim="1" solref="{solref}"/></body>
    <body pos="0.05 0 0"><joint type="slide" axis="1 0 0"/><geom type="sphere" size="{R}" mass="{MASS}" condim="1" solref="{solref}"/></body>
    </worldbody></mujoco>""")
    data = mujoco.MjData(model)
    data.qvel[0] = 1.0
    for _ in range(round(0.05 / dt)):
        mujoco.mj_step(model, data)
    return float(data.qvel[0]), float(data.qvel[1])


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}; balls of {MASS} kg, radius {100 * R:.0f} cm, on {LENGTH} m pendulums; timestep 0.1 ms")
    print("(1) two balls head-on at 1 m/s: velocities after the collision, and the restitution")
    for label, solref in SETTINGS.items():
        v0, v1 = head_on(solref)
        print(f"    {label:<40} {v0:+.3f} and {v1:+.3f} m/s, restitution {v1 - v0:.3f}")
    print("(2) the cradle, first ball lifted 30 deg: velocities 30 ms after the first impact (fraction of the incoming"
          " speed, along +x) and mechanical energy left")
    for label, solref in SETTINGS.items():
        for gap in (0.0, 0.0001, 0.001):
            v, e = release(cradle(solref, gap))
            print(f"    {label:<40} gap {1000 * gap:3.1f} mm: " + " ".join(f"{x:+.3f}" for x in v) + f"   energy {e:.3f}")
    print("(3) two balls lifted together, stiff spring, gap 1.0 mm")
    v, e = release(cradle(SETTINGS["stiff spring, solref (-1e7, -10)"], 0.001), lifted=2)
    print("    " + " ".join(f"{x:+.3f}" for x in v) + f"   energy {e:.3f}")
