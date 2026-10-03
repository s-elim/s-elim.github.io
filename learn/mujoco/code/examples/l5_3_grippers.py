"""Lesson 5.3: what decides whether a parallel-jaw grasp holds.

INPUT   gantry_gripper.xml (gripper.xml on a three-axis gantry, one cube)
PROCESS (1) the coupling: command openings, then push one finger and watch the
            equality constraint share the push;
        (2) the squeeze: actuator force and pad normal forces for three servo
            stiffnesses, against kp * opening and the forcerange cap;
        (3) the friction budget: lift cubes at fractions of m* = 2 mu N / g and
            measure whether they stay held and how fast they creep; then hold one
            cube under five friction-cone and solver settings;
        (4) which friction coefficient a pad contact uses, with and without priority;
        (5) twisting a held cube with condim 3 and condim 4 pads
OUTPUT  printed tables

Run:  python examples/l5_3_grippers.py
"""

import mujoco
import numpy as np

from mjcourse import model_path

G = 9.81
GRIP = 3                                   # actuator index of gripper/grip; ctrl = half-opening (m)


def build(condim: int | None = None, pad_priority: int | None = None, cube_friction: float | None = None):
    spec = mujoco.MjSpec.from_file(str(model_path("gantry_gripper")))
    for name in ("gripper/pad_left", "gripper/pad_right"):
        if condim is not None:
            spec.geom(name).condim = condim
        if pad_priority is not None:
            spec.geom(name).priority = pad_priority
    if cube_friction is not None:
        spec.geom("cube").friction = [cube_friction, 0.005, 0.0001]
    model = spec.compile()
    return model, mujoco.MjData(model)


