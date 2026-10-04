"""Lesson 20.3: where a step's time goes, and how to spend more cores on it (Level 20).

INPUT   pendulum, cart-pole, arm7, pick_place (after 0.5 s), and heaps of 50 and 200 boxes in a bin; a scene of 16
        separate piles of 12 boxes (16 constraint islands) and one heap of 192 boxes (one island)
PROCESS (1) MuJoCo's timers (mjData.timer) over 500 steps of each model: microseconds per stage and their share;
        (2) mju_threadpool on one mjData: time per step with 1 to 16 threads, for 16 islands and for one;
        (3) mujoco.rollout of 1000 pick_place trajectories (200 steps) on 1 to 32 threads: steps per second and
            the efficiency against one thread
OUTPUT  printed tables (absolute times depend on the machine and its load; this one is shared)

Run:  python examples/l20_3_performance.py          (about 2 minutes)
"""

import os
import time

import mujoco
import mujoco.rollout
import numpy as np

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"
SIDE = 0.025
STAGES = ["POS_KINEMATICS", "POS_INERTIA", "POS_COLLISION", "POS_MAKE", "POS_PROJECT", "VELOCITY", "ACTUATION",
          "CONSTRAINT", "ADVANCE"]


def box(x: float, y: float, z: float, yaw: float = 0.0) -> str:
    return (f'<body pos="{x:.3f} {y:.3f} {z:.3f}" euler="0 0 {yaw:.0f}"><freejoint/>'
            f'<geom type="box" size="{SIDE} {SIDE} {SIDE}" mass="0.1"/></body>')


def heap(n: int) -> mujoco.MjModel:
    rng, side = np.random.default_rng(0), int(np.ceil(np.sqrt(n / 4)))
    boxes = "".join(box((i % side - side / 2) * 0.06, ((i // side) % side - side / 2) * 0.06, 0.1 + 0.06 * (i // side**2),
                        rng.uniform(0, 90)) for i in range(n))
    wall = side * 0.035 + 0.05
    walls = "".join(f'<geom type="box" size="{sx} {sy} 0.15" pos="{px} {py} 0.15"/>' for sx, sy, px, py in
                    ((0.01, wall, wall, 0), (0.01, wall, -wall, 0), (wall, 0.01, 0, wall), (wall, 0.01, 0, -wall)))
    return mujoco.MjModel.from_xml_string(f'<mujoco><worldbody><geom type="plane" size="3 3 0.1"/>{walls}{boxes}'
                                          '</worldbody></mujoco>')


def piles(n_piles: int, per_pile: int) -> mujoco.MjModel:
    """Separate piles far apart: no contact between piles, so each is its own constraint island."""
    grid = int(np.ceil(np.sqrt(n_piles)))
    boxes = "".join(box((p % grid) * 0.5 + 0.004 * (k % 2), (p // grid) * 0.5, SIDE + 2 * SIDE * k, 10 * k)
                    for p in range(n_piles) for k in range(per_pile))
    return mujoco.MjModel.from_xml_string(f'<mujoco><worldbody><geom type="plane" size="5 5 0.1"/>{boxes}</worldbody></mujoco>')


def library(name: str, key: int | None = None, settle: float = 0.0) -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(model_path(name)))
    data = mujoco.MjData(model)
    if key is not None:
        mujoco.mj_resetDataKeyframe(model, data, key)
    while data.time < settle:
        mujoco.mj_step(model, data)
    return model, data


def settled(model: mujoco.MjModel, seconds: float) -> tuple[mujoco.MjModel, mujoco.MjData]:
    data = mujoco.MjData(model)
    while data.time < seconds:
        mujoco.mj_step(model, data)
    return model, data


def profile(model, data, steps: int = 500) -> tuple[float, dict]:
    for t in data.timer:
        t.duration, t.number = 0.0, 0
    for _ in range(steps):
        mujoco.mj_step(model, data)
    step = data.timer[mujoco.mjtTimer.mjTIMER_STEP]
    per_step = 1e6 * step.duration / max(step.number, 1)
    stages = {s: 1e6 * data.timer[getattr(mujoco.mjtTimer, f"mjTIMER_{s}")].duration / max(step.number, 1) for s in STAGES}
    return per_step, stages


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}; {os.cpu_count()} logical CPUs (shared machine)")
    print("(1) mjData.timer, microseconds per step and share of the step")
    scenes = [("pendulum", *library("pendulum")), ("cart-pole", *library("cartpole")),
              ("arm7", *library("arm7", key=0)), ("pick_place", *library("pick_place", key=0, settle=0.5)),
              ("heap of 50", *settled(heap(50), 1.5))]
    if not FAST:
        scenes.append(("heap of 200", *settled(heap(200), 1.5)))
    short = {"POS_KINEMATICS": "kin", "POS_INERTIA": "inertia", "POS_COLLISION": "collision", "POS_MAKE": "make",
             "POS_PROJECT": "project", "VELOCITY": "velocity", "ACTUATION": "actuation", "CONSTRAINT": "constraint",
             "ADVANCE": "advance"}
    print(f"    {'model':<12}{'nv':>5}{'ncon':>6}{'step us':>9}  " + "".join(f"{short[s]:>11}" for s in STAGES))
    for label, model, data in scenes:
        per_step, stages = profile(model, data)
        cells = "".join(f"{100 * v / per_step:>10.1f}%" for v in stages.values())
        print(f"    {label:<12}{model.nv:>5}{data.ncon:>6}{per_step:>9.1f}  {cells}")
    print("(2) mju_threadpool on one mjData: milliseconds per step")
    for label, model in (("16 piles of 12 boxes", piles(16, 12)), ("one heap of 192 boxes", heap(192))):
        _, base = settled(model, 1.0)
        cells = []
        for threads in ((1, 4) if FAST else (1, 2, 4, 8, 16)):
            data = mujoco.MjData(model)
            data.qpos[:], data.qvel[:] = base.qpos, base.qvel
            if threads > 1:
                mujoco.mju_threadpool(data, threads)
            mujoco.mj_forward(model, data)
            t0, steps = time.perf_counter(), 200
            for _ in range(steps):
                mujoco.mj_step(model, data)
            cells.append(f"{threads} threads {1000 * (time.perf_counter() - t0) / steps:.2f}")
        print(f"    {label:<22} (nv {model.nv}, islands {base.nisland}): " + ", ".join(cells))
    print("(3) mujoco.rollout, 1000 pick_place trajectories of 200 steps")
    model, data = library("pick_place", key=0)
    state = np.empty(mujoco.mj_stateSize(model, mujoco.mjtState.mjSTATE_FULLPHYSICS))
    mujoco.mj_getState(model, data, state, mujoco.mjtState.mjSTATE_FULLPHYSICS)
    n, nstep = (100, 50) if FAST else (1000, 200)
    states = np.tile(state, (n, 1))
    controls = np.tile(data.ctrl, (n, nstep, 1))
    base_rate = None
    for threads in ((1, 8) if FAST else (1, 2, 4, 8, 16, 32)):
        datas = [mujoco.MjData(model) for _ in range(threads)]          # one MjData per thread
        t0 = time.perf_counter()
        mujoco.rollout.rollout(model, datas, states, controls)
        rate = n * nstep / (time.perf_counter() - t0)
        base_rate = base_rate or rate
        print(f"    {threads:>3} threads: {rate:>11,.0f} steps/s, {rate / base_rate:5.2f}x one thread, "
              f"efficiency {rate / base_rate / threads:5.0%}")
