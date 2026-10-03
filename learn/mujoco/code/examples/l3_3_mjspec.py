"""Lesson 3.3: building and editing models in code with MjSpec.

INPUT   nothing for the procedural tower; cube_table.xml for the edits
PROCESS (1) build a tower of boxes from code, compile, simulate, check it stands;
        (2) load an existing model as a spec, change a geom and add a body;
        (3) add a body to a running simulation with spec.recompile, keeping state;
        (4) read simulation values for spec elements with data.bind
OUTPUT  printed checks and the first lines of the generated MJCF

Run:  python examples/l3_3_mjspec.py
"""

import mujoco
import numpy as np

from mjcourse import model_path

BOX = mujoco.mjtGeom.mjGEOM_BOX


def build_tower(n: int, half: float = 0.03) -> mujoco.MjSpec:
    spec = mujoco.MjSpec()
    spec.modelname = f"tower_{n}"
    spec.compiler.degree = False                     # angles in radians, as in every course model
    spec.option.timestep = 0.002
    world = spec.worldbody
    world.add_light(pos=[0, -1, 2], dir=[0, 0.5, -1])
    world.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[1, 1, 0.05])
    for k in range(n):
        body = world.add_body(name=f"box{k}", pos=[0, 0, half + 2 * half * k])
        body.add_freejoint()
        body.add_geom(name=f"box{k}", type=BOX, size=[half] * 3, mass=0.1,
                      rgba=[0.2 + 0.8 * k / max(n - 1, 1), 0.4, 0.8, 1])
    return spec


def tower() -> None:
    spec = build_tower(6)
    model = spec.compile()
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)                   # xpos is only valid after forward kinematics
    top0 = data.body("box5").xpos.copy()
    for _ in range(1000):
        mujoco.mj_step(model, data)
    drift = np.linalg.norm(data.body("box5").xpos - top0)
    print(f"  6-box tower: nbody={model.nbody}, top box moved {1e3 * drift:.3f} mm in 2 s")
    print("  generated MJCF, first lines:")
    for line in spec.to_xml().splitlines()[:6]:
        print("    " + line)


def edit_existing() -> None:
    spec = mujoco.MjSpec.from_file(str(model_path("cube_table")))
    spec.geom("rest_cube").friction = [0.2, 0.005, 0.0001]
    ball = spec.worldbody.add_body(name="ball", pos=[0, 0.2, 0.3])
    ball.add_freejoint()
    ball.add_geom(name="ball", type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.03], mass=0.05)
    model = spec.compile()
    print(f"  edited cube_table: nbody {model.nbody}, rest_cube friction {model.geom('rest_cube').friction}")


def recompile_keeps_state() -> None:
    spec = mujoco.MjSpec.from_file(str(model_path("cube_table")))
    model = spec.compile()
    data = mujoco.MjData(model)
    for _ in range(400):
        mujoco.mj_step(model, data)
    t, drop_z = data.time, data.body("drop_cube").xpos[2]
    extra = spec.worldbody.add_body(name="extra", pos=[0, -0.3, 0.5])
    extra.add_freejoint()
    extra.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.04], mass=0.1)
    model, data = spec.recompile(model, data)       # returns new objects in Python
    mujoco.mj_forward(model, data)
    print(f"  before: t = {t:.3f} s, drop_cube z = {drop_z:.4f} m; after recompile: t = {data.time:.3f} s, "
          f"drop_cube z = {data.body('drop_cube').xpos[2]:.4f} m, nbody {model.nbody}")

    bound = data.bind(spec.geom("drop_cube"))         # simulation values for a spec element
    print(f"  data.bind(spec.geom('drop_cube')).xpos = {np.round(bound.xpos, 4)}")


if __name__ == "__main__":
    print("procedural model:")
    tower()
    print("editing a loaded model:")
    edit_existing()
    print("recompiling a running simulation:")
    recompile_keeps_state()
