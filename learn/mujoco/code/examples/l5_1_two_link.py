"""Lesson 5.1: a two-link arm, checked the way you would check any robot model.

INPUT   arm2.xml (planar arm, explicit inertias, joint stops, torque motors)
PROCESS (1) print what the compiled model contains: joints, axes, ranges, motors, sites;
        (2) compare the end-effector site with the planar forward-kinematics formula;
        (3) compare gravity torque (qfrc_bias at rest) with the hand formula, and
            size the motors: margin over gravity, payload, peak acceleration;
        (4) compare the explicit inertias with what MuJoCo infers from the geoms,
            and show that a visual-only geom still adds mass;
        (5) let the arm fall onto its shoulder stop and measure the soft limit;
        (6) command more torque than ctrlrange allows
OUTPUT  printed tables

Run:  python examples/l5_1_two_link.py
"""

import mujoco
import numpy as np

from mjcourse import model_path

G = 9.81
L1, L2 = 0.5, 0.4          # link lengths (m)
M1, M2 = 1.0, 0.8          # link masses (kg)
C1, C2 = 0.25, 0.2         # centre-of-mass distance from each joint (m)


def load() -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm2")))
    return model, mujoco.MjData(model)


def structure(model: mujoco.MjModel) -> None:
    for j in range(model.njnt):
        jn = model.joint(j)
        print(f"  joint {jn.name:<9} axis {jn.axis}  range {jn.range} rad  limited {bool(model.jnt_limited[j])}"
              f"  damping {model.dof_damping[model.jnt_dofadr[j]]} N m s/rad")
    for a in range(model.nu):
        act = model.actuator(a)
        print(f"  motor {act.name:<9} gear {act.gear[0]:g}  ctrlrange {act.ctrlrange} N m  ctrllimited {bool(model.actuator_ctrllimited[a])}")
    print(f"  sites: {[model.site(i).name for i in range(model.nsite)]}")


def forward_kinematics(model, data) -> None:
    rng = np.random.default_rng(0)
    base = np.array([0.0, 0.0, 1.0])                     # link1's frame: the shoulder axis
    worst = 0.0
    for _ in range(1000):
        q = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        x = L1 * np.cos(q[0]) + L2 * np.cos(q[0] + q[1])
        z = L1 * np.sin(q[0]) + L2 * np.sin(q[0] + q[1])
        worst = max(worst, np.abs(data.site("ee").xpos - (base + [x, 0.0, z])).max())
    print(f"  1000 random poses within the joint ranges: max |site_xpos - formula| = {worst:.1e} m")


def gravity_torque(q: np.ndarray) -> np.ndarray:
    """Torque the motors must supply to hold the arm still at q (the derivative of potential energy)."""
    t2 = G * M2 * C2 * np.cos(q[0] + q[1])
    t1 = G * (M1 * C1 + M2 * L1) * np.cos(q[0]) + t2
    return np.array([t1, t2])


def motor_sizing(model, data) -> None:
    rng = np.random.default_rng(1)
    worst = 0.0
    for _ in range(1000):
        q = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        data.qpos[:] = q
        data.qvel[:] = 0
        mujoco.mj_forward(model, data)
        worst = max(worst, np.abs(data.qfrc_bias - gravity_torque(q)).max())
    print(f"  1000 random poses at rest: max |qfrc_bias - formula| = {worst:.1e} N m")

    data.qpos[:] = 0                       # arm horizontal: the largest gravity torque at both joints
    data.qvel[:] = 0
    mujoco.mj_forward(model, data)
    tau_g = data.qfrc_bias.copy()
    limit = model.actuator_ctrlrange[:, 1]
    print(f"  gravity torque, arm horizontal: shoulder {tau_g[0]:.3f} N m, elbow {tau_g[1]:.3f} N m")
    print(f"  motor limit / gravity torque: shoulder {limit[0] / tau_g[0]:.2f}, elbow {limit[1] / tau_g[1]:.2f}")
    payload = np.array([(limit[0] - tau_g[0]) / (G * (L1 + L2)), (limit[1] - tau_g[1]) / (G * L2)])
    print(f"  largest point payload at the tip, arm horizontal: shoulder allows {payload[0]:.2f} kg, "
          f"elbow allows {payload[1]:.2f} kg -> {payload.min():.2f} kg")
    mass = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, mass)                  # 3.10+: reads the factorized M from data
    acc = (limit[0] - tau_g[0]) / mass[0, 0]            # elbow held rigid: qacc_elbow = 0
    elbow = mass[1, 0] * acc + tau_g[1]                  # elbow torque that keeps it rigid
    print(f"  M(q) at this pose: {np.round(mass, 4).tolist()} kg m^2")
    print(f"  spare shoulder torque {limit[0] - tau_g[0]:.2f} N m gives {acc:.1f} rad/s^2 with the elbow rigid, "
          f"which needs {elbow:.2f} N m at the elbow")


