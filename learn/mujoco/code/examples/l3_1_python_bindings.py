"""Lesson 3.1: the Python bindings, the views-versus-copies trap, and batch rollouts.

INPUT   cartpole.xml and cube_table.xml
PROCESS (1) log a moving body's position the wrong way and the right way;
        (2) read the same quantities by name and by index;
        (3) list contacts with the geoms' names and the contact forces;
        (4) time a Python stepping loop against mujoco.rollout on 64 trajectories
OUTPUT  printed comparisons

Run:  python examples/l3_1_python_bindings.py
"""

import os
import time

import mujoco
import mujoco.rollout
import numpy as np

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"     # set by the test suite to keep runs short


def logging_trap() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)          # "tilted": the pole falls
    wrong, right = [], []
    for _ in range(200):
        mujoco.mj_step(model, data)
        tip = data.site("pole_tip").xpos                   # a view into mjData memory
        wrong.append(tip)                                  # appends the same view 200 times
        right.append(tip.copy())                           # appends a snapshot
    wrong, right = np.array(wrong), np.array(right)
    print(f"  logged views:  x range over 0.4 s = {np.ptp(wrong[:, 0]):.4f} m (every row is the last value)")
    print(f"  logged copies: x range over 0.4 s = {np.ptp(right[:, 0]):.4f} m")


def names_and_indices() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
    data = mujoco.MjData(model)
    data.qpos[:] = [0.2, 0.1]
    mujoco.mj_forward(model, data)
    pole = model.body("pole").id
    print(f"  model.body('pole').mass   = {model.body('pole').mass[0]:.3f} kg  (model.body_mass[{pole}] = {model.body_mass[pole]:.3f})")
    print(f"  data.joint('hinge').qpos  = {data.joint('hinge').qpos}  (data.qpos[model.jnt_qposadr[1]] = {data.qpos[model.jnt_qposadr[1]]:.3f})")
    print(f"  data.sensor('pole_angle').data = {data.sensor('pole_angle').data}")
    print(f"  data.xmat[{pole}] has shape {data.xmat[pole].shape}; reshape(3, 3) for the rotation matrix")


def contacts() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("cube_table")))
    data = mujoco.MjData(model)
    for _ in range(300):
        mujoco.mj_step(model, data)
    force = np.zeros(6)
    for i, c in enumerate(data.contact[: data.ncon]):
        mujoco.mj_contactForce(model, data, i, force)
        print(f"  contact {i}: {model.geom(c.geom1).name} / {model.geom(c.geom2).name}, "
              f"dist {1e3 * c.dist:+.3f} mm, normal force {force[0]:.3f} N")


def batch_rollouts() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
    data = mujoco.MjData(model)
    nbatch, nstep = 64, 100 if FAST else 500
    spec = mujoco.mjtState.mjSTATE_FULLPHYSICS
    state0 = np.zeros((nbatch, mujoco.mj_stateSize(model, spec)))
    rng = np.random.default_rng(0)
    for k in range(nbatch):                               # 64 random initial pole angles
        data.qpos[:] = [0.0, rng.uniform(-0.3, 0.3)]
        data.qvel[:] = 0
        data.time = 0
        mujoco.mj_getState(model, data, state0[k], spec)
    controls = np.zeros((nbatch, nstep, model.nu))

    t = time.perf_counter()
    for k in range(nbatch):                               # plain Python loop
        mujoco.mj_setState(model, data, state0[k], spec)
        for _ in range(nstep):
            mujoco.mj_step(model, data)
    loop = time.perf_counter() - t

    datas = [mujoco.MjData(model) for _ in range(4)]      # one MjData per worker thread
    t = time.perf_counter()
    states, _ = mujoco.rollout.rollout(model, datas, state0, controls)
    batched = time.perf_counter() - t
    print(f"  {nbatch} x {nstep} steps: Python loop {1e3 * loop:.1f} ms, mujoco.rollout (4 threads) {1e3 * batched:.1f} ms")
    print(f"  final states agree: {np.allclose(states[-1, -1, 1:3], data.qpos)}  (state layout: time, qpos, qvel)")


if __name__ == "__main__":
    print("logging a moving site:")
    logging_trap()
    print("named access and indices:")
    names_and_indices()
    print("contacts after the dropped cube lands:")
    contacts()
    print("stepping many trajectories:")
    batch_rollouts()
