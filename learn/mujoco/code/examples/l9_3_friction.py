"""Lesson 9.3: friction: the incline test, slow creep, condim, and the two friction cones.

INPUT   incline.xml (a 0.2 kg block on a ramp that is a mocap body); small scenes below
PROCESS (1) tilt the ramp slowly and find the angle at which the block starts to slide,
            for three friction coefficients and both cones, against atan(mu);
        (2) below the slip angle: the creep velocity against the prediction from the
            friction rows' soft-constraint equation, for five parameter settings, and
            the regularizer of friction rows against the normal row's;
        (3) condim: a ball on a 10 degree slope with no friction, sliding friction only,
            and rolling friction; a ball spinning in place with and without torsional
            friction
OUTPUT  printed tables

Run:  python examples/l9_3_friction.py
"""

import math
import os

import mujoco
import numpy as np

from mjcourse import model_path

G = 9.81
FAST = os.environ.get("MJC_FAST") == "1"


def incline(mu: float, cone: str = "mjCONE_ELLIPTIC", impratio: float = 1.0, tc: float = 0.02,
            d0: float = 0.9, noslip: int = 0) -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(model_path("incline")))
    model.opt.cone = getattr(mujoco.mjtCone, cone)
    model.opt.impratio, model.opt.noslip_iterations = impratio, noslip
    for g in range(model.ngeom):                      # same parameters on every geom: no mixing
        model.geom_friction[g][0] = mu
        model.geom_solref[g] = [tc, 1.0]
        model.geom_solimp[g][0] = d0
    return model, mujoco.MjData(model)


def place(model, data, angle: float) -> np.ndarray:
    """Tilt the ramp about world y, rest the block on it; return the downhill unit vector."""
    quat = np.array([math.cos(angle / 2), 0.0, math.sin(angle / 2), 0.0])
    data.mocap_quat[0] = quat
    rot = np.zeros(9)
    mujoco.mju_quat2Mat(rot, quat)
    rot = rot.reshape(3, 3)
    data.qpos[0:3] = data.mocap_pos[0] + rot[:, 2] * (0.01 + 0.03)
    data.qpos[3:7] = quat
    data.qvel[:] = 0
    mujoco.mj_forward(model, data)
    return -rot[:, 0] if rot[2, 0] > 0 else rot[:, 0]


def slip_angle(mu: float, cone: str) -> float:
    """Raise the tilt by 0.05 degree per 0.25 s and return the angle where the block moves faster than 1 cm/s."""
    model, data = incline(mu, cone)
    start = math.degrees(math.atan(mu)) - (1.0 if FAST else 3.0)
    angle = start
    place(model, data, math.radians(angle))
    while angle < 60:
        angle += 0.05
        quat = np.array([math.cos(math.radians(angle) / 2), 0.0, math.sin(math.radians(angle) / 2), 0.0])
        data.mocap_quat[0] = quat
        for _ in range(125):
            mujoco.mj_step(model, data)
        if np.linalg.norm(data.qvel[0:3]) > 0.01:
            return angle
    return float("nan")


def creep(**kw) -> tuple[float, int, np.ndarray]:
    model, data = incline(0.4, **kw)
    down = place(model, data, math.radians(15))
    for _ in range(1000):                              # settle 2 s
        mujoco.mj_step(model, data)
    p0, t0 = data.qpos[0:3].copy(), data.time
    for _ in range(5000):                              # measure over 10 s
        mujoco.mj_step(model, data)
    return float(np.dot(data.qpos[0:3] - p0, down) / (data.time - t0)), data.ncon, np.array(data.efc_R[:4])


