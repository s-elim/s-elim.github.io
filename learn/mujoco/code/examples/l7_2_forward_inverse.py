"""Lesson 7.2: forward and inverse dynamics, and making them agree through a timestep.

INPUT   arm7.xml; a 1 kg box on a plane, written below
PROCESS (1) mj_forward then mj_inverse at random states: the inverse recovers the
            applied forces; the forward-inverse check flag; the terms of qfrc_inverse;
        (2) torques for a 2 s minimum-jerk motion from mj_inverse, replayed open loop
            with mj_step, four ways: analytic or integrator-consistent accelerations,
            with or without the discrete-time inverse flag; then the exact recipe
            under the other integrators;
        (3) inverse dynamics with contact: the force needed to hold a box still at
            heights around its rest pose, for two contact stiffnesses
OUTPUT  printed tables

Run:  python examples/l7_2_forward_inverse.py
"""

import os

import mujoco
import numpy as np

from mjcourse import model_path

N = 200 if os.environ.get("MJC_FAST") == "1" else 1000
INVDISCRETE = int(mujoco.mjtEnableBit.mjENBL_INVDISCRETE)
BOX = """<mujoco><option timestep="0.002"/><worldbody><geom type="plane" size="1 1 .1"/>
<body name="box" pos="0 0 0.05"><freejoint/><geom type="box" size=".05 .05 .05" mass="1" solref="{tc} 1"/></body>
</worldbody></mujoco>"""


def inverse_undoes_forward() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(N):
        data.qpos[:] = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        data.qvel[:] = rng.normal(size=model.nv)
        data.ctrl[:] = rng.uniform(model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        data.qfrc_applied[:] = rng.normal(scale=2.0, size=model.nv)
        mujoco.mj_forward(model, data)                  # torques -> qacc
        applied = data.qfrc_actuator + data.qfrc_applied
        mujoco.mj_inverse(model, data)                  # qacc -> the forces that must have been applied
        worst = max(worst, np.abs(data.qfrc_inverse - applied).max())
    print(f"  {N} random states: max |qfrc_inverse - (qfrc_actuator + qfrc_applied)| = {worst:.1e} N m")
    mass = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, mass)
    terms = mass @ data.qacc + data.qfrc_bias - data.qfrc_passive - data.qfrc_constraint
    print(f"  qfrc_inverse = M qacc + qfrc_bias - qfrc_passive - qfrc_constraint: max difference "
          f"{np.abs(terms - data.qfrc_inverse).max():.1e} N m")


def min_jerk(q0, q1, duration):
    def at(t):
        s = np.clip(t / duration, 0.0, 1.0)
        p = 10 * s**3 - 15 * s**4 + 6 * s**5
        dp = (30 * s**2 - 60 * s**3 + 30 * s**4) / duration
        ddp = (60 * s - 180 * s**2 + 120 * s**3) / duration**2
        return q0 + (q1 - q0) * p, (q1 - q0) * dp, (q1 - q0) * ddp
    return at


