"""Lesson 6.2: Jacobians, velocity kinematics and singularities.

INPUT   arm2.xml (planar two-link arm), arm7.xml (7-DOF arm)
PROCESS (1) the two-link Jacobian derived by hand, from mj_jacSite and from central
            finite differences, over random poses;
        (2) singular values, manipulability and the joint speed needed for a
            0.1 m/s tip motion as the elbow straightens;
        (3) the point each mj_jac* function refers to, the rule that moves a
            Jacobian from one point of a body to another, and world versus local frames;
        (4) mj_jacDot against a finite difference of J along the motion
OUTPUT  printed tables

Run:  python examples/l6_2_jacobians.py
"""

import os

import mujoco
import numpy as np

from mjcourse import kinematics, model_path, spatial

N = 200 if os.environ.get("MJC_FAST") == "1" else 1000
L1, L2 = 0.5, 0.4


def planar_jacobian(q: np.ndarray) -> np.ndarray:
    """d(x, z)/d(q1, q2) for the two-link arm."""
    s1, c1 = np.sin(q[0]), np.cos(q[0])
    s12, c12 = np.sin(q[0] + q[1]), np.cos(q[0] + q[1])
    return np.array([[-L1 * s1 - L2 * s12, -L2 * s12],
                     [L1 * c1 + L2 * c12, L2 * c12]])


def three_ways() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm2")))
    data = mujoco.MjData(model)
    rng = np.random.default_rng(0)
    e_mj = e_fd = 0.0
    for _ in range(N):
        q = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        mujoco.mj_comPos(model, data)
        jacp, _ = kinematics.site_jacobian(model, data, "ee")
        fdp, _ = kinematics.fd_site_jacobian(model, data, "ee")
        hand = planar_jacobian(q)
        e_mj = max(e_mj, np.abs(jacp[[0, 2]] - hand).max())
        e_fd = max(e_fd, np.abs(fdp[[0, 2]] - hand).max())
    print(f"  {N} random poses: max |mj_jacSite - hand| = {e_mj:.1e}, "
          f"max |finite difference (eps 1e-6) - hand| = {e_fd:.1e} m/rad")


def singular_values() -> None:
    print(f"  {'q2 (rad)':>9}{'sigma1':>9}{'sigma2':>10}{'w = s1 s2':>11}{'L1 L2 |sin q2|':>16}{'cond':>9}{'|qdot| for 0.1 m/s':>21}")
    for q2 in (-1.5, -0.5, -0.1, -0.01, 0.0):
        jac = planar_jacobian(np.array([0.4, q2]))
        u, s, _ = np.linalg.svd(jac)
        speed = np.inf if s[1] < 1e-12 else 0.1 / s[1]          # along the weakest direction u[:, 1]
        cond = np.inf if s[1] < 1e-12 else s[0] / s[1]
        print(f"  {q2:>9.2f}{s[0]:>9.4f}{s[1]:>10.5f}{s[0] * s[1]:>11.5f}{L1 * L2 * abs(np.sin(q2)):>16.5f}"
              f"{cond:>9.1f}{speed:>16.2f} rad/s")


