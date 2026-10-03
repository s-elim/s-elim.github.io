"""Lesson 0.3: measure how far a block creeps on a slope that should hold it.

INPUT   incline.xml (block on a mocap ramp, sliding friction 0.4 on both geoms)
PROCESS tilt the ramp to 15 degrees (below the Coulomb slip angle atan(0.4) = 21.8
        degrees), place the block on it, simulate 10 s under four solver settings
OUTPUT  the distance the block slid along the slope for each setting

Ideal Coulomb friction predicts zero motion. Any non-zero distance is a property
of MuJoCo's regularized (soft) friction model, not of the physics being modelled.

Run:  python examples/l0_3_slow_slip.py
"""

import math

import mujoco
import numpy as np

from mjcourse import model_path

ANGLE = math.radians(15.0)
SETTINGS = {
    "pyramidal cone (default)": dict(cone=mujoco.mjtCone.mjCONE_PYRAMIDAL, impratio=1.0, noslip=0),
    "elliptic cone, impratio 1": dict(cone=mujoco.mjtCone.mjCONE_ELLIPTIC, impratio=1.0, noslip=0),
    "elliptic cone, impratio 10": dict(cone=mujoco.mjtCone.mjCONE_ELLIPTIC, impratio=10.0, noslip=0),
    "elliptic, impratio 10, noslip 3": dict(cone=mujoco.mjtCone.mjCONE_ELLIPTIC, impratio=10.0, noslip=3),
}


def tilt(model: mujoco.MjModel, data: mujoco.MjData, angle: float) -> np.ndarray:
    """Tilt the ramp about world y and put the block at rest on its surface.

    Returns the unit vector pointing down the slope.
    """
    quat = np.array([math.cos(angle / 2), 0.0, math.sin(angle / 2), 0.0])  # rotation about +y
    data.mocap_quat[0] = quat
    rot = np.zeros(9)
    mujoco.mju_quat2Mat(rot, quat)
    rot = rot.reshape(3, 3)
    normal, along = rot[:, 2], rot[:, 0]
    # ramp half-thickness 0.01 m, block half-size 0.03 m (see incline.xml)
    centre = data.mocap_pos[0] + normal * (0.01 + 0.03)
    data.qpos[0:3] = centre
    data.qpos[3:7] = quat
    data.qvel[:] = 0
    mujoco.mj_forward(model, data)
    return -along if along[2] > 0 else along


def slide_distance(cone: int, impratio: float, noslip: int, seconds: float = 10.0) -> float:
    model = mujoco.MjModel.from_xml_path(str(model_path("incline")))
    model.opt.cone, model.opt.impratio, model.opt.noslip_iterations = cone, impratio, noslip
    data = mujoco.MjData(model)
    downhill = tilt(model, data, ANGLE)
    start = data.qpos[0:3].copy()
    for _ in range(round(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)
    return float(np.dot(data.qpos[0:3] - start, downhill))


if __name__ == "__main__":
    print(f"slope 15.0 deg, friction 0.4, Coulomb slip angle {math.degrees(math.atan(0.4)):.1f} deg")
    for name, kw in SETTINGS.items():
        d = slide_distance(**kw)
        print(f"{name:<34s} slid {1e3 * d:9.4f} mm in 10 s")