def torque_from_motion() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    h, duration = model.opt.timestep, 2.0
    q0 = model.key_qpos[model.key("home").id].copy()
    q1 = q0 + np.array([0.6, -0.3, 0.4, -0.5, 0.5, 0.4, 0.8])
    path = min_jerk(q0, q1, duration)
    n = round(duration / h)
    samples = np.array([path(k * h)[0] for k in range(n + 2)])   # the positions the replay must hit

    def torques(accel: str, invdiscrete: bool) -> np.ndarray:
        data = mujoco.MjData(model)
        model.opt.enableflags = (model.opt.enableflags | INVDISCRETE) if invdiscrete else (model.opt.enableflags & ~INVDISCRETE)
        tau = np.zeros((n, model.nv))
        for k in range(n):
            if accel == "analytic":                     # the continuous-time trajectory at t_k
                q, v, a = path(k * h)
            else:                                       # what semi-implicit Euler needs to land on the samples:
                q = samples[k]                          # v_{k+1} = v_k + h a_k, q_{k+1} = q_k + h v_{k+1}
                v = (samples[k] - samples[k - 1]) / h if k else np.zeros(model.nv)
                a = ((samples[k + 1] - samples[k]) / h - v) / h
            data.qpos[:], data.qvel[:], data.qacc[:] = q, v, a
            mujoco.mj_inverse(model, data)
            tau[k] = data.qfrc_inverse
        model.opt.enableflags &= ~INVDISCRETE
        return tau

    def replay(tau: np.ndarray) -> np.ndarray:
        data = mujoco.MjData(model)
        data.qpos[:] = q0
        err = np.zeros(n)
        for k in range(n):
            data.ctrl[:] = tau[k]                       # motors with gear 1: ctrl is joint torque
            mujoco.mj_step(model, data)
            err[k] = np.abs(data.qpos - samples[k + 1]).max()
        return err

    print(f"  motion: home to home + [0.6, -0.3, 0.4, -0.5, 0.5, 0.4, 0.8] rad in {duration} s, Euler, h = {h} s")
    for accel, inv in (("analytic", False), ("analytic", True), ("integrator-consistent", False), ("integrator-consistent", True)):
        tau = torques(accel, inv)
        err = replay(tau)
        print(f"  {accel:<22} invdiscrete {str(inv):<5}: max joint error at 0.5 s {err[n // 4 - 1]:.1e}, "
              f"1 s {err[n // 2 - 1]:.1e}, 2 s {err[-1]:.1e} rad")
    print(f"  largest torque over the motion / motor limit: {np.max(np.abs(tau) / model.actuator_ctrlrange[:, 1]):.2f}")
    for name in ("mjINT_IMPLICITFAST", "mjINT_IMPLICIT", "mjINT_RK4"):
        model.opt.integrator = getattr(mujoco.mjtIntegrator, name)
        try:
            err = replay(torques("integrator-consistent", True))
            print(f"  {name[6:].lower():<13} integrator-consistent, invdiscrete True: max joint error over 2 s {err.max():.1e} rad")
        except mujoco.FatalError as exc:
            model.opt.enableflags &= ~INVDISCRETE
            print(f"  {name[6:].lower():<13} mj_inverse with invdiscrete raises: {exc}")


def contact_inverse() -> None:
    for tc in (0.02, 0.005):
        model = mujoco.MjModel.from_xml_string(BOX.format(tc=tc))
        data = mujoco.MjData(model)
        for _ in range(2000):                           # settle onto the plane
            mujoco.mj_step(model, data)
        rest = data.qpos[2]
        row = []
        for dz in (1e-3, 0.0, -2e-4, -5e-4, -1e-3):
            probe = mujoco.MjData(model)
            probe.qpos[:] = data.qpos
            probe.qpos[2] = rest + dz
            probe.qvel[:] = 0
            probe.qacc[:] = 0                           # "hold it perfectly still here"
            mujoco.mj_inverse(model, probe)
            row.append(f"{1000 * dz:+.1f} mm: {probe.qfrc_inverse[2]:+8.2f} N")
        print(f"  solref time constant {tc} s (rests {1000 * (0.05 - rest):.3f} mm deep): " + ", ".join(row))
    model = mujoco.MjModel.from_xml_string(BOX.format(tc=0.02))
    model.opt.enableflags |= int(mujoco.mjtEnableBit.mjENBL_FWDINV)
    data = mujoco.MjData(model)
    worst = np.zeros(2)
    for k in range(1000):                               # rest, then push it into sliding
        data.xfrc_applied[1, :3] = [12.0, 0.0, 0.0] if k > 500 else 0.0
        mujoco.mj_step(model, data)
        worst = np.maximum(worst, data.solver_fwdinv)
    print(f"  with contacts active (box at rest, then sliding under a 12 N push, above its 9.81 N friction limit), the forward-inverse check "
          f"(mjENBL_FWDINV) stays at most {worst[0]:.1e} in qfrc and {worst[1]:.1e} in constraint force")


if __name__ == "__main__":
    print("(1) mj_inverse undoes mj_forward (arm7, no contacts)")
    inverse_undoes_forward()
    print("(2) torque from motion, replayed open loop")
    torque_from_motion()
    print("(3) vertical force needed to hold a 1 kg box still, by height offset from its rest pose")
    contact_inverse()