def run(model, data, seconds: float) -> None:
    for _ in range(round(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)


def set_servo(model, kp: float, force_limit: float = 30.0) -> None:
    model.actuator_gainprm[GRIP, 0] = kp
    model.actuator_biasprm[GRIP, 1] = -kp
    model.actuator_forcerange[GRIP] = [-force_limit, force_limit]


def pad_forces(model, data) -> tuple[float, float, list[float], int]:
    """Normal force on each pad from the cube, the friction coefficients used, and the contact count."""
    pads = [model.geom("gripper/pad_left").id, model.geom("gripper/pad_right").id]
    cube = model.geom("cube").id
    normal, mus, n = [0.0, 0.0], set(), 0
    f = np.zeros(6)
    for i in range(data.ncon):
        c = data.contact[i]
        for k, pad in enumerate(pads):
            if {c.geom1, c.geom2} == {pad, cube}:
                mujoco.mj_contactForce(model, data, i, f)
                normal[k] += f[0]
                mus.add(round(float(c.friction[0]), 3))
                n += 1
    return normal[0], normal[1], sorted(mus), n


def close_on_cube(model, data, mass: float = 0.1) -> None:
    """The research-mode routine: settle, descend 0.33 m over 1 s, close."""
    mujoco.mj_resetDataKeyframe(model, data, 0)
    model.body_mass[model.body("cube").id] = mass
    mujoco.mj_setConst(model, data)
    run(model, data, 0.3)
    for k in range(100):
        data.ctrl[2] = -0.33 * (k + 1) / 100
        run(model, data, 0.01)
    run(model, data, 0.3)
    data.ctrl[GRIP] = 0.0
    run(model, data, 0.6)


def coupling() -> None:
    model, data = build()
    mujoco.mj_resetDataKeyframe(model, data, 0)
    data.qpos[5:8] = [0.3, 0.3, 0.02]                    # move the cube out of the way
    for target in (0.03, 0.02, 0.01):
        data.ctrl[GRIP] = target
        run(model, data, 0.5)
        print(f"  command {target:.3f} m: left {data.qpos[3]:.5f}, right {data.qpos[4]:.5f}, "
              f"tendon {data.ten_length[0]:.5f} m, actuator force {data.actuator_force[GRIP]:+.3f} N")
    finger = model.body("gripper/finger_left").id
    axis = data.xmat[finger].reshape(3, 3)[:, 1]          # the left finger slides along its body y axis
    data.xfrc_applied[finger, :3] = 5.0 * axis           # push the left finger open with 5 N
    run(model, data, 0.5)
    print(f"  5 N on the left finger only: left {data.qpos[3]:.5f}, right {data.qpos[4]:.5f}, "
          f"difference {1e6 * (data.qpos[3] - data.qpos[4]):.1f} um, tendon {data.ten_length[0]:.5f} m")


def squeeze() -> None:
    print(f"  {'kp (N/m)':>9}{'forcerange':>12}{'opening (m)':>13}{'kp * opening':>14}{'actuator force':>16}"
          f"{'N left':>8}{'N right':>9}{'contacts':>10}")
    for kp, cap in ((800, 30), (3000, 30), (3000, 10)):
        model, data = build()
        set_servo(model, kp, cap)
        close_on_cube(model, data)
        nl, nr, _, n = pad_forces(model, data)
        opening = data.ten_length[0]
        print(f"  {kp:>9}{cap:>10} N{opening:>13.5f}{kp * opening:>12.2f} N{data.actuator_force[GRIP]:>14.2f} N"
              f"{nl:>8.2f}{nr:>9.2f}{n:>10}")


def hold(mass: float, kp: float = 800, cap: float = 30, cone: str = "mjCONE_ELLIPTIC",
         impratio: float = 10, noslip: int = 0) -> tuple[float, bool, float]:
    """Close on a cube, lift it 0.1 m smoothly over 2 s, hold 4 s.

    Returns (normal force per pad at the grasp, whether the cube is still held,
    creep: how fast the cube slides down relative to the fingertips during the hold, mm/s).
    """
    model, data = build()
    set_servo(model, kp, cap)
    model.opt.cone = getattr(mujoco.mjtCone, cone)
    model.opt.impratio = impratio
    model.opt.noslip_iterations = noslip
    close_on_cube(model, data, mass)
    normal = 0.5 * sum(pad_forces(model, data)[:2])
    for k in range(200):                                  # minimum-jerk lift: no acceleration spike
        s = (k + 1) / 200
        data.ctrl[2] = -0.33 + 0.1 * (10 * s**3 - 15 * s**4 + 6 * s**5)
        run(model, data, 0.01)
    run(model, data, 0.5)
    cube, tcp = model.body("cube").id, model.site("gripper/tcp").id
    gap0, t0 = data.site_xpos[tcp][2] - data.xpos[cube][2], data.time
    run(model, data, 4.0)
    gap1 = data.site_xpos[tcp][2] - data.xpos[cube][2]
    held = bool(data.xpos[cube][2] > 0.05)
    return normal, held, 1000 * (gap1 - gap0) / (data.time - t0) if held else float("nan")


def friction_budget() -> None:
    mu = 1.5
    for kp, cap in ((800, 30), (3000, 30)):
        normal = hold(0.1, kp, cap)[0]
        m_star = 2 * mu * normal / G
        print(f"  kp {kp} N/m, forcerange {cap} N: N = {normal:.2f} N per pad -> m* = 2 mu N / g = {m_star:.2f} kg")
        for frac in (0.25, 0.5, 0.75, 0.95, 1.05):
            _, held, creep = hold(frac * m_star, kp, cap)
            state = f"held, creeping {creep:.3f} mm/s" if held else "dropped"
            print(f"    {frac:4.2f} m* = {frac * m_star:5.2f} kg: {state}")
    m_star = 2 * mu * hold(0.1)[0] / G
    print(f"  one cube at 0.5 m* = {0.5 * m_star:.2f} kg (kp 800), five contact settings:")
    for cone, imp, noslip in (("mjCONE_ELLIPTIC", 10, 0), ("mjCONE_ELLIPTIC", 10, 10), ("mjCONE_PYRAMIDAL", 10, 0),
                              ("mjCONE_ELLIPTIC", 1, 0), ("mjCONE_PYRAMIDAL", 1, 0)):
        _, held, creep = hold(0.5 * m_star, cone=cone, impratio=imp, noslip=noslip)
        state = f"held, creeping {creep:.3f} mm/s" if held else "dropped"
        label = f"{cone[7:].lower()}, impratio {imp}" + (f", noslip {noslip}" if noslip else "")
        print(f"    {label:<34} {state}")


def friction_mixing() -> None:
    for prio in (1, 0):
        for cube_mu in (0.3, 2.0):
            model, data = build(pad_priority=prio, cube_friction=cube_mu)
            close_on_cube(model, data)
            mus = pad_forces(model, data)[2]
            print(f"  pad priority {prio}, pad friction 1.5, cube friction {cube_mu}: contact friction {mus}")


def twist(condim: int) -> float:
    """Torque about the grasp axis (N m) at which a held, lifted cube turns by more than 2 degrees."""
    model, data = build(condim=condim)
    close_on_cube(model, data)
    for k in range(50):                                   # lift 0.1 m slowly
        data.ctrl[2] = -0.33 + 0.1 * (k + 1) / 50
        run(model, data, 0.02)
    run(model, data, 0.3)
    cube = model.body("cube").id
    q0 = data.xquat[cube].copy()
    axis = data.xmat[model.body("gripper/finger_left").id].reshape(3, 3)[:, 1]   # the line through both pads
    for k in range(400):                                  # ramp 0 -> 1 N m over 4 s
        torque = 1.0 * k / 400
        data.xfrc_applied[cube, 3:] = torque * axis
        run(model, data, 0.01)
        dq = np.zeros(3)
        mujoco.mju_subQuat(dq, data.xquat[cube], q0)
        if np.linalg.norm(dq) > np.radians(2):
            return torque
    return float("nan")


if __name__ == "__main__":
    print("(1) coupling: one command, two fingers")
    coupling()
    print("(2) squeeze: what sets the grip force (cube 40 mm wide)")
    squeeze()
    print("(3) friction budget: cubes at fractions of m*, lifted 0.1 m and held 4 s")
    friction_budget()
    print("(4) which friction coefficient the pad contacts use")
    friction_mixing()
    print("(5) twisting a held cube about the line through both pads")
    for condim in (4, 3):
        print(f"  pads with condim {condim}: the cube turns 2 degrees at {twist(condim):.3f} N m")
