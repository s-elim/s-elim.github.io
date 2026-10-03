"""Lesson 2.2: where mass and inertia come from, and how defaults resolve.

INPUT   MJCF strings in this file
PROCESS (1) compile one body per primitive shape at the default density and compare
            MuJoCo's mass and principal inertia with the textbook formulas;
        (2) show that an explicit <inertial> replaces what the geoms would give;
        (3) resolve a nested default-class hierarchy and print what each geom got
OUTPUT  tables of compiled values next to hand-computed ones

Run:  python examples/l2_2_mass_inertia_defaults.py
"""

import math

import mujoco
import numpy as np

RHO = 1000.0  # MuJoCo's default geom density, kg/m^3 (the density of water)

SHAPES = """
<mujoco>
  <worldbody>
    <body name="box"><freejoint/><geom type="box" size="0.1 0.05 0.02"/></body>
    <body name="sphere" pos="1 0 0"><freejoint/><geom type="sphere" size="0.05"/></body>
    <body name="capsule" pos="2 0 0"><freejoint/><geom type="capsule" size="0.03 0.1"/></body>
    <body name="explicit" pos="3 0 0"><freejoint/>
      <inertial pos="0 0 0" mass="2" diaginertia="0.01 0.02 0.03"/>
      <geom type="box" size="0.1 0.05 0.02"/>
    </body>
  </worldbody>
</mujoco>
"""

DEFAULTS = """
<mujoco>
  <default>
    <geom friction="0.8 0.005 0.0001" rgba="0.5 0.5 0.5 1"/>
    <default class="metal">
      <geom friction="0.3 0.005 0.0001"/>
      <default class="painted_metal">
        <geom rgba="0.8 0.1 0.1 1"/>
      </default>
    </default>
  </default>
  <worldbody>
    <body name="a" childclass="metal">
      <geom name="inherits_metal" size="0.05"/>
      <geom name="explicit_class" class="painted_metal" size="0.05" pos="0.2 0 0"/>
      <geom name="attribute_wins" class="painted_metal" friction="1.5 0.005 0.0001" size="0.05" pos="0.4 0 0"/>
    </body>
    <body name="b" pos="0 1 0">
      <geom name="top_level_default" size="0.05"/>
    </body>
  </worldbody>
</mujoco>
"""


def textbook(name: str) -> tuple[float, np.ndarray]:
    if name == "box":
        a, b, c = 0.1, 0.05, 0.02                    # half-sizes
        m = RHO * 8 * a * b * c
        return m, m / 3 * np.array([b * b + c * c, a * a + c * c, a * a + b * b])
    if name == "sphere":
        r = 0.05
        m = RHO * 4 / 3 * math.pi * r**3
        return m, np.full(3, 0.4 * m * r * r)
    if name == "capsule":                           # solid cylinder plus two hemispheres
        r, h = 0.03, 0.2                            # radius, cylinder length (2 x half-length)
        m_cyl, m_sph = RHO * math.pi * r * r * h, RHO * 4 / 3 * math.pi * r**3
        i_cyl_xy, i_cyl_z = m_cyl * (3 * r * r + h * h) / 12, m_cyl * r * r / 2
        # hemisphere centroids sit 3r/8 beyond each end of the cylinder
        i_sph_xy = 0.4 * m_sph * r * r + m_sph * h * (3 * r + 2 * h) / 8
        i_sph_z = 0.4 * m_sph * r * r
        return m_cyl + m_sph, np.array([i_cyl_xy + i_sph_xy, i_cyl_xy + i_sph_xy, i_cyl_z + i_sph_z])
    raise ValueError(name)


def shapes() -> None:
    model = mujoco.MjModel.from_xml_string(SHAPES)
    print(f"  {'body':<9}{'mass (kg)':>12}{'textbook':>12}   principal inertia (kg m^2), MuJoCo / textbook")
    for name in ("box", "sphere", "capsule"):
        b = model.body(name)
        m_ref, i_ref = textbook(name)
        print(f"  {name:<9}{b.mass[0]:>12.6f}{m_ref:>12.6f}   {np.array2string(b.inertia, precision=8)} / "
              f"{np.array2string(i_ref, precision=8)}")
    e = model.body("explicit")
    print(f"  explicit <inertial>: mass {e.mass[0]} kg, inertia {e.inertia} (the box geom is ignored for mass)")


def defaults() -> None:
    model = mujoco.MjModel.from_xml_string(DEFAULTS)
    for g in range(model.ngeom):
        geom = model.geom(g)
        print(f"  {geom.name:<18} friction={geom.friction[0]:<4} rgba={np.round(geom.rgba, 2)}")


if __name__ == "__main__":
    print("mass and inertia from geoms, density 1000 kg/m^3:")
    shapes()
    print("default classes:")
    defaults()
