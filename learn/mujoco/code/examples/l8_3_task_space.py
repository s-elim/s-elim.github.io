"""Lesson 8.3: task-space control: Jacobian transpose, resolved rates, operational space, impedance.

INPUT   arm7.xml; arm7_table.xml (the arm over a table, flange 24 mm above it at home)
PROCESS (1) track a circle of radius 10 cm at 0.5 Hz with the ee site (vertical plane
            through the home position) using four controllers, with and without a
            null-space posture term, and with the controller's link masses scaled;
            report RMS and peak position error after 2 s and the elbow's height;
        (2) Cartesian impedance pressing the flange 2 cm "into" the table: the contact
            force against K times the commanded penetration, for position-only and
            full 6-D impedance and four stiffnesses
OUTPUT  printed tables

Run:  python examples/l8_3_task_space.py
"""

import mujoco
import numpy as np

from mjcourse import control, model_path, spatial

RADIUS, FREQ, DURATION, SKIP = 0.10, 0.5, 6.0, 2.0
WN = 30.0                       # task-space bandwidth for OSC (rad/s)
K_NULL = 20.0                   # posture stiffness in the null space (N m/rad)


def controller_model(scale: float):
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    model.body_mass[1:] *= scale
    model.body_inertia[1:] *= scale
    data = mujoco.MjData(model)
    mujoco.mj_setConst(model, data)
    return model, data


def circle(center: np.ndarray, t: float):
    w = 2 * np.pi * FREQ
    c, s = np.cos(w * t), np.sin(w * t)
    return (center + RADIUS * np.array([0.0, c, s]), RADIUS * w * np.array([0.0, -s, c]),
            -RADIUS * w * w * np.array([0.0, c, s]))


def track(kind: str, null: bool = True, scale: float = 1.0) -> tuple[float, float, float, float]:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    home = model.key_qpos[model.key("home").id].copy()
    data.qpos[:] = home
    mujoco.mj_forward(model, data)
    sid, elbow = model.site("ee").id, model.body("link4").id
    center = data.site_xpos[sid] - [0.0, RADIUS, 0.0]          # the circle passes through the home position
    dyn = controller_model(scale)
    m_home = np.diag(_mass(*controller_model(1.0), home))
    kpj, kdj = m_home * 20.0**2, 2 * m_home * 20.0             # joint gains for the resolved-rate inner loop
    q_ref, kin = home.copy(), mujoco.MjData(model)                # reference posture and its kinematics
    errors, heights, h = [], [], model.opt.timestep
    for k in range(round(DURATION / h)):
        t = k * h
        mujoco.mj_forward(model, data)                         # kinematics for the current state
        x_d, v_d, a_d = circle(center, t)
        if kind == "operational space":
            tau = control.operational_space(model, data, "ee", x_d, v_d, WN**2, 2 * WN, xdd_des=a_d,
                                            q_rest=home if null else None, k_null=K_NULL if null else 0.0, dyn=dyn)
        else:
            cm, cd = dyn
            cd.qpos[:], cd.qvel[:] = data.qpos, data.qvel
            mujoco.mj_forward(cm, cd)
            jac = np.zeros((3, model.nv))
            mujoco.mj_jacSite(model, data, jac, None, sid)
            e, edot = x_d - data.site_xpos[sid], v_d - jac @ data.qvel
            if kind == "Jacobian transpose":                   # F = Kp e + Kd edot with constant gains
                tau = jac.T @ (400.0 * e + 40.0 * edot) + cd.qfrc_bias + model.dof_damping * data.qvel
            else:                                              # resolved rate: differential IK, then joint PD
                pinv = jac.T @ np.linalg.inv(jac @ jac.T + 1e-4 * np.eye(3))
                kin.qpos[:] = q_ref
                mujoco.mj_kinematics(model, kin)
                qd_ref = pinv @ (v_d + 20.0 * (x_d - kin.site_xpos[sid]))
                if null:
                    qd_ref += (np.eye(model.nv) - pinv @ jac) @ (2.0 * (home - q_ref))
                q_ref = q_ref + h * qd_ref
                tau = kpj * (q_ref - data.qpos) + kdj * (qd_ref - data.qvel) + cd.qfrc_bias + model.dof_damping * data.qvel
            tau = control.clip_to_ctrlrange(model, tau)
        data.ctrl[:] = tau
        mujoco.mj_step(model, data)
        heights.append(data.xpos[elbow][2])
        if t >= SKIP:
            mujoco.mj_kinematics(model, data)
            errors.append(np.linalg.norm(circle(center, t + h)[0] - data.site_xpos[sid]))
    err = np.array(errors)
    return 1000 * float(np.sqrt(np.mean(err**2))), 1000 * float(err.max()), min(heights), max(heights)


