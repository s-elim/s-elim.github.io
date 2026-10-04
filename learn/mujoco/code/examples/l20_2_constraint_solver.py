"""Lesson 20.2: the constraint solver, PGS, CG and Newton, measured (Level 20).

INPUT   a tower of 10 boxes (5 cm cubes, 0.1 kg, stacked on a floor) and a heap of N boxes dropped into a bin;
        MuJoCo 3.14.0 defaults: Newton, 100 iterations, tolerance 1e-8, pyramidal cones, warmstart on
PROCESS (1) one state of the tower after 1 s: each solver started cold (warmstart disabled) and stopped after
            k iterations; the error of qacc against Newton run to convergence, and mjData.solver's statistics;
        (2) iterations per step with and without warmstart over 2 s of the tower;
        (3) a box resting on a 20 degree slope with friction 0.5, each solver limited to a few iterations: how far
            it slides in 5 s;
        (4) cost: milliseconds per step and iterations per step for the tower and for heaps of 50 and 200 boxes
OUTPUT  printed tables

Run:  python examples/l20_2_constraint_solver.py          (about 1 minute)
"""

import math
import os
import time

import mujoco
import numpy as np

FAST = os.environ.get("MJC_FAST") == "1"
SOLVERS = {"PGS": mujoco.mjtSolver.mjSOL_PGS, "CG": mujoco.mjtSolver.mjSOL_CG, "Newton": mujoco.mjtSolver.mjSOL_NEWTON}
SIDE = 0.025                                                    # box half-size


def tower(n: int = 10) -> mujoco.MjModel:
    boxes = "".join(f"""
    <body pos="0 0 {SIDE + 2 * SIDE * i:.4f}"><freejoint/>
      <geom type="box" size="{SIDE} {SIDE} {SIDE}" mass="0.1" rgba="{0.3 + 0.07 * i:.2f} .45 .7 1"/></body>"""
                    for i in range(n))
    return mujoco.MjModel.from_xml_string(f"""<mujoco><option timestep="0.002"/>
  <worldbody><geom type="plane" size="1 1 0.1"/>{boxes}</worldbody></mujoco>""")


def slope(angle: float = 20.0, mu: float = 0.5) -> mujoco.MjModel:
    """A box resting on a plane tilted by `angle` degrees about y."""
    a = math.radians(angle)
    return mujoco.MjModel.from_xml_string(f"""<mujoco><option timestep="0.002"/><worldbody>
  <geom type="plane" size="1 1 0.1" euler="0 {-angle} 0" friction="{mu}"/>
  <body pos="0 0 {SIDE / math.cos(a):.5f}" euler="0 {-angle} 0"><freejoint/>
    <geom type="box" size="{SIDE} {SIDE} {SIDE}" mass="0.1" friction="{mu}"/></body></worldbody></mujoco>""")


def heap(n: int) -> mujoco.MjModel:
    rng = np.random.default_rng(0)
    side = int(np.ceil(np.sqrt(n / 4)))
    boxes = "".join(f"""
    <body pos="{(i % side - side / 2) * 0.06:.3f} {((i // side) % side - side / 2) * 0.06:.3f} {0.1 + 0.06 * (i // side ** 2):.3f}"
          euler="{rng.uniform(0, 90):.0f} {rng.uniform(0, 90):.0f} 0"><freejoint/>
      <geom type="box" size="{SIDE} {SIDE} {SIDE}" mass="0.1"/></body>""" for i in range(n))
    wall = side * 0.035 + 0.05
    walls = "".join(f'<geom type="box" size="{sx} {sy} 0.15" pos="{px} {py} 0.15"/>' for sx, sy, px, py in
                    ((0.01, wall, wall, 0), (0.01, wall, -wall, 0), (wall, 0.01, 0, wall), (wall, 0.01, 0, -wall)))
    return mujoco.MjModel.from_xml_string(f"""<mujoco><option timestep="0.002"/>
  <worldbody><geom type="plane" size="2 2 0.1"/>{walls}{boxes}</worldbody></mujoco>""")


def settle(model: mujoco.MjModel, seconds: float) -> mujoco.MjData:
    data = mujoco.MjData(model)
    while data.time < seconds:
        mujoco.mj_step(model, data)
    return data


