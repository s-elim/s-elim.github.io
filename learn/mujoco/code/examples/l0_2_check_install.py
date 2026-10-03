"""Lesson 0.2: check that this machine can run every part of the course.

INPUT   nothing (reads the installed packages and the MUJOCO_GL environment variable)
PROCESS import mujoco, compile and step a model, try an offscreen render
OUTPUT  a short report; exit status 1 only if MuJoCo itself is missing or wrong

Run:  python examples/l0_2_check_install.py
"""

import os
import platform
import sys

EXPECTED = "3.14.0"


def main() -> int:
    print(f"python   {sys.version.split()[0]} on {platform.system()} {platform.machine()}")
    try:
        import mujoco
    except ImportError:
        print("mujoco   NOT INSTALLED: pip install mujoco==3.14.0")
        return 1
    import numpy as np

    print(f"mujoco   {mujoco.__version__} (engine reports {mujoco.mj_versionString()})")
    print(f"numpy    {np.__version__}")
    if mujoco.__version__ != EXPECTED:
        print(f"WARNING  the course was verified with {EXPECTED}; numbers may differ")

    xml = """<mujoco><worldbody><geom type="plane" size="1 1 .1"/>
             <body pos="0 0 .5"><freejoint/><geom size=".05"/></body></worldbody></mujoco>"""
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    for _ in range(500):
        mujoco.mj_step(model, data)
    print(f"physics  ok: t = {data.time:.3f} s, ball at z = {data.qpos[2]:.4f} m, {data.ncon} contact(s)")

    backend = os.environ.get("MUJOCO_GL", "(unset: platform default)")
    try:
        renderer = mujoco.Renderer(model, height=48, width=64)
        renderer.update_scene(data)
        image = renderer.render()
        renderer.close()
        print(f"render   ok with MUJOCO_GL={backend}: image {image.shape} {image.dtype}")
    except Exception as err:  # noqa: BLE001 - any GL failure is reported, not fatal
        print(f"render   unavailable with MUJOCO_GL={backend}: {type(err).__name__}: {err}")
        print("         physics, kinematics, control and learning lessons still work;")
        print("         see 'Headless rendering' in Lesson 0.2 for camera lessons")

    try:
        import gymnasium

        print(f"gym      gymnasium {gymnasium.__version__}")
    except ImportError:
        print("gym      gymnasium not installed (needed from Level 12): pip install gymnasium")
    try:
        import torch

        print(f"torch    {torch.__version__} (CUDA available: {torch.cuda.is_available()})")
    except ImportError:
        print("torch    not installed (needed for PPO and vision policies): pip install -e .[learn]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
