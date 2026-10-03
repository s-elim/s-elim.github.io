"""Lesson 10.1: grasping under motion: the friction budget, fast lifts and transports, a slip audit.

INPUT   gantry_gripper.xml (parallel gripper on a Cartesian gantry), a 1 kg cube
PROCESS (1) the grasp's friction budget: pad normal force, friction coefficient, the
            static capacity and the largest vertical and horizontal accelerations a
            1 kg cube can take;
        (2) lift the cube 0.1 m with minimum-jerk profiles of decreasing duration:
            planned and delivered peak acceleration, slip, outcome;
        (3) carry it 0.2 m sideways the same way;
        (4) the slip audit: MuJoCo's documented checklist evaluated for this grasp
OUTPUT  printed tables

Run:  python examples/l10_1_grasping.py
"""

import math

import mujoco
import numpy as np

from mjcourse import model_path

G, MASS, GRIP = 9.81, 1.0, 3                      # cube mass (kg), gripper actuator index


def scene() -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(model_path("gantry_gripper")))
    model.body_mass[model.body("cube").id] = MASS
    data = mujoco.MjData(model)
    mujoco.mj_setConst(model, data)
    return model, data


def run(model, data, seconds: float) -> None:
    for _ in range(round(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)


def min_jerk(s: float) -> float:
    s = min(max(s, 0.0), 1.0)
    return 10 * s**3 - 15 * s**4 + 6 * s**5


def grasp(model, data) -> None:
    """Settle, descend 0.33 m, close, then raise 3 cm slowly so the cube hangs free."""
    mujoco.mj_resetDataKeyframe(model, data, 0)
    run(model, data, 0.3)
    for k in range(100):
        data.ctrl[2] = -0.33 * min_jerk((k + 1) / 100)
        run(model, data, 0.01)
    run(model, data, 0.3)
    data.ctrl[GRIP] = 0.0
    run(model, data, 0.6)
    for k in range(100):
        data.ctrl[2] = -0.33 + 0.03 * min_jerk((k + 1) / 100)
        run(model, data, 0.01)
    run(model, data, 0.3)


def pad_normal(model, data) -> tuple[float, float, int]:
    pad, cube = model.geom("gripper/pad_left").id, model.geom("cube").id
    total, mu, n, f = 0.0, 0.0, 0, np.zeros(6)
    for i in range(data.ncon):
        c = data.contact[i]
        if {c.geom1, c.geom2} == {pad, cube}:
            mujoco.mj_contactForce(model, data, i, f)
            total, mu, n = total + f[0], c.friction[0], n + 1
    return total, mu, n


def move(axis: int, distance: float, duration: float) -> tuple[float, float, str]:
    """Move the gantry along one axis with a minimum-jerk profile, hold 0.5 s; return
    (delivered peak acceleration, slip in mm, outcome)."""
    model, data = scene()
    grasp(model, data)
    cube, tcp = model.body("cube").id, model.site("gripper/tcp").id
    offset = data.site_xpos[tcp] - data.xpos[cube]
    start, n = data.ctrl[axis], max(1, round(duration / model.opt.timestep))
    peak = 0.0
    for k in range(n + 250):
        data.ctrl[axis] = start + distance * min_jerk((k + 1) / n)
        mujoco.mj_step(model, data)
        peak = max(peak, abs(data.qacc[axis]))              # the carriage's actual acceleration
    slip = 1000 * float(np.linalg.norm((data.site_xpos[tcp] - data.xpos[cube]) - offset))
    outcome = "dropped" if data.xpos[cube][2] < 0.025 else ("slipped" if slip > 5 else "held")
    return peak, slip, outcome


def budget() -> tuple[float, float]:
    model, data = scene()
    grasp(model, data)
    normal, mu, n = pad_normal(model, data)
    capacity = 2 * mu * normal
    a_up = capacity / MASS - G
    a_side = math.sqrt((capacity / MASS) ** 2 - G**2)
    print(f"  pad normal force {normal:.2f} N ({n} contacts per pad), contact friction {mu}, friction budget 2 mu N = {capacity:.2f} N")
    print(f"  static capacity 2 mu N / g = {capacity / G:.2f} kg; for the {MASS} kg cube: largest upward acceleration "
          f"2 mu N / m - g = {a_up:.2f} m/s^2, largest horizontal sqrt((2 mu N / m)^2 - g^2) = {a_side:.2f} m/s^2")
    return a_up, a_side


def sweep(axis: int, distance: float, durations, limit: float, name: str) -> None:
    print(f"  {'duration (s)':>12}{'planned peak (m/s^2)':>22}{'delivered peak (m/s^2)':>24}{'slip (mm)':>11}{'outcome':>10}")
    for duration in durations:
        planned = 5.7735 * distance / duration**2               # peak of a minimum-jerk acceleration
        peak, slip, outcome = move(axis, distance, duration)
        flag = " (over budget)" if peak > limit else ""
        print(f"  {duration:>12.2f}{planned:>22.1f}{peak:>24.1f}{slip:>11.2f}{outcome:>10}{flag}")
    print(f"  {name} budget: {limit:.2f} m/s^2")


def audit() -> None:
    model, data = scene()
    grasp(model, data)
    normal, mu, n = pad_normal(model, data)
    pad = model.geom("gripper/pad_left").id
    force_limit = model.actuator_forcerange[GRIP, 1]
    checks = [
        ("normal force: squeeze x mu vs weight", f"{mu * normal:.1f} N of friction per pad in use, {mu * force_limit / 2:.1f} N "
         f"if the servo saturated, weight per pad {MASS * G / 2:.2f} N", mu * normal > MASS * G / 2),
        ("friction coefficient", f"{mu} (pad priority {model.geom_priority[pad]} fixes it at the pad's value)", mu >= 1.0),
        ("torsional friction", f"condim {model.geom_condim[pad]}, torsional coefficient {model.geom_friction[pad][1]} m", model.geom_condim[pad] >= 4),
        ("contact points", f"{n} per pad (box-box collider)", n >= 3),
        ("integrator (explicit damping causes vibration)", mujoco.mjtIntegrator(model.opt.integrator).name,
         model.opt.integrator in (int(mujoco.mjtIntegrator.mjINT_IMPLICITFAST), int(mujoco.mjtIntegrator.mjINT_IMPLICIT))),
        ("slow slippage: cone and impratio", f"{mujoco.mjtCone(model.opt.cone).name}, impratio {model.opt.impratio:g}, "
         f"noslip {model.opt.noslip_iterations}", model.opt.cone == int(mujoco.mjtCone.mjCONE_ELLIPTIC) and model.opt.impratio > 1),
    ]
    for name, value, ok in checks:
        print(f"  [{'ok' if ok else 'check'}] {name:<48} {value}")


if __name__ == "__main__":
    print(f"(1) the friction budget of the gantry grasp, {MASS} kg cube")
    a_up, a_side = budget()
    print("(2) lift 0.1 m, minimum-jerk")
    sweep(2, 0.1, (1.0, 0.5, 0.3, 0.2, 0.15, 0.1), a_up, "upward")
    print("(3) carry 0.2 m along x, minimum-jerk")
    sweep(0, 0.2, (1.0, 0.5, 0.3, 0.25, 0.2, 0.15), a_side, "horizontal")
    print("(4) slip audit: MuJoCo's documented checklist for preventing slip, applied to this grasp")
    audit()
