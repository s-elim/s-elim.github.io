"""Lesson 9.1: collision detection: which pairs are checked, margin and gap, contacts per pair.

INPUT   small scenes written below
PROCESS (1) overlap geoms in every filtering situation and list which pairs make contacts:
            same body, parent-child, child of the world, contype/conaffinity bits,
            <exclude>, and an explicit <pair>;
        (2) a sphere approaching a plane with margin 10 mm and gap 5 mm: the three
            regimes, and the height at which the sphere comes to rest;
        (3) how many contacts each geom pair produces at rest;
        (4) the cost of collision detection as the number of free bodies grows;
        (5) a non-convex mesh: a ball dropped into a U-shaped bowl rests on its convex hull
OUTPUT  printed tables

Run:  python examples/l9_1_collision.py
"""

import os
import time

import mujoco
import numpy as np

FILTERS = """
<mujoco>
  <worldbody>
    <geom name="ground" type="plane" size="1 1 0.1"/>
    <body name="a" pos="0 0 0.5">
      <freejoint/>
      <geom name="a1" size="0.1"/>
      <geom name="a2" size="0.1" pos="0.05 0 0"/>
      <body name="a_child" pos="0.1 0 0">
        <joint type="hinge" axis="0 0 1"/>
        <geom name="child" size="0.1"/>
      </body>
    </body>
    <body name="b" pos="0 0.12 0.5">
      <freejoint/>
      <geom name="b_bits" size="0.1" contype="2" conaffinity="2"/>
    </body>
    <body name="c" pos="0.12 0.12 0.5">
      <freejoint/>
      <geom name="c_bits" size="0.1" contype="1" conaffinity="2"/>
    </body>
    <body name="d" pos="-0.12 0 0.5">
      <freejoint/>
      <geom name="d_excluded" size="0.1"/>
    </body>
    <body name="e" pos="-0.12 0.12 0.5">
      <freejoint/>
      <geom name="e_ghost" size="0.1" contype="0" conaffinity="0"/>
    </body>
    <body name="w_child" pos="0 0 0.05">
      <joint type="slide" axis="0 0 1"/>
      <geom name="world_child" size="0.1"/>
    </body>
  </worldbody>
  <contact>
    <exclude body1="a" body2="d"/>
    <pair geom1="e_ghost" geom2="a1"/>
  </contact>
</mujoco>
"""

MARGIN = """
<mujoco><option gravity="0 0 0"/><worldbody>
  <geom name="plane" type="plane" size="1 1 0.1" margin="0.01" gap="0.005"/>
  <body name="ball" pos="0 0 0.2"><freejoint/><geom name="ball" size="0.05" mass="1"/></body>
</worldbody></mujoco>
"""

SHAPES = """
<mujoco><worldbody>
  <geom type="plane" size="2 2 0.1"/>
  {body}
</worldbody></mujoco>
"""


def filters() -> None:
    model = mujoco.MjModel.from_xml_string(FILTERS)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    found = sorted({" / ".join(sorted((model.geom(c.geom1).name, model.geom(c.geom2).name)))
                    for c in data.contact[:data.ncon]})
    print(f"  contacts between overlapping geoms ({len(found)} pairs):")
    for pair in found:
        print(f"    {pair}")
    expected_missing = {
        "a1 / a2": "same body: never checked",
        "a1 / child": "parent and child: filtered (filterparent on by default)",
        "a1 / b_bits": "contype 1 & conaffinity 2 = 0 and contype 2 & conaffinity 1 = 0: incompatible bits",
        "a1 / d_excluded": "bodies a and d excluded with <exclude>",
    }
    for pair, why in expected_missing.items():
        print(f"    absent: {pair:<20} {why}")
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_FILTERPARENT
    mujoco.mj_forward(model, data)
    has = any({model.geom(c.geom1).name, model.geom(c.geom2).name} == {"a1", "child"} for c in data.contact[:data.ncon])
    print(f"  with the filterparent flag disabled, a1 / child collides: {has}")


