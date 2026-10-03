"""Lesson 9.4: why simulations explode, how to tell, and what the fixes cost.

INPUT   small scenes written below; pick_place.xml for the cost of fixes
PROCESS (1) a 1 kg mass on a spring: largest stable omega * h for five integrators,
            and how much each damps the oscillation;
        (2) a small ball fired at a thin wall: tunnelling (no contact ever detected)
            versus soft push-through (detected but too soft to stop it), and the fixes;
        (3) a box that starts inside the floor: ejection speed for two contact stiffnesses;
        (4) what MuJoCo does when a simulation diverges: the warning, the automatic reset;
        (5) the cost of the fixes: microseconds per step of pick_place.xml for each
            integrator and timestep
OUTPUT  printed tables

Run:  python examples/l9_4_stability.py
"""

import math
import os
import time

import mujoco
import numpy as np

from mjcourse import model_path

SPRING = """<mujoco><option timestep="0.002" gravity="0 0 0" integrator="{integ}"/><worldbody>
<body><joint type="slide" axis="1 0 0" stiffness="{k}"/><geom size="0.05" mass="1"/></body></worldbody></mujoco>"""
WALL = """<mujoco><option timestep="{h}" gravity="0 0 0"/><worldbody>
<geom name="wall" type="box" size="{t} 0.3 0.3" pos="0.25 0 0" solref="{tc} 1"/>
<body pos="0 0 0"><freejoint/><geom name="ball" size="0.01" mass="0.01" solref="{tc} 1"/></body></worldbody></mujoco>"""
OVERLAP = """<mujoco><option timestep="0.002"/><worldbody><geom type="plane" size="1 1 .1" solref="{tc} 1"/>
<body pos="0 0 {z}"><freejoint/><geom type="box" size=".05 .05 .05" mass="1" solref="{tc} 1"/></body></worldbody></mujoco>"""


def spring_stability() -> None:
    stiffness = (1e4, 5e5, 9e5, 1.1e6, 2e6, 4e6)
    print("  " + " " * 13 + "".join(f"{f'wh {math.sqrt(k) * 0.002:.2f}':>12}" for k in stiffness))
    for integ in ("Euler", "implicitfast", "implicit", "RK4", "discrete"):
        cells = []
        for k in stiffness:
            model = mujoco.MjModel.from_xml_string(SPRING.format(integ=integ, k=k))
            data = mujoco.MjData(model)
            data.qpos[0] = 0.01
            peak = 0.0
            for i in range(2000):                          # 4 s
                mujoco.mj_step(model, data)
                if i >= 1750:                              # amplitude over the last 0.5 s
                    peak = max(peak, abs(data.qpos[0]))
            diverged = data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number > 0
            cells.append("diverged" if diverged else f"{peak / 0.01:.3f}")
        print(f"  {integ:<13}" + "".join(f"{c:>12}" for c in cells))
    print("  (cells: amplitude after 4 s divided by the initial 10 mm; 1.000 means no numerical damping)")


def wall(v: float, half: float, h: float, tc: float) -> str:
    model = mujoco.MjModel.from_xml_string(WALL.format(h=h, t=half, tc=tc))
    data = mujoco.MjData(model)
    data.qvel[0] = v
    touched = False
    for _ in range(round(0.5 / h)):
        mujoco.mj_step(model, data)
        touched |= data.ncon > 0
    if data.qpos[0] < 0.25:
        return "stopped" if touched else "never arrived"
    return "push-through" if touched else "tunnelled"


def wall_table() -> None:
    speeds = (1, 5, 20, 100)
    cases = [("2 mm wall, h 2 ms, timeconst 0.02", 0.001, 0.002, 0.02),
             ("2 mm wall, h 0.5 ms, timeconst 0.02", 0.001, 0.0005, 0.02),
             ("2 mm wall, h 0.5 ms, timeconst 0.001", 0.001, 0.0005, 0.001),
             ("20 mm wall, h 0.5 ms, timeconst 0.001", 0.01, 0.0005, 0.001)]
    print("  " + " " * 40 + "".join(f"{f'{v} m/s':>14}" for v in speeds))
    for label, half, h, tc in cases:
        print(f"  {label:<40}" + "".join(f"{wall(v, half, h, tc):>14}" for v in speeds))


