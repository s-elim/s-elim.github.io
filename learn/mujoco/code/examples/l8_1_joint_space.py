"""Lesson 8.1: joint-space control of one joint: P, PD, PID and MuJoCo's servo actuators.

INPUT   pendulum.xml (1 kg at 0.5 m on a hinge, torque motor limited to +-3 N m)
PROCESS (1) gravity off: PD step responses against the damping-ratio predictions;
        (2) gravity on: the steady-state error of PD, and removing it with gravity
            compensation or with integral action;
        (3) integral windup at the torque limit, a hand-written anti-windup clamp, and
            MuJoCo's <pid> actuator with imax;
        (4) the same PD written in Python versus MuJoCo's <position> actuator, under
            Euler and implicitfast, at a damping gain beyond the explicit limit
OUTPUT  printed tables

Run:  python examples/l8_1_joint_space.py
"""

import math

import mujoco
import numpy as np

from mjcourse import model_path

M, L, G = 1.0, 0.5, 9.81
I_PIVOT = M * L**2 + 1e-4                 # kg m^2, from pendulum.xml's <inertial>


def pendulum(gravity: bool = True, torque_limit: float = 3.0):
    model = mujoco.MjModel.from_xml_path(str(model_path("pendulum")))
    if not gravity:
        model.opt.gravity[:] = 0
    model.actuator_ctrlrange[0] = [-torque_limit, torque_limit]
    return model, mujoco.MjData(model)


def run(model, data, policy, seconds: float) -> np.ndarray:
    """Step with ctrl = policy(data); return the angle after each step."""
    out = np.zeros(round(seconds / model.opt.timestep))
    for k in range(len(out)):
        data.ctrl[0] = policy(data)
        mujoco.mj_step(model, data)
        out[k] = data.qpos[0]
    return out


def step_responses() -> None:
    kp, target = 20.0, 0.5
    omega = math.sqrt(kp / I_PIVOT)
    print(f"  kp {kp} N m/rad, I {I_PIVOT} kg m^2 -> natural frequency {omega:.3f} rad/s; step of {target} rad")
    print(f"  {'zeta':>6}{'kd':>8}{'overshoot predicted':>21}{'measured':>10}{'peak time predicted':>21}{'measured':>10}")
    for zeta in (0.1, 0.3, 0.5, 0.7, 1.0):
        kd = 2 * zeta * math.sqrt(kp * I_PIVOT)
        model, data = pendulum(gravity=False, torque_limit=100.0)
        q = run(model, data, lambda d: kp * (target - d.qpos[0]) - kd * d.qvel[0], 3.0)
        over = 100 * max(q.max() - target, 0) / target
        pred = 100 * math.exp(-math.pi * zeta / math.sqrt(1 - zeta**2)) if zeta < 1 else 0.0
        tpk_pred = f"{math.pi / (omega * math.sqrt(1 - zeta**2)):.3f} s" if zeta < 1 else "none"
        tpk = f"{(np.argmax(q) + 1) * model.opt.timestep:.3f} s" if zeta < 1 else "none"
        print(f"  {zeta:>6.1f}{kd:>8.3f}{pred:>19.1f} %{over:>8.1f} %{tpk_pred:>21}{tpk:>10}")


def gravity_error() -> None:
    target = 0.5
    tau_g = M * G * L * math.sin(target)
    for kp in (10.0, 20.0, 50.0):
        kd = 2 * math.sqrt(kp * I_PIVOT)
        model, data = pendulum()
        q = run(model, data, lambda d: kp * (target - d.qpos[0]) - kd * d.qvel[0], 6.0)
        # Equilibrium: kp (target - q) = m g L sin q; to first order e = m g L sin(target) / (kp + m g L cos(target)).
        pred = tau_g / (kp + M * G * L * math.cos(target))
        print(f"  PD, kp {kp:>4.0f}: steady-state error {1000 * (target - q[-1]):6.1f} mrad, "
              f"first-order prediction {1000 * pred:6.1f} mrad")
    kp = 20.0
    kd = 2 * math.sqrt(kp * I_PIVOT)
    model, data = pendulum()
    q = run(model, data, lambda d: kp * (target - d.qpos[0]) - kd * d.qvel[0] + M * G * L * math.sin(d.qpos[0]), 6.0)
    print(f"  PD + gravity compensation m g L sin q, kp {kp:.0f}: steady-state error {1000 * (target - q[-1]):.4f} mrad")
    integral = [0.0]

    def pid(d, ki=20.0):
        e = target - d.qpos[0]
        integral[0] += e * model.opt.timestep
        return kp * e - kd * d.qvel[0] + ki * integral[0]

    model, data = pendulum()
    q = run(model, data, pid, 6.0)
    print(f"  PID, kp {kp:.0f}, ki 20: error after 6 s {1000 * (target - q[-1]):.4f} mrad")