def inferred_inertia(model) -> None:
    xml = model_path("arm2").read_text()
    lines = [ln for ln in xml.splitlines() if "<inertial" not in ln]
    inferred = mujoco.MjModel.from_xml_string("\n".join(lines))
    for name in ("link1", "link2"):
        a, b = model.body(name), inferred.body(name)
        print(f"  {name}: explicit {a.mass[0]:.3f} kg, principal moments {np.round(np.sort(a.inertia), 5)}  |  "
              f"from geoms {b.mass[0]:.3f} kg, {np.round(np.sort(b.inertia), 5)} kg m^2")
    d = mujoco.MjData(inferred)
    mujoco.mj_forward(inferred, d)
    print(f"  gravity torque at the horizontal pose: explicit {gravity_torque(np.zeros(2))[0]:.3f} N m, "
          f"from geoms {d.qfrc_bias[0]:.3f} N m (shoulder)")


def visual_geom_mass() -> None:
    xml = ('<mujoco><compiler {c}/><worldbody><body name="b"><freejoint/>'
           '<geom size=".05" mass="1"/>'
           '<geom size=".05" pos=".2 0 0" mass="2" group="3" contype="0" conaffinity="0"/>'
           '</body></worldbody></mujoco>')
    for compiler in ('', 'inertiagrouprange="0 2"'):
        m = mujoco.MjModel.from_xml_string(xml.format(c=compiler))
        label = compiler or "default inertiagrouprange (0 5)"
        print(f"  1 kg collision geom + 2 kg non-colliding geom in group 3, {label}: body mass {m.body('b').mass[0]:.3f} kg")


def joint_stop(model, data) -> None:
    mujoco.mj_resetData(model, data)
    for _ in range(round(60.0 / model.opt.timestep)):      # damping is light: let the elbow settle
        mujoco.mj_step(model, data)
    lo = model.jnt_range[0, 0]
    limit_rows = [i for i in range(data.nefc) if data.efc_type[i] == mujoco.mjtConstraint.mjCNSTR_LIMIT_JOINT]
    print(f"  after 60 s with zero torque: shoulder at {data.qpos[0]:.5f} rad, stop at {lo} rad "
          f"-> {1000 * (lo - data.qpos[0]):.2f} mrad past the stop")
    print(f"  active limit rows: {len(limit_rows)}; qfrc_constraint[shoulder] = {data.qfrc_constraint[0]:.4f} N m, "
          f"gravity torque qfrc_bias[shoulder] = {data.qfrc_bias[0]:.4f} N m")


def clamping(model, data) -> None:
    mujoco.mj_resetData(model, data)
    data.ctrl[:] = [100.0, -100.0]
    mujoco.mj_forward(model, data)
    print(f"  ctrl = {data.ctrl}: actuator_force = {data.actuator_force} N m (no warning is raised)")


if __name__ == "__main__":
    model, data = load()
    print("(1) what the compiled model contains:")
    structure(model)
    print("(2) forward kinematics of the ee site:")
    forward_kinematics(model, data)
    print("(3) gravity torque and motor sizing:")
    motor_sizing(model, data)
    print("(4) explicit inertias versus inertias inferred from the geoms:")
    inferred_inertia(model)
    visual_geom_mass()
    print("(5) the shoulder stop is a soft constraint:")
    joint_stop(model, data)
    print("(6) commands beyond ctrlrange are clamped:")
    clamping(model, data)
