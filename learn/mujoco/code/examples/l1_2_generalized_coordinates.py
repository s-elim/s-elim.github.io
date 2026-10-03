"""Lesson 1.2: generalized coordinates, and why positions are not velocities.

INPUT   joint_zoo.xml: one free, one ball, one slide and one hinge joint
PROCESS (1) print where each joint lives in qpos and in qvel;
        (2) spin the free body, then recover its velocity from two poses
            by naive differencing and by mj_differentiatePos;
        (3) integrate a pose with mj_integratePos and check the quaternion norm
OUTPUT  the layout table and the two velocity estimates side by side

Run:  python examples/l1_2_generalized_coordinates.py
"""

import mujoco
import numpy as np

from mjcourse import model_path

NAMES = {0: "free", 1: "ball", 2: "slide", 3: "hinge"}


def layout(model: mujoco.MjModel) -> None:
    print(f"nq = {model.nq}, nv = {model.nv}")
    for j in range(model.njnt):
        qadr, vadr = model.jnt_qposadr[j], model.jnt_dofadr[j]
        qend = model.jnt_qposadr[j + 1] if j + 1 < model.njnt else model.nq
        vend = model.jnt_dofadr[j + 1] if j + 1 < model.njnt else model.nv
        print(f"  {model.joint(j).name:<6} ({NAMES[model.jnt_type[j]]:<5}) "
              f"qpos[{qadr}:{qend}] size {qend - qadr}   qvel[{vadr}:{vend}] size {vend - vadr}")


def recover_velocity(model: mujoco.MjModel) -> None:
    data = mujoco.MjData(model)
    free = model.joint("free")
    q0 = data.qpos.copy()
    # Spin the free body: 2 rad/s about its local z axis, plus 0.1 m/s along world x.
    data.qvel[free.dofadr[0]: free.dofadr[0] + 6] = [0.1, 0, 0, 0, 0, 2.0]
    true_v = data.qvel.copy()
    dt = 0.05
    for _ in range(round(dt / model.opt.timestep)):
        mujoco.mj_step(model, data)
    q1 = data.qpos.copy()

    naive = (q1 - q0) / dt                    # length nq: not a velocity at all for free and ball joints
    proper = np.zeros(model.nv)
    mujoco.mj_differentiatePos(model, proper, dt, q0, q1)
    a, b = free.qposadr[0], free.dofadr[0]
    print("free joint, true qvel           :", np.round(true_v[b:b + 6], 4))
    print("mj_differentiatePos(dt, q0, q1)  :", np.round(proper[b:b + 6], 4))
    print("naive (q1 - q0) / dt, 7 numbers  :", np.round(naive[a:a + 7], 4))


def integrate_pose(model: mujoco.MjModel) -> None:
    q = mujoco.MjData(model).qpos.copy()
    v = np.zeros(model.nv)
    free = model.joint("free")
    v[free.dofadr[0] + 3: free.dofadr[0] + 6] = [1.0, 2.0, 3.0]   # angular velocity, rad/s
    mujoco.mj_integratePos(model, q, v, 0.5)                      # advance 0.5 s
    quat = q[free.qposadr[0] + 3: free.qposadr[0] + 7]
    print("after mj_integratePos: quaternion =", np.round(quat, 4), " norm =", round(float(np.linalg.norm(quat)), 12))


if __name__ == "__main__":
    model = mujoco.MjModel.from_xml_path(str(model_path("joint_zoo")))
    layout(model)
    recover_velocity(model)
    integrate_pose(model)