def condim_demos() -> None:
    # MJCF angles are in degrees unless <compiler angle="radian"/> says otherwise.
    slope = """<mujoco><option cone="elliptic"/><worldbody>
      <body euler="0 10 0"><geom type="plane" size="1 0.3 0.01" condim="{condim}" friction="1 0.005 {roll}"/></body>
      <body pos="0 0 0.0508"><freejoint/><geom size="0.05" mass="0.2" condim="{condim}" friction="1 0.005 {roll}"/></body>
    </worldbody></mujoco>"""
    a = G * math.sin(math.radians(10))
    for condim, roll, note in ((1, 0.0001, f"frictionless sliding predicts g sin 10 deg x 1 s = {a:.4f}"),
                               (3, 0.0001, f"rolling without slip predicts 5/7 g sin 10 deg x 1 s = {5 / 7 * a:.4f}"),
                               (6, 0.02, "rolling friction 0.02 m exceeds r tan 10 deg = 0.0088 m: no motion")):
        model = mujoco.MjModel.from_xml_string(slope.format(condim=condim, roll=roll))
        data = mujoco.MjData(model)
        for _ in range(100):                           # settle onto the surface
            mujoco.mj_step(model, data)
        v0 = np.linalg.norm(data.qvel[0:3])
        for _ in range(500):
            mujoco.mj_step(model, data)
        speed = np.linalg.norm(data.qvel[0:3]) - v0
        print(f"  ball on a 10 degree slope, condim {condim}: speed gained in 1 s {speed:.4f} m/s ({note})")
    spin = """<mujoco><option cone="elliptic"/><worldbody><geom type="plane" size="1 1 .1" condim="{condim}" friction="1 0.005 0.0001"/>
      <body pos="0 0 0.05"><freejoint/><geom size="0.05" mass="0.2" condim="{condim}" friction="1 0.005 0.0001"/></body>
    </worldbody></mujoco>"""
    for condim in (3, 4):
        model = mujoco.MjModel.from_xml_string(spin.format(condim=condim))
        data = mujoco.MjData(model)
        data.qvel[5] = 20.0                            # spin about the vertical at 20 rad/s, one contact point
        for _ in range(500):
            mujoco.mj_step(model, data)
        print(f"  ball spinning about the vertical at 20 rad/s, condim {condim}: spin after 1 s {data.qvel[5]:.3f} rad/s")


if __name__ == "__main__":
    print("(1) slip angle: tilt slowly until the block moves faster than 1 cm/s")
    print(f"  {'mu':>5}{'atan(mu) (deg)':>16}{'elliptic (deg)':>16}{'pyramidal (deg)':>17}")
    for mu in (0.3, 0.5, 0.8):
        print(f"  {mu:>5}{math.degrees(math.atan(mu)):>16.2f}{slip_angle(mu, 'mjCONE_ELLIPTIC'):>16.2f}"
              f"{slip_angle(mu, 'mjCONE_PYRAMIDAL'):>17.2f}")
    print("(2) creep on a 15 degree slope with mu = 0.4, below the 21.8 degree slip angle")
    print("  prediction for elliptic cones: v = (1 - d0)/d0 * g sin(15 deg) * (dw tc / 2) / (contacts * impratio)")
    a0 = G * math.sin(math.radians(15))
    for label, kw in (("elliptic, defaults", {}), ("elliptic, impratio 10", {"impratio": 10.0}),
                      ("elliptic, timeconst 0.01", {"tc": 0.01}), ("elliptic, d0 0.99", {"d0": 0.99}),
                      ("elliptic, impratio 10, noslip 3", {"impratio": 10.0, "noslip": 3}),
                      ("pyramidal, defaults", {"cone": "mjCONE_PYRAMIDAL"})):
        v, n, r = creep(**kw)
        d0, tc, imp = kw.get("d0", 0.9), kw.get("tc", 0.02), kw.get("impratio", 1.0)
        pred = (1 - d0) / d0 * a0 * (0.95 * tc / 2) / (n * imp)
        shown = f"{1000 * pred:.4f}" if "pyramidal" not in label and "noslip" not in label else "-"
        print(f"  {label:<34} creep {1000 * v:8.4f} mm/s   predicted {shown:>7}   R of first contact's rows {np.round(r[:3], 5)}")
    print("(3) condim")
    condim_demos()