def solve_once(model, state_data, solver: str, iterations: int, tolerance: float = 0.0):
    """qacc, qacc_smooth and solver statistics from one cold-started forward pass of the given state."""
    model.opt.solver, model.opt.iterations, model.opt.tolerance = SOLVERS[solver], iterations, tolerance
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_WARMSTART
    data = mujoco.MjData(model)
    data.qpos[:], data.qvel[:] = state_data.qpos, state_data.qvel
    mujoco.mj_forward(model, data)
    stats = [(data.solver[i].improvement, data.solver[i].gradient) for i in range(data.solver_niter[0])]
    model.opt.disableflags &= ~int(mujoco.mjtDisableBit.mjDSBL_WARMSTART)
    return data.qacc.copy(), data.solver_niter[0], stats, data.qacc_smooth.copy()


if __name__ == "__main__":
    model = tower()
    state = settle(model, 1.0)
    print(f"MuJoCo {mujoco.__version__}; tower of 10 boxes after 1 s: nv {model.nv}, ncon {state.ncon}, nefc {state.nefc}, "
          f"islands {state.nisland}")
    print("(1) one state, cold start: the share of the constraint correction still missing after k iterations,")
    print("    |qacc - qacc*| / |qacc_smooth - qacc*|, with qacc* from Newton run to convergence")
    reference, n_ref, _, smooth = solve_once(model, state, "Newton", 200, 1e-14)
    scale = np.linalg.norm(smooth - reference)
    ks = (1, 2, 5, 10, 20, 50, 100)
    print(f"    reference: Newton, {n_ref} iteration(s); |qacc_smooth - qacc*| = {scale:.2f}")
    print("    " + f"{'k':>8}" + "".join(f"{k:>10}" for k in ks))
    for name in SOLVERS:
        errs = [np.linalg.norm(solve_once(model, state, name, k)[0] - reference) / scale for k in ks]
        print(f"    {name:>8}" + "".join(f"{e:>10.1e}" for e in errs))
    _, n_newton, stats, _ = solve_once(model, state, "Newton", 100, 1e-8)
    print(f"    Newton at the default tolerance 1e-8 stops after {n_newton} iterations; mjData.solver per iteration "
          "(improvement, gradient): " + "; ".join(f"{i:.1e}, {g:.1e}" for i, g in stats))
    print("(2) iterations per step over 2 s of the tower, default tolerance")
    for name in SOLVERS:
        cells = []
        for warm in (True, False):
            m = tower()
            m.opt.solver = SOLVERS[name]
            if not warm:
                m.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_WARMSTART
            d = mujoco.MjData(m)
            iters = []
            while d.time < 2.0:
                mujoco.mj_step(m, d)
                iters.append(d.solver_niter[0])
            cells.append(f"{'warmstart' if warm else 'cold start'} mean {np.mean(iters[250:]):5.1f}, max {max(iters[250:]):3d}")
        print(f"    {name:>8}: " + "; ".join(cells))
    print("(3) a box on a 20 degree slope with friction 0.5 (tan 20 deg = 0.36: it should stay): distance slid in 5 s")
    for name, iterations in (("PGS", 2), ("PGS", 5), ("PGS", 20), ("PGS", 100), ("CG", 2), ("CG", 5), ("CG", 100),
                             ("Newton", 1), ("Newton", 100)):
        m = slope()
        m.opt.solver, m.opt.iterations = SOLVERS[name], iterations
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        start = d.xpos[1].copy()
        while d.time < (2.0 if FAST else 5.0):
            mujoco.mj_step(m, d)
        print(f"    {name:>8}, {iterations:>3} iterations: {1000 * np.linalg.norm(d.xpos[1] - start):8.3f} mm")
    print("(4) cost per step, default settings (iterations used, time)")
    scenes = [("tower of 10", tower(), 1.0)] + [(f"heap of {n}", heap(n), 1.5) for n in ((50,) if FAST else (50, 200))]
    for label, m0, seconds in scenes:
        cells = []
        for name in SOLVERS:
            m0.opt.solver = SOLVERS[name]
            d = settle(m0, seconds)
            t0, iters, steps = time.perf_counter(), [], 300
            for _ in range(steps):
                mujoco.mj_step(m0, d)
                iters.append(sum(d.solver_niter[:max(d.nisland, 1)]))
            cells.append(f"{name} {1000 * (time.perf_counter() - t0) / steps:.3f} ms ({np.mean(iters):.1f} it)")
        print(f"    {label:<12} nv {m0.nv:>4}, nefc {d.nefc:>5}: " + ", ".join(cells))
