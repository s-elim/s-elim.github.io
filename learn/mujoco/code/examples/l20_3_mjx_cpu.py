"""Lesson 20.3: MJX, MuJoCo's JAX reimplementation, on a CPU, against the C engine (Level 20).

INPUT   the course models; cart-pole (2 dof, no contacts) and cube_table (two cubes on a table, contacts)
PROCESS (1) which models mjx.put_model accepts, and why it rejects the others;
        (2) for cart-pole and cube_table: the C engine (a Python loop, and mujoco.rollout on 8 threads) against
            jax.jit(jax.vmap(mjx.step)) at batch sizes 1 to 4096 on the CPU: the first call's time (tracing and
            compilation) and steady steps per second
OUTPUT  printed tables. This machine has no GPU; nothing here says how MJX performs on one.

Run:  pip install "mujoco-mjx==3.14.0" "jax[cpu]";  python examples/l20_3_mjx_cpu.py          (about 2 minutes)
"""
# requires: mjx

import os
import time

import jax
import jax.numpy as jnp
import mujoco
import mujoco.rollout
import numpy as np
from mujoco import mjx

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"
MODELS = ("pendulum", "cartpole", "double_pendulum", "arm7", "cube_table", "ball_drop", "push", "pick_place")


def c_engine(model: mujoco.MjModel, steps: int = 2000) -> tuple[float, float]:
    """Steps per second of the C engine: one Python loop, and rollout of 512 trajectories on 8 threads."""
    data = mujoco.MjData(model)
    t0 = time.perf_counter()
    for _ in range(steps):
        mujoco.mj_step(model, data)
    loop = steps / (time.perf_counter() - t0)
    state = np.empty(mujoco.mj_stateSize(model, mujoco.mjtState.mjSTATE_FULLPHYSICS))
    mujoco.mj_getState(model, mujoco.MjData(model), state, mujoco.mjtState.mjSTATE_FULLPHYSICS)
    n, nstep = 512, 200
    datas = [mujoco.MjData(model) for _ in range(8)]
    t0 = time.perf_counter()
    mujoco.rollout.rollout(model, datas, np.tile(state, (n, 1)), np.zeros((n, nstep, model.nu)))
    return loop, n * nstep / (time.perf_counter() - t0)


def mjx_rate(model: mujoco.MjModel, batch: int, steps: int) -> tuple[float, float]:
    """(seconds for the first call, steady steps per second) of a jitted, vmapped mjx.step."""
    mx = mjx.put_model(model)
    dx = mjx.make_data(mx)
    batched = jax.vmap(lambda _: dx)(jnp.arange(batch))
    step = jax.jit(jax.vmap(mjx.step, in_axes=(None, 0)))
    t0 = time.perf_counter()
    out = jax.block_until_ready(step(mx, batched))
    first = time.perf_counter() - t0
    t0 = time.perf_counter()
    for _ in range(steps):
        out = step(mx, out)
    jax.block_until_ready(out)
    return first, batch * steps / (time.perf_counter() - t0)


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}, JAX {jax.__version__} on {jax.devices()[0].platform}; {os.cpu_count()} logical CPUs")
    print("(1) mjx.put_model on the course models")
    for name in MODELS:
        model = mujoco.MjModel.from_xml_path(str(model_path(name)))
        try:
            mjx.put_model(model)
            print(f"    {name:<16} accepted (nv {model.nv})")
        except Exception as err:                                         # MJX names the unsupported feature
            print(f"    {name:<16} rejected: {str(err).splitlines()[0]}")
    print("(2) steps per second on this CPU")
    for name in ("cartpole", "cube_table"):
        model = mujoco.MjModel.from_xml_path(str(model_path(name)))
        loop, rollout = c_engine(model)
        print(f"    {name}: C engine, Python loop {loop:,.0f}; rollout on 8 threads {rollout:,.0f}")
        for batch in ((1, 256) if FAST else (1, 64, 1024, 4096)):
            first, rate = mjx_rate(model, batch, 20 if FAST else max(20, 20000 // batch))
            print(f"    {name}: MJX batch {batch:>5}: first call {first:5.2f} s, then {rate:>11,.0f} steps/s")
