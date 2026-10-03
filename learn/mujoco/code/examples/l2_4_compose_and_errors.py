"""Lesson 2.4: composing models, reading compiler errors, seeing the compiled model.

INPUT   gantry_gripper.xml (composed with <attach>) and a list of broken MJCF snippets
PROCESS (1) list the names the attachment produced and where they came from;
        (2) compile each broken snippet and print MuJoCo's own error message;
        (3) change a parameter of the compiled model and save it back to MJCF
OUTPUT  the names, the error catalogue, and the saved element

Run:  python examples/l2_4_compose_and_errors.py
"""

import tempfile
from pathlib import Path

import mujoco

from mjcourse import model_path

BROKEN = {
    "unknown element": "<mujoco><worldbody><bod/></worldbody></mujoco>",
    "unknown attribute": '<mujoco><worldbody><geom size=".1" colour="1 0 0 1"/></worldbody></mujoco>',
    "too few numbers": '<mujoco><worldbody><body pos="0 0"><geom size=".1"/></body></worldbody></mujoco>',
    "duplicate name": '<mujoco><worldbody><geom name="a" size=".1"/><geom name="a" size=".1"/></worldbody></mujoco>',
    "undefined joint": '<mujoco><worldbody><geom size=".1"/></worldbody><actuator><motor joint="nope"/></actuator></mujoco>',
    "undefined class": '<mujoco><worldbody><geom class="nope" size=".1"/></worldbody></mujoco>',
    "wrong keyframe length": '<mujoco><worldbody><body><joint/><geom size=".1"/></body></worldbody>'
                             '<keyframe><key qpos="0 0"/></keyframe></mujoco>',
    "missing mesh file": '<mujoco><asset><mesh file="nope.stl"/></asset><worldbody/></mujoco>',
}


def attachment() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("gantry_gripper")))
    joints = [model.joint(j).name for j in range(model.njnt)]
    acts = [model.actuator(a).name for a in range(model.nu)]
    print("  joints:   ", joints)
    print("  actuators:", acts)
    print("  tendons:  ", [model.tendon(t).name for t in range(model.ntendon)],
          " equalities:", [model.eq(e).name for e in range(model.neq)])


def errors() -> None:
    for label, xml in BROKEN.items():
        try:
            mujoco.MjModel.from_xml_string(xml)
            print(f"  {label:<22s} compiled (unexpected)")
        except ValueError as err:
            first = str(err).strip().splitlines()
            print(f"  {label:<22s} {first[0]}")
            for line in first[1:3]:
                print(f"  {'':<22s} {line}")


def save_runtime_change() -> None:
    """mj_saveLastXML copies real-valued mjModel parameters back into the XML it writes."""
    model = mujoco.MjModel.from_xml_path(str(model_path("pendulum")))
    model.dof_damping[0] = 0.25              # a change made to the compiled model at run time
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "saved.xml"
        mujoco.mj_saveLastXML(str(out), model)
        saved = out.read_text()
    joint_line = next(ln.strip() for ln in saved.splitlines() if "<joint" in ln)
    print(f"  saved joint element: {joint_line}")
    print(f"  comments kept: {'<!--' in saved}; lines in source {len(model_path('pendulum').read_text().splitlines())},"
          f" in saved file {len(saved.splitlines())}")


if __name__ == "__main__":
    print("names created by <attach prefix=\"gripper/\">:")
    attachment()
    print("compiler errors, verbatim:")
    errors()
    print("saving a model changed at run time:")
    save_runtime_change()
