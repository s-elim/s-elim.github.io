"""Lesson 7.1: the equations of motion MuJoCo solves, derived and read out of the engine.

INPUT   arm2.xml (planar two-link arm, explicit inertias), arm7.xml
PROCESS (1) the two-link mass matrix and bias forces from the Lagrangian, against
            mj_fullM and qfrc_bias at random states;
        (2) where armature and joint damping enter: M's diagonal and qfrc_passive;
        (3) the full balance M qacc + qfrc_bias = qfrc_actuator + qfrc_passive +
            qfrc_constraint + qfrc_applied on arm7, with random states and controls;
        (4) kinetic energy as 1/2 qdot^T M qdot against MuJoCo's energy, and the
            spread of M's eigenvalues with and without armature
OUTPUT  printed comparisons

Run:  python examples/l7_1_equations_of_motion.py
"""

import os

import mujoco
import numpy as np

from mjcourse import model_path

N = 200 if os.environ.get("MJC_FAST") == "1" else 1000
G = 9.81
M1, M2, L1, C1, C2 = 1.0, 0.8, 0.5, 0.25, 0.2       # masses (kg), link 1 length, COM distances (m)
I1, I2 = 0.0208333, 0.0106667                      # COM inertias as written in arm2.xml (kg m^2)
I1_ROD, I2_ROD = 1.0 * 0.5**2 / 12, 0.8 * 0.4**2 / 12   # the exact thin-rod values they round


def mass_matrix_2link(q: np.ndarray, i1: float = I1, i2: float = I2) -> np.ndarray:
    c2 = np.cos(q[1])
    m11 = i1 + i2 + M1 * C1**2 + M2 * (L1**2 + C2**2 + 2 * L1 * C2 * c2)
    m12 = i2 + M2 * (C2**2 + L1 * C2 * c2)
    m22 = i2 + M2 * C2**2
    return np.array([[m11, m12], [m12, m22]])


def bias_2link(q: np.ndarray, qd: np.ndarray) -> np.ndarray:
    """Coriolis, centrifugal and gravity terms: the torque needed when qacc = 0."""
    h = M2 * L1 * C2 * np.sin(q[1])
    coriolis = np.array([-h * (2 * qd[0] * qd[1] + qd[1] ** 2), h * qd[0] ** 2])
    g2 = G * M2 * C2 * np.cos(q[0] + q[1])
    gravity = np.array([G * (M1 * C1 + M2 * L1) * np.cos(q[0]) + g2, g2])
    return coriolis + gravity


def full_mass(model, data) -> np.ndarray:
    m = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, m)
    return m


def two_link() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm2")))
    data = mujoco.MjData(model)
    rng = np.random.default_rng(0)
    e_m = e_rod = e_b = 0.0
    for _ in range(N):
        data.qpos[:] = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        data.qvel[:] = rng.normal(scale=3.0, size=2)
        mujoco.mj_forward(model, data)
        m = full_mass(model, data)
        e_m = max(e_m, np.abs(m - mass_matrix_2link(data.qpos)).max())
        e_rod = max(e_rod, np.abs(m - mass_matrix_2link(data.qpos, I1_ROD, I2_ROD)).max())
        e_b = max(e_b, np.abs(data.qfrc_bias - bias_2link(data.qpos, data.qvel)).max())
    print(f"  {N} random states (q in range, qdot ~ N(0, 3 rad/s)):")
    print(f"    max |mj_fullM - M(q)| = {e_m:.1e} kg m^2 with the inertias as written in the XML, "
          f"{e_rod:.1e} with the exact m L^2 / 12 they round")
    print(f"    max |qfrc_bias - c(q, qdot) - g(q)| = {e_b:.1e} N m")
    data.qpos[:] = [0.0, 0.0]
    mujoco.mj_forward(model, data)
    print(f"  M at q = (0, 0): {np.round(full_mass(model, data), 5).tolist()} kg m^2")
    data.qpos[:] = [0.0, np.pi / 2]
    mujoco.mj_forward(model, data)
    print(f"  M at q = (0, pi/2): {np.round(full_mass(model, data), 5).tolist()} kg m^2 (the off-diagonal shrinks as the elbow bends)")


def armature_and_damping() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm2")))
    data = mujoco.MjData(model)
    data.qpos[:] = [0.3, -0.8]
    data.qvel[:] = [1.5, -2.0]
    mujoco.mj_forward(model, data)
    bare = full_mass(model, data)
    model.dof_armature[:] = 0.1
    mujoco.mj_forward(model, data)
    print(f"  armature 0.1 kg m^2 on both joints: M changes by {np.round(full_mass(model, data) - bare, 6).tolist()}")
    print(f"  qfrc_passive = {np.round(data.qfrc_passive, 6)} N m; -damping * qvel = {np.round(-model.dof_damping * data.qvel, 6)} N m "
          f"(damping is not part of qfrc_bias)")


def balance() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    rng = np.random.default_rng(1)
    worst = 0.0
    for _ in range(N):
        data.qpos[:] = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        data.qvel[:] = rng.normal(scale=1.0, size=model.nv)
        data.ctrl[:] = rng.uniform(model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        data.qfrc_applied[:] = rng.normal(scale=2.0, size=model.nv)
        mujoco.mj_forward(model, data)
        lhs = full_mass(model, data) @ data.qacc + data.qfrc_bias
        rhs = data.qfrc_actuator + data.qfrc_passive + data.qfrc_constraint + data.qfrc_applied
        worst = max(worst, np.abs(lhs - rhs).max())
    print(f"  {N} random states, controls and applied forces: max |M qacc + bias - (actuator + passive + "
          f"constraint + applied)| = {worst:.1e} N m")


def energy_and_spectrum() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    model.opt.enableflags |= mujoco.mjtEnableBit.mjENBL_ENERGY
    data = mujoco.MjData(model)
    data.qpos[:] = model.key_qpos[model.key("home").id]
    data.qvel[:] = np.random.default_rng(2).normal(size=model.nv)
    mujoco.mj_forward(model, data)
    m = full_mass(model, data)
    print(f"  1/2 qdot^T M qdot = {0.5 * data.qvel @ m @ data.qvel:.10f} J, MuJoCo energy[1] = {data.energy[1]:.10f} J")
    for arm in (0.05, 0.0):
        model.dof_armature[:] = arm
        mujoco.mj_forward(model, data)
        eig = np.linalg.eigvalsh(full_mass(model, data))
        print(f"  armature {arm:<4}: M symmetric {np.allclose(full_mass(model, data), full_mass(model, data).T)}, "
              f"eigenvalues from {eig[0]:.2e} to {eig[-1]:.3f} kg m^2, condition number {eig[-1] / eig[0]:.0f}")


if __name__ == "__main__":
    print("(1) two-link arm: Lagrangian against MuJoCo")
    two_link()
    print("(2) armature and damping")
    armature_and_damping()
    print("(3) the balance MuJoCo solves, arm7")
    balance()
    print("(4) kinetic energy and the conditioning of M, arm7 at home")
    energy_and_spectrum()
