"""Showcase: a cloth dropped over a ball, and a contact limit that decides whether it stays on top.

INPUT   a square flexcomp cloth (dim 2, edges held by equality constraints, vertex radius 6 mm, 0.1 kg),
        0.03 m between vertices, released 0.3 m above a floor with a ball of radius 8 cm on it
PROCESS (1) cloths of 6 x 6 to 20 x 20 vertices: after 3 s, the contacts by geom, the vertices touching or
            inside the floor or the ball (closer than their radius), the deepest penetration, and the cost
            of a step;
        (2) two separate 14 x 14 cloths on the floor: the contacts of each
OUTPUT  printed tables; mujoco.mjMAXCONPAIR

Run:  python examples/showcase_cloth.py          (about 30 seconds)
"""

import collections
import time

import mujoco
import numpy as np

R_VERT, R_BALL, SPACING = 0.006, 0.08, 0.03


def cloth(name: str, n: int, x: float = 0.0) -> str:
    return f"""
      <flexcomp name="{name}" type="grid" count="{n} {n} 1" spacing="{SPACING} {SPACING} {SPACING}" pos="{x} 0 0.3"
                radius="{R_VERT}" dim="2" mass="0.1">
        <contact condim="3" solref="0.01 1" selfcollide="none"/>
        <edge equality="true" damping="0.001"/>
      </flexcomp>"""


def scene(cloths: str, ball: bool = True) -> mujoco.MjModel:
    sphere = f'<geom name="ball" type="sphere" size="{R_BALL}" pos="0 0 {R_BALL}"/>' if ball else ""
    return mujoco.MjModel.from_xml_string(f"""<mujoco>
  <option timestep="0.002" solver="CG" tolerance="1e-6" integrator="implicitfast"/>
  <worldbody><geom name="floor" type="plane" size="2 2 0.1"/>{sphere}{cloths}</worldbody></mujoco>""")


def settle(model, seconds: float = 3.0) -> tuple[mujoco.MjData, float]:
    data = mujoco.MjData(model)
    t0 = time.perf_counter()
    for _ in range(round(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)
    return data, (time.perf_counter() - t0) / round(seconds / model.opt.timestep)


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}; mujoco.mjMAXCONPAIR = {mujoco.mjMAXCONPAIR}")
    print("(1) one cloth over the ball, after 3 s")
    print(f"    {'vertices':>9} {'side':>7}   {'contacts: floor, ball':>22}   {'vertices touching or inside':>28}   "
          f"{'deepest into floor, ball':>25}   {'step':>8}")
    for n in (6, 8, 10, 14, 20):
        model = scene(cloth("cloth", n))
        data, per = settle(model)
        ball = model.geom("ball").id
        by = collections.Counter("ball" if ball in (int(data.contact[i].geom[0]), int(data.contact[i].geom[1])) else "floor"
                                 for i in range(data.ncon))
        v = data.flexvert_xpos
        into_floor = R_VERT - v[:, 2]
        into_ball = R_BALL + R_VERT - np.linalg.norm(v - [0.0, 0.0, R_BALL], axis=1)
        touching = int(np.sum((into_floor > 0) | (into_ball > 0)))
        print(f"    {n * n:>9} {SPACING * (n - 1):>6.2f}m   {by['floor']:>12}, {by['ball']:>3}   {touching:>28}   "
              f"{1000 * max(into_floor.max(), 0):>14.1f} mm, {1000 * max(into_ball.max(), 0):.1f} mm   {1000 * per:>5.2f} ms")
    print("(2) two separate 14 x 14 cloths on the floor, no ball")
    model = scene(cloth("a", 14, -0.4) + cloth("b", 14, 0.4), ball=False)
    data, _ = settle(model)
    by_flex = collections.Counter(int(data.contact[i].flex[1]) for i in range(data.ncon))
    print(f"    contacts: {data.ncon} in total; cloth a {by_flex[0]}, cloth b {by_flex[1]}")