def reference_points() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    data.qpos[:] = [0.3, 0.6, -0.4, 1.4, 0.2, 0.9, 0.1]
    data.qvel[:] = np.random.default_rng(2).normal(size=model.nv)
    mujoco.mj_forward(model, data)
    nv, body = model.nv, model.body("link7").id
    site, geom = model.site("ee").id, model.geom("flange").id

    def jac_at(point):
        p, r = np.zeros((3, nv)), np.zeros((3, nv))
        mujoco.mj_jac(model, data, p, r, point, body)
        return p, r

    cases = {
        "mj_jacBody      -> xpos (body frame origin)": (mujoco.mj_jacBody, body, data.xpos[body]),
        "mj_jacBodyCom   -> xipos (body centre of mass)": (mujoco.mj_jacBodyCom, body, data.xipos[body]),
        "mj_jacSite      -> site_xpos": (mujoco.mj_jacSite, site, data.site_xpos[site]),
        "mj_jacGeom      -> geom_xpos": (mujoco.mj_jacGeom, geom, data.geom_xpos[geom]),
    }
    for name, (fn, idx, point) in cases.items():
        p, r = np.zeros((3, nv)), np.zeros((3, nv))
        fn(model, data, p, r, idx)
        ref_p, ref_r = jac_at(point)
        print(f"  {name:<46} equals mj_jac at that point: {np.abs(p - ref_p).max():.0e}, rotation part {np.abs(r - ref_r).max():.0e}")

    a, b = data.xpos[body], data.site_xpos[site]
    pa, ra = jac_at(a)
    pb, _ = jac_at(b)
    shifted = pa - spatial.hat(b - a) @ ra                     # v_b = v_a + w x (b - a)
    print(f"  shift rule J_p(b) = J_p(a) - [b - a]x J_r, link7 origin -> ee site: max error {np.abs(shifted - pb).max():.0e}")

    sub = np.zeros((3, nv))
    mujoco.mj_jacSubtreeCom(model, data, sub, model.body("link4").id)
    mujoco.mj_subtreeVel(model, data)
    print(f"  mj_jacSubtreeCom(link4) @ qvel = {np.round(sub @ data.qvel, 5)}, subtree_linvel after mj_subtreeVel = "
          f"{np.round(data.subtree_linvel[model.body('link4').id], 5)} m/s")

    _, r = np.zeros((3, nv)), np.zeros((3, nv))
    mujoco.mj_jacSite(model, data, None, r, site)
    w_world = r @ data.qvel
    vel = np.zeros(6)
    mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_SITE, site, vel, 0)
    vel_local = np.zeros(6)
    mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_SITE, site, vel_local, 1)
    rot = data.site_xmat[site].reshape(3, 3)
    print(f"  angular velocity: J_r qvel (world) vs mj_objectVelocity world: {np.abs(w_world - vel[:3]).max():.0e}; "
          f"R^T J_r qvel vs local: {np.abs(rot.T @ w_world - vel_local[:3]).max():.0e} rad/s")


def jac_dot() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    data.qpos[:] = [0.3, 0.6, -0.4, 1.4, 0.2, 0.9, 0.1]
    data.qvel[:] = np.random.default_rng(3).normal(size=model.nv)
    mujoco.mj_forward(model, data)
    site, nv = model.site("ee").id, model.nv
    dp, dr = np.zeros((3, nv)), np.zeros((3, nv))
    mujoco.mj_jacDot(model, data, dp, dr, data.site_xpos[site], model.site_bodyid[site])

    def site_jac(qpos):
        d = mujoco.MjData(model)
        d.qpos[:] = qpos
        mujoco.mj_kinematics(model, d)
        mujoco.mj_comPos(model, d)
        return kinematics.site_jacobian(model, d, site)

    h = 1e-6
    q_plus, q_minus = data.qpos.copy(), data.qpos.copy()
    mujoco.mj_integratePos(model, q_plus, data.qvel, h)
    mujoco.mj_integratePos(model, q_minus, data.qvel, -h)
    (pp, rp), (pm, rm) = site_jac(q_plus), site_jac(q_minus)
    print(f"  max |mj_jacDot - (J(q + h qdot) - J(q - h qdot)) / 2h|: translation {np.abs(dp - (pp - pm) / (2 * h)).max():.1e}, "
          f"rotation {np.abs(dr - (rp - rm) / (2 * h)).max():.1e}")
    print(f"  the velocity-product term Jdot qdot at the ee site: {np.round(dp @ data.qvel, 4)} m/s^2")


if __name__ == "__main__":
    print("(1) the two-link Jacobian three ways")
    three_ways()
    print("(2) singular values as the elbow straightens (q1 = 0.4 rad)")
    singular_values()
    print("(3) reference points and frames of MuJoCo's Jacobians (arm7, link7)")
    reference_points()
    print("(4) the time derivative of the Jacobian")
    jac_dot()
