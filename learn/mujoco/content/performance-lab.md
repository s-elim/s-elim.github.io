How fast MuJoCo runs decides which experiments are affordable: how many episodes an evaluation can have, how many samples a planner can roll out per decision, how long a training run takes. This lab measures throughput from 1 to 1000 simulations, in Python and in this browser, and shows where the time inside one step goes. Level 20.3 builds on it.

## In this browser

The benchmark below steps 1, 10, 100 and 1000 independent copies of a model on MuJoCo's single-threaded WebAssembly build, for about a second each, and reports steps per second.

```lab perf
{}
```

> [!implementation] Why the benchmark sets the arena size
> MuJoCo preallocates each `mjData`'s arena from a compile-time estimate. For the course's cart-pole and pick-and-place models that estimate is 13 and 14 MiB per `mjData`, while the course measured the actual peak use (`data.maxuse_arena`) at 0.3 KiB and 73 KiB. A thousand environments at the default would reserve over 13 GB, far beyond the 2 GB WebAssembly heap. The benchmark therefore compiles each model with `<size memory="512K"/>`. The same advice applies to Python when you run many environments: measure `maxuse_arena` once, then set `memory` with a margin.

## In Python

```io
INPUT: `cartpole.xml` (2 DOF, no contacts) and `pick_place.xml` (27 DOF, contacts)
PROCESS: step N = 1 to 1000 environments 200 steps each, in a Python loop and with `mujoco.rollout` on 1 and 8 threads; profile one step with MuJoCo's timers; time offscreen rendering
OUTPUT: steps per second, multiples of real time, CPU utilization, and a per-stage profile
```

```python file=examples/perf_lab.py
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
```
One run on the course's build machine, a shared 48-core Linux server, with `MUJOCO_GL=osmesa` (software rendering):

```text
cartpole: nv=2, timestep 0.002 s, memory per MjData 13.0 MiB (buffer 0.01 + arena 13.00)
      N method                    steps/s  x real time  CPU/wall
      1 python loop               362,341        724.7      1.00
      1 rollout, 1 thread         298,543        597.1      1.00
      1 rollout, 8 threads        114,001        228.0      2.80
     10 python loop               389,848        779.7      1.00
     10 rollout, 8 threads        572,095      1,144.2      4.32
    100 python loop               386,628        773.3      1.00
    100 rollout, 8 threads      2,086,872      4,173.7      7.36
   1000 python loop               523,379      1,046.8      1.00
   1000 rollout, 8 threads      3,069,888      6,139.8      7.51

pick_place: nv=27, timestep 0.002 s, memory per MjData 14.0 MiB (buffer 0.03 + arena 14.00)
      N method                    steps/s  x real time  CPU/wall
      1 python loop                39,735         79.5      1.00
      1 rollout, 8 threads         43,754         87.5      1.24
     10 python loop                48,531         97.1      1.00
     10 rollout, 8 threads        117,733        235.5      5.39
    100 python loop                28,187         56.4      1.00
    100 rollout, 1 thread          48,938         97.9      1.00
    100 rollout, 8 threads        229,804        459.6      7.66
   1000 python loop                37,552         75.1      1.00
   1000 rollout, 8 threads        230,345        460.7      7.78
  profile of one step (mean over 1000 steps):
  pos_kinematics     1.14 us    4.9 %
  pos_inertia        0.37 us    1.6 %
  pos_collision      4.68 us   20.2 %
  pos_make           3.80 us   16.5 %
  velocity           1.12 us    4.9 %
  actuation          0.15 us    0.6 %
  constraint        10.04 us   43.5 %
  advance            1.19 us    5.2 %
  whole step        23.09 us
  render 320x240 RGB, MUJOCO_GL=osmesa: 27 frames/s
```

(Some rows are omitted for width; the script prints all of them.)

> [!warning] Absolute numbers on a shared machine are noisy
> On this machine, two runs of the same script gave pick-and-place single-step times of 39 µs and 23 µs, and Python-loop throughputs anywhere from 28 000 to 48 000 steps per second, because other users' jobs share the CPUs and caches. The *shape* of the table was stable across runs; the absolute numbers were not. Benchmark on the machine you will use, more than once, and report the spread.

## What the table says

**Model cost dominates.** A 27-DOF scene with contacts is roughly ten times more expensive per step than the 2-DOF cart-pole, and the profile shows why: 80% of the step is collision detection, building the constraint problem and solving it. Contact is where simulation time goes.

**Threads pay only with enough work.** With one environment, eight threads are slower than one (the cart-pole drops from about 300 000 to 114 000 steps per second): the work per trajectory is too small to cover the cost of coordinating threads. From 100 environments up, eight threads deliver 5 to 7.7 times the single-thread rate, close to the eight-fold ideal, as the CPU-to-wall ratio of about 7.5 shows.

**A Python loop is not the bottleneck it is often assumed to be.** For a single environment, the Python loop and `mujoco.rollout` on one thread are within noise of each other: the per-call overhead (about a microsecond) is small next to even the cheapest step. The loop's real cost is that it is single-threaded; the fix is parallelism, not rewriting the loop.

**Rendering costs more than physics.** Software rendering at 320 by 240 produced 27 frames per second, while the same scene's physics ran at about 40 000 steps per second on one core: rendering one frame costs as much as roughly 1500 physics steps. Vision experiments are rendering-bound; render on a GPU (EGL), at the lowest resolution the policy needs, and only at the control rate.

> [!research] A cache effect worth knowing about
> In the pick-and-place rows, the Python loop over 100 separate `mjData` ran slower (28 000 steps/s) than `rollout` on one thread (49 000), which steps the same trajectories one after another through a single `mjData`. A plausible explanation is memory locality: cycling through 100 large `mjData` objects evicts each one from the CPU caches before it is used again, while one reused `mjData` stays warm. This course did not test that explanation, and the noise above means the gap should be re-measured before it is relied on.

## Scaling further

| Approach | When it fits | Cost |
|---|---|---|
| One `mjData` per thread with `mujoco.rollout` | many trajectories with open-loop controls (sampling planners, evaluation from saved states) | none beyond CPU cores; controls fixed in advance |
| `mju_threadpool` on one `mjData` (3.10+) | one large scene with many independent islands | parallelizes inside a step; helps only big scenes |
| Python multiprocessing or vectorized Gymnasium environments | closed-loop policies in RL training | process overhead, data copying between processes |
| MJX (JAX) or MuJoCo Warp on a GPU | thousands of identical environments with batched neural-network policies | different feature coverage and numerics from the C engine; benchmark your model before committing |

> [!unverified] GPU throughput
> This course has not benchmarked MJX or MuJoCo Warp on its own models, so it quotes no GPU numbers. Their documentation reports large speedups for batched simulation of suitable models; whether your model is suitable (contacts, mesh collisions, solver settings) is something to measure, not assume.

## Exercises

1. Run `examples/perf_lab.py` on your machine twice and report the spread of each row.
2. Set `<size memory="1M"/>` in `pick_place.xml` and measure memory per `mjData` and throughput for 1000 environments. Does throughput change?
3. Add a row for `mujoco.rollout` with as many threads as your machine has physical cores. Where does scaling stop?
4. Profile `cube_table.xml` and `pick_place.xml` with the timers and explain the difference in the share of time spent on collision.