def _mass(model, data, qpos):
    data.qpos[:] = qpos
    mujoco.mj_forward(model, data)
    m = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, m)
    return m


def press(stiffness: float, rotation: bool, depth: float = 0.02, seconds: float = 4.0):
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7_table")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    home, sid = data.qpos.copy(), model.site("flange").id
    top = model.geom("table").pos[2] + model.geom("table").size[2]
    target = data.site_xpos[sid].copy()
    target[2] = top - depth                                    # 2 cm below the table surface
    q_target = spatial.mat_to_quat(data.site_xmat[sid].reshape(3, 3))
    damping, k_rot = 2 * np.sqrt(stiffness * 2.0), 30.0        # translational damping for an effective 2 kg
    d_rot = 2 * np.sqrt(k_rot * 0.05)
    for _ in range(round(seconds / model.opt.timestep)):
        mujoco.mj_forward(model, data)
        jp, jr = np.zeros((3, model.nv)), np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, jp, jr, sid)
        wrench = stiffness * (target - data.site_xpos[sid]) - damping * (jp @ data.qvel)
        jac = jp
        if rotation:
            cur = spatial.mat_to_quat(data.site_xmat[sid].reshape(3, 3))
            e_rot = spatial.quat_to_rotvec(spatial.quat_mul(q_target, spatial.quat_conj(cur)))
            wrench = np.r_[wrench, k_rot * e_rot - d_rot * (jr @ data.qvel)]
            jac = np.vstack([jp, jr])
        mass = np.zeros((model.nv, model.nv))
        mujoco.mj_fullM(model, data, mass)
        m_inv = np.linalg.inv(mass)
        lam = np.linalg.inv(jac @ m_inv @ jac.T)
        null = np.eye(model.nv) - jac.T @ (m_inv @ jac.T @ lam).T
        tau = jac.T @ wrench + data.qfrc_bias + model.dof_damping * data.qvel
        tau += null @ (K_NULL * (home - data.qpos) - 2 * np.sqrt(K_NULL) * data.qvel)
        data.ctrl[:] = tau
        mujoco.mj_step(model, data)
    mujoco.mj_forward(model, data)
    table, flange = model.geom("table").id, model.geom("flange").id
    force, n, f = 0.0, 0, np.zeros(6)
    for i in range(data.ncon):
        c = data.contact[i]
        if {c.geom1, c.geom2} == {table, flange}:
            mujoco.mj_contactForce(model, data, i, f)
            force += f[0]
            n += 1
    cur = spatial.mat_to_quat(data.site_xmat[sid].reshape(3, 3))
    tilt = np.degrees(np.linalg.norm(spatial.quat_to_rotvec(spatial.quat_mul(q_target, spatial.quat_conj(cur)))))
    commanded = stiffness * (data.site_xpos[sid][2] - target[2])
    return force, commanded, 1000 * (top - data.site_xpos[sid][2]), n, tilt


if __name__ == "__main__":
    print(f"(1) circle of radius {100 * RADIUS:.0f} cm at {FREQ} Hz in the y-z plane through home; errors after {SKIP} s")
    print(f"  {'controller':<22}{'posture term':>13}{'model scale':>12}{'RMS (mm)':>10}{'peak (mm)':>11}{'elbow height (m)':>19}")
    cases = [("Jacobian transpose", False, 1.0), ("resolved rate", True, 1.0), ("operational space", True, 1.0),
             ("operational space", False, 1.0), ("operational space", True, 0.5), ("operational space", True, 1.5)]
    for kind, null, scale in cases:
        rms, peak, lo, hi = track(kind, null, scale)
        print(f"  {kind:<22}{('on' if null else 'off'):>13}{scale:>12g}{rms:>10.3f}{peak:>11.3f}{lo:>11.3f} to {hi:.3f}")
    print("(2) impedance: flange commanded 20 mm below the table surface, held 4 s")
    print(f"  {'stiffness':>10}{'controller':>14}{'contact force':>15}{'K x (z - z*)':>14}{'into table':>12}{'contacts':>10}{'tilt':>10}")
    for k, rot in ((200, False), (200, True), (500, True), (1000, True), (3000, True)):
        force, commanded, depth, n, tilt = press(k, rot)
        print(f"  {k:>6} N/m{('6-D' if rot else 'position'):>14}{force:>13.3f} N{commanded:>12.3f} N{depth:>9.3f} mm{n:>10}{tilt:>8.3f} deg")