def windup() -> None:
    target, kp, ki = 0.55, 20.0, 40.0     # holding 0.55 rad takes 2.56 N m of the 3 N m available
    kd = 2 * math.sqrt(kp * I_PIVOT)
    print(f"  holding {target} rad needs an integral of m g L sin(target) / ki = {M * G * L * math.sin(target) / ki:.4f} rad s")
    for clamp in (None, 0.05, 0.07):
        integral = [0.0]
        model, data = pendulum()

        def pid(d):
            e = target - d.qpos[0]
            integral[0] += e * model.opt.timestep
            if clamp is not None:
                integral[0] = min(max(integral[0], -clamp), clamp)
            return kp * e - kd * d.qvel[0] + ki * integral[0]

        q = run(model, data, pid, 8.0)
        label = "no anti-windup" if clamp is None else f"integral clamped at +-{clamp} rad s"
        settle = np.flatnonzero(np.abs(q - target) > 0.01)
        print(f"  Python PID, {label:<32}: peak {1000 * (q.max() - target):+6.1f} mrad from target, "
              f"inside 10 mrad after {(settle[-1] + 1) * model.opt.timestep if len(settle) else 0:.2f} s"
              f"{'' if settle[-1] + 1 < len(q) else ' (never: the clamp is below the integral the hold needs)'}")
    xml = model_path("pendulum").read_text().replace(
        '<motor name="torque" joint="hinge" gear="1" ctrlrange="-3 3"/>',
        f'<pid name="pid" joint="hinge" kp="{kp}" kv="{kd:.6f}" ki="{ki}" imax="0.07" input="pos" forcerange="-3 3"/>')
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    q = run(model, data, lambda d: target, 8.0)
    settle = np.flatnonzero(np.abs(q - target) > 0.01)
    print(f"  MuJoCo <pid> actuator, ki {ki:.0f}, imax 0.07{'':<15}: peak {1000 * (q.max() - target):+6.1f} mrad from target, "
          f"inside 10 mrad after {(settle[-1] + 1) * model.opt.timestep:.2f} s; act holds the integral: {data.act[0]:.4f}")


def servo_versus_python() -> None:
    kp, kv, target = 100.0, 300.0, 0.3       # kv beyond the explicit limit 2 I / h = 250 N m s/rad
    print(f"  kp {kp}, kv {kv} N m s/rad, h 2 ms: explicit damping is stable only for kv < 2 I / h = {2 * I_PIVOT / 0.002:.0f}")
    for integrator in ("mjINT_EULER", "mjINT_IMPLICITFAST"):
        model, data = pendulum(gravity=False, torque_limit=1e6)
        model.opt.integrator = getattr(mujoco.mjtIntegrator, integrator)
        q = run(model, data, lambda d: kp * (target - d.qpos[0]) - kv * d.qvel[0], 4.0)
        xml = model_path("pendulum").read_text().replace(
            '<motor name="torque" joint="hinge" gear="1" ctrlrange="-3 3"/>',
            f'<position name="servo" joint="hinge" kp="{kp}" kv="{kv}"/>')
        smodel = mujoco.MjModel.from_xml_string(xml)
        smodel.opt.gravity[:] = 0
        smodel.opt.integrator = model.opt.integrator
        sdata = mujoco.MjData(smodel)
        qs = run(smodel, sdata, lambda d: target, 4.0)
        name = integrator[6:].lower()
        print(f"  {name:<13} PD in Python: angle after 4 s {q[-1]:.4g} rad (max |q| {np.abs(q).max():.3g}); "
              f"<position> actuator: {qs[-1]:.4g} rad (max |q| {np.abs(qs).max():.3g})")


if __name__ == "__main__":
    print("(1) PD step responses, gravity off")
    step_responses()
    print("(2) under gravity: steady-state error, and two ways to remove it (target 0.5 rad)")
    gravity_error()
    print("(3) integral windup at the 3 N m limit (target 0.55 rad, kp 20, ki 40)")
    windup()
    print("(4) the same PD in Python and as a <position> actuator, gravity off, step to 0.3 rad")
    servo_versus_python()
