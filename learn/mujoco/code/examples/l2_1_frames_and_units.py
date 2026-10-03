"""Lesson 2.1: five ways to write one orientation, and the degrees trap.

INPUT   MJCF strings written in this file
PROCESS (1) compile five bodies meant to be rotated 90 degrees about z, each with a
            different orientation attribute, and compare the quaternions MuJoCo
            stores (zaxis cannot express a rotation about z: watch its output);
        (2) compile the same hinge with range="-90 90" under the default compiler
            setting (degrees) and under angle="radian"
OUTPUT  the compiled body quaternions and joint ranges

Run:  python examples/l2_1_frames_and_units.py
"""

import mujoco
import numpy as np

FIVE_WAYS = """
<mujoco>
  <compiler angle="degree"/>
  <worldbody>
    <body name="quat"      quat="0.7071068 0 0 0.7071068"><geom size=".01"/></body>
    <body name="axisangle" axisangle="0 0 1 90"><geom size=".01"/></body>
    <body name="euler"     euler="0 0 90"><geom size=".01"/></body>
    <body name="xyaxes"    xyaxes="0 1 0  -1 0 0"><geom size=".01"/></body>
    <body name="zaxis"     zaxis="0 0 1"><geom size=".01"/></body>
  </worldbody>
</mujoco>
"""

HINGE = """
<mujoco>
  {compiler}
  <worldbody>
    <body><joint name="j" type="hinge" range="-90 90"/><geom type="capsule" size=".02" fromto="0 0 0 .2 0 0"/></body>
  </worldbody>
</mujoco>
"""


def five_ways() -> None:
    model = mujoco.MjModel.from_xml_string(FIVE_WAYS)
    for b in range(1, model.nbody):
        print(f"  {model.body(b).name:<10s} body_quat = {np.round(model.body_quat[b], 6)}")


def degrees_trap() -> None:
    for compiler in ("", '<compiler angle="radian"/>'):
        model = mujoco.MjModel.from_xml_string(HINGE.format(compiler=compiler))
        lo, hi = model.jnt_range[0]
        label = compiler or "(no compiler element: MJCF default)"
        print(f"  {label:<38s} range = [{lo:.4f}, {hi:.4f}] rad = [{np.degrees(lo):.1f}, {np.degrees(hi):.1f}] deg")


if __name__ == "__main__":
    print("one rotation (90 deg about z), five specifications:")
    five_ways()
    print("hinge written with range=\"-90 90\":")
    degrees_trap()