def margin_and_gap() -> None:
    model = mujoco.MjModel.from_xml_string(MARGIN)
    data = mujoco.MjData(model)
    print(f"  {'distance (mm)':>14}{'contacts':>10}{'active rows':>13}{'normal force (N)':>18}")
    for dist in (0.020, 0.014, 0.012, 0.008, 0.002):
        mujoco.mj_resetData(model, data)
        data.qpos[2] = 0.05 + dist
        data.qvel[2] = -0.5                                  # approaching at 0.5 m/s
        mujoco.mj_forward(model, data)
        f = np.zeros(6)
        force = 0.0
        if data.ncon:
            mujoco.mj_contactForce(model, data, 0, f)
            force = f[0]
        active = sum(1 for c in data.contact[:data.ncon] if c.efc_address >= 0)
        print(f"  {1000 * dist:>14.1f}{data.ncon:>10}{active:>13}{force:>18.3f}")
    for margin in (0.0, 0.01):
        xml = MARGIN.replace('<option gravity="0 0 0"/>', "").replace('margin="0.01" gap="0.005"', f'margin="{margin}"')
        m2 = mujoco.MjModel.from_xml_string(xml)
        d2 = mujoco.MjData(m2)
        for _ in range(2000):
            mujoco.mj_step(m2, d2)
        print(f"  under gravity with margin {1000 * margin:.0f} mm, the ball comes to rest with its surface "
              f"{1000 * (d2.qpos[2] - 0.05):+.3f} mm from the plane")


def contacts_per_pair() -> None:
    bodies = {
        "sphere on plane": '<body pos="0 0 0.2"><freejoint/><geom type="sphere" size="0.05"/></body>',
        "capsule lying on plane": '<body pos="0 0 0.2" euler="0 1.5708 0"><freejoint/><geom type="capsule" size="0.03 0.1"/></body>',
        "cylinder upright on plane": '<body pos="0 0 0.2"><freejoint/><geom type="cylinder" size="0.05 0.05"/></body>',
        "box on plane": '<body pos="0 0 0.2"><freejoint/><geom type="box" size="0.05 0.05 0.05"/></body>',
        "box on box": '<geom type="box" size="0.2 0.2 0.05" pos="0 0 0.05"/><body pos="0 0 0.25"><freejoint/><geom type="box" size="0.05 0.05 0.05"/></body>',
    }
    for name, body in bodies.items():
        model = mujoco.MjModel.from_xml_string(SHAPES.format(body=body))
        data = mujoco.MjData(model)
        for _ in range(1500):
            mujoco.mj_step(model, data)
        print(f"  {name:<27} {data.ncon} contact(s) at rest")


def collision_cost() -> None:
    reps = 200 if os.environ.get("MJC_FAST") == "1" else 2000
    for n in (10, 100, 400):
        side = int(np.ceil(np.sqrt(n)))
        balls = "".join(f'<body pos="{0.12 * (i % side)} {0.12 * (i // side)} 0.05"><freejoint/><geom size="0.05"/></body>'
                        for i in range(n))
        model = mujoco.MjModel.from_xml_string(SHAPES.format(body=balls))
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        t0 = time.perf_counter()
        for _ in range(reps):
            mujoco.mj_collision(model, data)
        us = 1e6 * (time.perf_counter() - t0) / reps
        print(f"  {n:>4} balls on a plane: {n * (n + 1) // 2:>6} geom pairs in principle, {data.ncon:>4} contacts, "
              f"mj_collision {us:8.1f} us (this machine)")


def convex_hull() -> None:
    # A U-shaped bowl, 20 cm wide inside, as one mesh: two walls joined by a floor.
    spec = mujoco.MjSpec()
    spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[1, 1, 0.1])
    verts = []
    for x0, x1 in ((-0.15, -0.10), (0.10, 0.15), (-0.15, 0.15)):
        z1 = 0.15 if (x0, x1) != (-0.15, 0.15) else 0.02
        for x in (x0, x1):
            for y in (-0.1, 0.1):
                for z in (0.0, z1):
                    verts += [x, y, z]
    spec.add_mesh(name="u", uservert=verts)
    spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_MESH, meshname="u", rgba=[0.6, 0.6, 0.7, 1])
    ball = spec.worldbody.add_body(pos=[0, 0, 0.4])
    ball.add_freejoint()
    ball.add_geom(size=[0.03, 0, 0])
    model = spec.compile()
    data = mujoco.MjData(model)
    for _ in range(1500):
        mujoco.mj_step(model, data)
    print(f"  a ball dropped into the U (walls 15 cm high, floor 2 cm thick) rests with its centre at z = {data.qpos[2]:.3f} m: "
          f"on the convex hull's top (0.15 m + radius 0.03 m = 0.18 m), not on the 2 cm floor")


if __name__ == "__main__":
    print("(1) which overlapping geoms make contacts")
    filters()
    print("(2) margin 10 mm and gap 5 mm on the plane, ball (radius 50 mm) approaching at 0.5 m/s")
    margin_and_gap()
    print("(3) contacts per pair at rest")
    contacts_per_pair()
    print("(4) cost of collision detection")
    collision_cost()
    print("(5) non-convex meshes collide as their convex hull")
    convex_hull()
