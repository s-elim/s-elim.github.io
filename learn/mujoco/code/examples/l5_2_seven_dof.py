"""Lesson 5.2: checking a 7-DOF arm built from primitives.

INPUT   arm7.xml
PROCESS (1) tabulate each joint: axis, range, armature, damping, torque limit, its
            diagonal entry of M at the home pose with and without armature, and the
            largest timestep at which a controller's damping gain kd stays stable;
        (2) singular values of the 6x7 tool Jacobian at the zero and home poses;
        (3) gravity torque over random poses against the motor limits;
        (4) self-collision over random poses within the joint ranges;
        (5) hold the home pose at h = 2 ms with and without armature, under gravity
            compensation alone and under a joint PD controller;
        (6) find the controller damping at which the bare wrist (no armature) goes
            unstable, and compare with the bound h < 2 I / (kd - b)
OUTPUT  printed tables

Run:  python examples/l5_2_seven_dof.py
"""

import os

import mujoco
import numpy as np

from mjcourse import model_path

N_POSES = 2000 if os.environ.get("MJC_FAST") == "1" else 10000


def load() -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    return model, mujoco.MjData(model)


def mass_matrix(model, data) -> np.ndarray:
    mass = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, mass)
    return mass


KP, KD = 100.0, 5.0        # joint PD gains used in (1) and (5): N m/rad, N m s/rad


def h_max(inertia: float, b: float, kd: float = KD) -> str:
    """Largest stable step for explicit damping kd on a joint whose damping b is implicit (Euler)."""
    return "any" if kd <= b else f"{1000 * 2 * inertia / (kd - b):.2f} ms"


def joint_table(model, data) -> None:
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    with_arm = np.diag(mass_matrix(model, data)).copy()
    bare = with_arm - model.dof_armature                  # armature adds to the diagonal only
    print(f"  {'joint':<5}{'axis':>5}{'range (rad)':>15}{'armature':>10}{'damping':>9}{'limit':>7}"
          f"{'M_ii':>9}{'M_ii bare':>11}{'h_max':>10}{'bare':>11}")
    for j in range(model.njnt):
        axis = "xyz"[int(np.argmax(np.abs(model.jnt_axis[j])))]
        print(f"  {model.joint(j).name:<5}{axis:>5}{np.array2string(model.jnt_range[j], precision=1):>15}"
              f"{model.dof_armature[j]:>10.3f}{model.dof_damping[j]:>9.2f}{model.actuator_ctrlrange[j, 1]:>7.0f}"
              f"{with_arm[j]:>9.4f}{bare[j]:>11.5f}{h_max(with_arm[j], model.dof_damping[j]):>10}{h_max(bare[j], model.dof_damping[j]):>11}")
    print(f"  units: limit N m, M_ii kg m^2 at the home pose; h_max = 2 M_ii / (kd - b) for a controller")
    print(f"  damping kd = {KD} N m s/rad on top of the joint's own damping b, which Euler treats implicitly")


def jacobian_svd(model, data) -> None:
    site = model.site("ee").id
    jacp, jacr = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    for key in ("zero", "home"):
        mujoco.mj_resetDataKeyframe(model, data, model.key(key).id)
        mujoco.mj_forward(model, data)
        mujoco.mj_jacSite(model, data, jacp, jacr, site)
        sv = np.linalg.svd(np.vstack([jacp, jacr]), compute_uv=False)
        rank = int(np.sum(sv > 1e-9 * sv[0]))
        print(f"  {key:<5} singular values {np.round(sv, 4)}  rank {rank}  "
              f"manipulability sqrt(det(J J^T)) = {np.prod(sv):.2e}")


def gravity_budget(model, data) -> None:
    rng = np.random.default_rng(0)
    lo, hi = model.jnt_range[:, 0], model.jnt_range[:, 1]
    peak = np.zeros(model.nv)
    over = 0
    for _ in range(N_POSES):
        data.qpos[:] = rng.uniform(lo, hi)
        data.qvel[:] = 0
        mujoco.mj_forward(model, data)
        tau = np.abs(data.qfrc_bias)
        peak = np.maximum(peak, tau)
        over += bool(np.any(tau > model.actuator_ctrlrange[:, 1]))
    limit = model.actuator_ctrlrange[:, 1]
    ratio = ["-" if p < 1e-9 else f"{lim / p:.2f}" for lim, p in zip(limit, peak)]
    print(f"  {N_POSES} random poses within the ranges: largest gravity torque per joint (N m) {np.round(peak, 2)}")
    print(f"  motor limit / largest gravity torque: {' '.join(ratio)}  (- : vertical axis, gravity never loads it)")
    print(f"  poses where some joint's gravity torque exceeds its motor limit: {over}")