def overlap() -> None:
    for tc in (0.02, 0.004):
        cells = []
        for depth in (0.001, 0.005, 0.02):
            model = mujoco.MjModel.from_xml_string(OVERLAP.format(tc=tc, z=0.05 - depth))
            data = mujoco.MjData(model)
            vmax = zmax = 0.0
            for _ in range(500):
                mujoco.mj_step(model, data)
                vmax, zmax = max(vmax, data.qvel[2]), max(zmax, data.qpos[2])
            cells.append(f"{1000 * depth:g} mm: {vmax:.2f} m/s, {max(0.0, 1000 * (zmax - 0.05)):.0f} mm up")
        print(f"  timeconst {tc:<6} " + "   ".join(cells))


def divergence() -> None:
    model = mujoco.MjModel.from_xml_string(SPRING.format(integ="Euler", k=4e6))
    data = mujoco.MjData(model)
    data.qpos[0] = 0.01
    first = None
    for i in range(1000):
        mujoco.mj_step(model, data)
        w = data.warning[mujoco.mjtWarning.mjWARN_BADQACC]
        if w.number and first is None:
            first = (i + 1, w.lastinfo, data.time, data.qpos[0])
    w = data.warning[mujoco.mjtWarning.mjWARN_BADQACC]
    print(f"  first bad-acceleration warning during step {first[0]} (lastinfo = dof {first[1]}); MuJoCo reset the state "
          f"to qpos0 and continued: time {first[2]:.3f} s, qpos {first[3]:.3g} (it started at 0.01)")
    print(f"  after 1000 steps: {w.number} warnings in total, time {data.time:.3f} s (the clock restarts at every reset)")
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_AUTORESET
    data = mujoco.MjData(model)
    data.qpos[0] = 0.01
    for _ in range(1000):
        mujoco.mj_step(model, data)
    print(f"  with autoreset disabled: time {data.time:.3f} s, qpos {data.qpos[0]:.3g}, finite {bool(np.isfinite(data.qpos[0]))}")


def cost() -> None:
    reps = 300 if os.environ.get("MJC_FAST") == "1" else 3000
    base = None
    for integ in ("mjINT_EULER", "mjINT_IMPLICITFAST", "mjINT_IMPLICIT", "mjINT_RK4", "mjINT_DISCRETE"):
        model = mujoco.MjModel.from_xml_path(str(model_path("pick_place")))
        model.opt.integrator = getattr(mujoco.mjtIntegrator, integ)
        data = mujoco.MjData(model)
        mujoco.mj_resetDataKeyframe(model, data, 1 if model.nkey > 1 else 0)
        for _ in range(200):
            mujoco.mj_step(model, data)
        iters = 0
        t0 = time.perf_counter()
        for _ in range(reps):
            mujoco.mj_step(model, data)
            iters += data.solver_niter[0]
        us = 1e6 * (time.perf_counter() - t0) / reps
        base = base or us
        print(f"  {integ[6:].lower():<13} {us:7.1f} us per step ({us / base:.2f} x Euler), {iters / reps:.2f} solver iterations "
              f"per step; per simulated second {500 * us / 1000:.1f} ms at h = 2 ms, {1000 * us / 1000:.1f} ms at h = 1 ms")
    print("  (timings on this machine)")


if __name__ == "__main__":
    print("(1) a 1 kg mass on a spring, h = 2 ms: amplitude ratio after 4 s, by integrator and omega h")
    spring_stability()
    print("(2) a 1 cm ball (10 g) fired at a wall 0.25 m away, gravity off: what happens within 0.5 s")
    wall_table()
    print("(3) a 1 kg box starting inside the floor: peak upward speed and how far it flies")
    overlap()
    print("(4) what happens when a step diverges (the stiff spring of (1) under Euler, wh = 4)")
    divergence()
    print("(5) the cost of the fixes: pick_place.xml")
    cost()
