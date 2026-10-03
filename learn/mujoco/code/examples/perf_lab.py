"""Performance lab: how simulation throughput scales from 1 to 1000 environments.

INPUT   cartpole.xml (2 DOF, no contacts) and pick_place.xml (27 DOF, contacts)
PROCESS for N = 1, 10, 100, 1000 environments: step each for a fixed number of steps
        (a) in a Python loop, (b) with mujoco.rollout over 1 and 8 threads; measure
        wall time, CPU time and memory per MjData; profile one step with MuJoCo's
        timers; optionally time offscreen rendering
OUTPUT  a table of steps per second and CPU utilization per configuration

Run:  python examples/perf_lab.py            (MUJOCO_GL=egl or osmesa adds a render row)
Timings depend on the machine; the shape of the table is what transfers.
"""

import os
import time

import mujoco
import mujoco.rollout
import numpy as np

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"
NSTEP = 50 if FAST else 200
COUNTS = (1, 10, 100) if FAST else (1, 10, 100, 1000)


def initial_states(model: mujoco.MjModel, n: int, key: int | None) -> np.ndarray:
    data = mujoco.MjData(model)
    if key is not None:
        mujoco.mj_resetDataKeyframe(model, data, key)
    spec = mujoco.mjtState.mjSTATE_FULLPHYSICS
    state = np.empty(mujoco.mj_stateSize(model, spec))
    mujoco.mj_getState(model, data, state, spec)
    return np.tile(state, (n, 1))


def python_loop(model, states) -> tuple[float, float]:
    datas = [mujoco.MjData(model) for _ in range(len(states))]
    for d, s in zip(datas, states):
        mujoco.mj_setState(model, d, s, mujoco.mjtState.mjSTATE_FULLPHYSICS)
    w, c = time.perf_counter(), time.process_time()
    for _ in range(NSTEP):
        for d in datas:
            mujoco.mj_step(model, d)
    return time.perf_counter() - w, time.process_time() - c


def rollout(model, states, nthread: int) -> tuple[float, float]:
    datas = [mujoco.MjData(model) for _ in range(nthread)]
    controls = np.zeros((len(states), NSTEP, model.nu))
    w, c = time.perf_counter(), time.process_time()
    mujoco.rollout.rollout(model, datas, states, controls)
    return time.perf_counter() - w, time.process_time() - c


def profile(model: mujoco.MjModel, key: int) -> None:
    """Where one step's time goes, from MuJoCo's own timers (data.timer)."""
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, key)
    for _ in range(1000):
        mujoco.mj_step(model, data)
    step = data.timer[mujoco.mjtTimer.mjTIMER_STEP]
    total = step.duration / step.number
    for name in ("POS_KINEMATICS", "POS_INERTIA", "POS_COLLISION", "POS_MAKE", "VELOCITY", "ACTUATION",
                 "CONSTRAINT", "ADVANCE"):
        t = data.timer[getattr(mujoco.mjtTimer, f"mjTIMER_{name}")]
        per = t.duration / max(t.number, 1)
        print(f"  {name.lower():<15s} {1e6 * per:7.2f} us  {100 * per / total:5.1f} %")
    print(f"  {'whole step':<15s} {1e6 * total:7.2f} us")


def main() -> None:
    print(f"MuJoCo {mujoco.__version__}, {os.cpu_count()} logical CPUs, {NSTEP} steps per environment")
    for name, key in (("cartpole", None), ("pick_place", 1)):
        model = mujoco.MjModel.from_xml_path(str(model_path(name)))
        data = mujoco.MjData(model)
        mem = (data.nbuffer + model.narena) / 2**20
        print(f"\n{name}: nv={model.nv}, timestep {model.opt.timestep} s, memory per MjData {mem:.1f} MiB "
              f"(buffer {data.nbuffer / 2**20:.2f} + arena {model.narena / 2**20:.2f})")
        print(f"  {'N':>5} {'method':<20} {'steps/s':>12} {'x real time':>12} {'CPU/wall':>9}")
        for n in COUNTS:
            states = initial_states(model, n, key)
            rows = [("python loop", python_loop(model, states))]
            rows += [(f"rollout, {t} thread{'s' if t > 1 else ''}", rollout(model, states, t)) for t in (1, 8)]
            for label, (wall, cpu) in rows:
                sps = n * NSTEP / wall
                print(f"  {n:>5} {label:<20} {sps:>12,.0f} {sps * model.opt.timestep:>12,.1f} {cpu / wall:>9.2f}")
        if name == "pick_place":
            print("  profile of one step (mean over 1000 steps):")
            profile(model, 1)
            try:
                renderer = mujoco.Renderer(model, 240, 320)
                mujoco.mj_resetDataKeyframe(model, data, 1)
                mujoco.mj_forward(model, data)
                w = time.perf_counter()
                for _ in range(20):
                    renderer.update_scene(data, "front")
                    renderer.render()
                fps = 20 / (time.perf_counter() - w)
                renderer.close()
                print(f"  render 320x240 RGB, MUJOCO_GL={os.environ.get('MUJOCO_GL', 'default')}: {fps:.0f} frames/s")
            except Exception as err:  # noqa: BLE001
                print(f"  render: unavailable ({type(err).__name__})")


if __name__ == "__main__":
    main()