def self_collision(model, data) -> None:
    rng = np.random.default_rng(1)
    lo, hi = model.jnt_range[:, 0], model.jnt_range[:, 1]
    hits, pairs = 0, {}
    for _ in range(N_POSES):
        data.qpos[:] = rng.uniform(lo, hi)
        mujoco.mj_forward(model, data)
        if data.ncon:
            hits += 1
        for c in data.contact[:data.ncon]:
            key = " / ".join(sorted((model.geom(c.geom1).name, model.geom(c.geom2).name)))
            pairs[key] = pairs.get(key, 0) + 1
    print(f"  {N_POSES} random poses: {100 * hits / N_POSES:.1f}% have at least one self-contact")
    for key, n in sorted(pairs.items(), key=lambda kv: -kv[1])[:4]:
        print(f"    {key:<24} {n} poses")
    for key in ("zero", "home"):
        mujoco.mj_resetDataKeyframe(model, data, model.key(key).id)
        mujoco.mj_forward(model, data)
        print(f"  contacts at the {key} pose: {data.ncon}")


def wrist_peak(kd: float, kp: float, seconds: float = 4.0) -> float:
    """Largest |qvel| of j7 over the last quarter of a hold with no armature anywhere."""
    model, data = load()
    model.dof_armature[:] = 0
    key = model.key("home").id
    mujoco.mj_resetDataKeyframe(model, data, key)
    target = model.key_qpos[key].copy()
    data.qvel[:] = 0.01
    n = round(seconds / model.opt.timestep)
    peak = 0.0
    for i in range(n):
        mujoco.mj_forward(model, data)
        data.ctrl[:] = data.qfrc_bias + kp * (target - data.qpos) - kd * data.qvel
        mujoco.mj_step(model, data)
        if i > 0.75 * n:
            peak = max(peak, abs(data.qvel[6]))
    return peak


def wrist_threshold() -> None:
    model, data = load()
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    inertia = mass_matrix(model, data)[6, 6] - model.dof_armature[6]
    b, h = model.dof_damping[6], model.opt.timestep
    print(f"  bare j7: I = {inertia:.6f} kg m^2, b = {b} N m s/rad, h = {h} s -> bound predicts kd < b + 2 I / h = {b + 2 * inertia / h:.3f}")
    for kp in (0.0, KP):
        stable = [kd for kd in np.arange(0.50, 0.81, 0.02) if wrist_peak(kd, kp) < 1e-3]
        print(f"  kp {kp:>5g}: stable for kd up to {max(stable):.2f}, unstable from {max(stable) + 0.02:.2f} N m s/rad")


def hold_home(armature: float, integrator: str, pd: bool, eulerdamp: bool = True, seconds: float = 2.0) -> str:
    model, data = load()
    model.dof_armature[:] = armature
    model.opt.integrator = getattr(mujoco.mjtIntegrator, integrator)
    if not eulerdamp:
        model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_EULERDAMP
    key = model.key("home").id
    mujoco.mj_resetDataKeyframe(model, data, key)
    target = model.key_qpos[key].copy()
    data.qvel[:] = 0.01                                   # a small disturbance
    peak = np.zeros(model.nv)
    for _ in range(round(seconds / model.opt.timestep)):
        mujoco.mj_forward(model, data)
        data.ctrl[:] = data.qfrc_bias                     # gravity compensation (clamped to ctrlrange)
        if pd:
            data.ctrl[:] += KP * (target - data.qpos) - KD * data.qvel
        mujoco.mj_step(model, data)
        peak = np.maximum(peak, np.abs(data.qvel))
    warn = data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number
    j = int(np.argmax(peak))
    return f"max |qvel| {peak[j]:9.3g} rad/s at {model.joint(j).name}, bad-acceleration warnings {warn}"


if __name__ == "__main__":
    model, data = load()
    print("(1) joints, inertia and the explicit-damping timestep bound:")
    joint_table(model, data)
    print("(2) singular values of the 6x7 Jacobian of the ee site:")
    jacobian_svd(model, data)
    print("(3) gravity torque against motor limits:")
    gravity_budget(model, data)
    print("(4) self-collision:")
    self_collision(model, data)
    print(f"(5) hold the home pose for 2 s at h = 2 ms after a 0.01 rad/s nudge (PD: kp {KP:g}, kd {KD:g}):")
    cases = [
        ("gravity compensation only", 0.0, "mjINT_EULER", False, True),
        ("  same, eulerdamp disabled", 0.0, "mjINT_EULER", False, False),
        ("joint PD", 0.05, "mjINT_EULER", True, True),
        ("joint PD", 0.0, "mjINT_EULER", True, True),
        ("joint PD", 0.0, "mjINT_IMPLICITFAST", True, True),
    ]
    for label, arm, integ, pd, eulerdamp in cases:
        name = {"mjINT_EULER": "Euler", "mjINT_IMPLICITFAST": "implicitfast"}[integ]
        print(f"  {label:<28} armature {arm:<5} {name:<13} {hold_home(arm, integ, pd, eulerdamp)}")
    print("(6) the bare wrist's stability threshold in kd (no armature, Euler, h = 2 ms):")
    wrist_threshold()
