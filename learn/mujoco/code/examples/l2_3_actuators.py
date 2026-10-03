"""Lesson 2.3: actuator force laws, clamping, activation dynamics, coupling.

INPUT   an actuator test bench written in this file (one hinge per actuator), and
        gantry_gripper.xml for tendon and equality coupling
PROCESS (1) put every joint at a known angle and velocity, set controls, run
            mj_forward, and compare actuator_force with the documented law
            p = a*u + b0 + b1*l + b2*ldot (with gear, l = gear*q);
        (2) push controls past ctrlrange and forces past forcerange;
        (3) watch a filter actuator's activation approach its control;
        (4) close the gripper and check both fingers move together
OUTPUT  tables of measured force next to the formula

Run:  python examples/l2_3_actuators.py
"""

import math

import mujoco
import numpy as np

from mjcourse import model_path

BENCH = """
<mujoco>
  <compiler angle="radian"/>
  <option gravity="0 0 0"/>
  <worldbody>
    <body name="b0"><joint name="j_motor"/><geom type="capsule" fromto="0 0 0 .1 0 0" size=".01"/></body>
    <body name="b1" pos="0 .2 0"><joint name="j_position"/><geom type="capsule" fromto="0 0 0 .1 0 0" size=".01"/></body>
    <body name="b2" pos="0 .4 0"><joint name="j_velocity"/><geom type="capsule" fromto="0 0 0 .1 0 0" size=".01"/></body>
    <body name="b3" pos="0 .6 0"><joint name="j_filter"/><geom type="capsule" fromto="0 0 0 .1 0 0" size=".01"/></body>
  </worldbody>
  <actuator>
    <motor    name="motor"    joint="j_motor"    gear="2" ctrlrange="-1 1"/>
    <position name="position" joint="j_position" kp="10" kv="1" forcerange="-3 3"/>
    <velocity name="velocity" joint="j_velocity" kv="3"/>
    <general  name="filter"   joint="j_filter"   dyntype="filter" dynprm="0.1" gainprm="5"/>
  </actuator>
</mujoco>
"""


def force_laws() -> None:
    model = mujoco.MjModel.from_xml_string(BENCH)
    data = mujoco.MjData(model)
    q, qd = 0.3, -0.5
    data.qpos[:] = q
    data.qvel[:] = qd
    data.ctrl[:] = [0.4, 0.5, 1.0, 0.8]
    mujoco.mj_forward(model, data)
    expected = {
        "motor":    0.4,                              # gain 1: force = ctrl; the joint torque is gear * force
        "position": 10 * (0.5 - q) - 1 * qd,          # kp (ctrl - q) - kv qdot
        "velocity": 3 * (1.0 - qd),                   # kv (ctrl - qdot)
        "filter":   5 * data.act[0],                  # gain * activation (activation starts at 0)
    }
    print(f"  {'actuator':<9}{'gainprm[0]':>11}{'biasprm[0:3]':>22}{'actuator_force':>16}{'formula':>10}{'qfrc_actuator':>15}")
    for i in range(model.nu):
        name = model.actuator(i).name
        print(f"  {name:<9}{model.actuator_gainprm[i, 0]:>11.3g}{np.array2string(model.actuator_biasprm[i, :3], precision=3):>22}"
              f"{data.actuator_force[i]:>16.4f}{expected[name]:>10.4f}{data.qfrc_actuator[i]:>15.4f}")
    print("  (the motor's actuator_force is in actuator space, 0.4; the joint torque is gear * 0.4 = 0.8)")


def clamping() -> None:
    model = mujoco.MjModel.from_xml_string(BENCH)
    data = mujoco.MjData(model)
    data.ctrl[0] = 5.0                                # beyond ctrlrange [-1, 1]
    data.ctrl[1] = 2.0                                # target 2 rad from q = 0: kp * 2 = 20 > forcerange 3
    mujoco.mj_forward(model, data)
    print(f"  motor ctrl 5.0 with ctrlrange [-1, 1] -> actuator_force {data.actuator_force[0]:.3f} "
          f"(data.ctrl still reads {data.ctrl[0]})")
    print(f"  position target 2 rad, kp 10, forcerange [-3, 3] -> actuator_force {data.actuator_force[1]:.3f}")


def activation() -> None:
    model = mujoco.MjModel.from_xml_string(BENCH)
    data = mujoco.MjData(model)
    data.ctrl[3] = 1.0
    tau = model.actuator_dynprm[3, 0]
    for t_mark in (0.05, 0.1, 0.2, 0.5):
        while data.time < t_mark - 1e-9:
            mujoco.mj_step(model, data)
        print(f"  t = {data.time:.2f} s: act = {data.act[0]:.4f}, 1 - exp(-t/tau) = {1 - math.exp(-data.time / tau):.4f}")


def coupling() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("gantry_gripper")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    data.ctrl[model.actuator("gripper/grip").id] = 0.03
    for _ in range(1000):
        mujoco.mj_step(model, data)
    left, right = data.joint("gripper/finger_left").qpos[0], data.joint("gripper/finger_right").qpos[0]
    print(f"  grip command 0.03 m: finger_left {left:.5f} m, finger_right {right:.5f} m, "
          f"tendon length {data.ten_length[0]:.5f} m")


if __name__ == "__main__":
    print("force laws at q = 0.3 rad, qdot = -0.5 rad/s:")
    force_laws()
    print("clamping:")
    clamping()
    print("filter activation, time constant 0.1 s, control stepped to 1 at t = 0:")
    activation()
    print("gripper coupling (tendon + joint equality):")
    coupling()
