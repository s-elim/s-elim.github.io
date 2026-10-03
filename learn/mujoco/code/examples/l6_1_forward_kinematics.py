"""Lesson 6.1: forward kinematics as a chain of transforms, and what mj_kinematics does.

INPUT   arm2.xml (planar two-link arm), arm7.xml (7-DOF arm)
PROCESS (1) the two-link arm's end-effector pose from a product of 4x4 homogeneous
            transforms, against MuJoCo's site_xpos and site_xmat;
        (2) arm7's forward kinematics written from mjModel fields alone (body_pos,
            body_quat, jnt_pos, jnt_axis, site_pos), against MuJoCo;
        (3) which mjData fields mj_kinematics fills, which it leaves alone, and the
            wrong Jacobian you get if you stop there;
        (4) the cost of each stage of the position pipeline
OUTPUT  printed comparisons and timings

Run:  python examples/l6_1_forward_kinematics.py
"""

import os
import time

import mujoco
import numpy as np

from mjcourse import model_path, spatial

N = 200 if os.environ.get("MJC_FAST") == "1" else 1000


def homogeneous(rot: np.ndarray, pos: np.ndarray) -> np.ndarray:
    t = np.eye(4)
    t[:3, :3], t[:3, 3] = rot, pos
    return t


def rot_axis(axis: np.ndarray, angle: float) -> np.ndarray:
    return spatial.quat_to_mat(spatial.axis_angle_to_quat(axis, angle))


def two_link() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm2")))
    data = mujoco.MjData(model)
    minus_y = np.array([0.0, -1.0, 0.0])
    rng = np.random.default_rng(0)
    worst_p = worst_r = 0.0
    for _ in range(N):
        q = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        chain = (homogeneous(np.eye(3), [0, 0, 1.0])                 # world -> shoulder (link1's frame)
                 @ homogeneous(rot_axis(minus_y, q[0]), np.zeros(3))  # shoulder joint
                 @ homogeneous(np.eye(3), [0.5, 0, 0])                # along link 1 to the elbow
                 @ homogeneous(rot_axis(minus_y, q[1]), np.zeros(3))  # elbow joint
                 @ homogeneous(np.eye(3), [0.4, 0, 0]))               # along link 2 to the ee site
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        site = model.site("ee").id
        worst_p = max(worst_p, np.abs(chain[:3, 3] - data.site_xpos[site]).max())
        worst_r = max(worst_r, np.abs(chain[:3, :3] - data.site_xmat[site].reshape(3, 3)).max())
    print(f"  {N} random poses: max |position - site_xpos| = {worst_p:.1e} m, "
          f"max |rotation - site_xmat| = {worst_r:.1e}")


def fk_from_model(model: mujoco.MjModel, qpos: np.ndarray, site: str) -> tuple[np.ndarray, np.ndarray]:
    """Site pose for a tree whose joints are all hinges, from mjModel fields only."""
    xpos = np.zeros((model.nbody, 3))
    xmat = np.zeros((model.nbody, 3, 3))
    xmat[0] = np.eye(3)
    for b in range(1, model.nbody):                               # bodies are stored parents first
        p = model.body_parentid[b]
        pos = xpos[p] + xmat[p] @ model.body_pos[b]               # fixed offset from the parent
        rot = xmat[p] @ spatial.quat_to_mat(model.body_quat[b])
        for j in range(model.body_jntadr[b], model.body_jntadr[b] + model.body_jntnum[b]):
            assert model.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE
            anchor = model.jnt_pos[j]                             # in the body frame
            r_joint = rot_axis(model.jnt_axis[j], qpos[model.jnt_qposadr[j]])
            pos = pos + rot @ (anchor - r_joint @ anchor)         # rotate about the anchor, not the origin
            rot = rot @ r_joint
        xpos[b], xmat[b] = pos, rot
    s = model.site(site).id
    b = model.site_bodyid[s]
    return xpos[b] + xmat[b] @ model.site_pos[s], xmat[b] @ spatial.quat_to_mat(model.site_quat[s])


def seven_dof() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    rng = np.random.default_rng(1)
    worst_p = worst_r = 0.0
    for _ in range(N):
        q = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        pos, rot = fk_from_model(model, q, "ee")
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        worst_p = max(worst_p, np.abs(pos - data.site("ee").xpos).max())
        worst_r = max(worst_r, np.abs(rot - data.site("ee").xmat.reshape(3, 3)).max())
    print(f"  {N} random poses: max |position - site_xpos| = {worst_p:.1e} m, "
          f"max |rotation - site_xmat| = {worst_r:.1e}")


def what_kinematics_fills() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    q = np.array([0.3, 0.6, -0.4, 1.4, 0.2, 0.9, 0.1])
    fields = ["xpos", "xquat", "xmat", "xipos", "ximat", "xanchor", "xaxis", "site_xpos", "site_xmat",
              "geom_xpos", "geom_xmat", "subtree_com", "cdof", "cinert", "qfrc_bias", "sensordata"]
    data = mujoco.MjData(model)
    data.qpos[:] = q
    mujoco.mj_kinematics(model, data)
    filled = [f for f in fields if np.abs(getattr(data, f)).max() > 0]
    empty = [f for f in fields if f not in filled]
    print(f"  fresh MjData, mj_kinematics only:\n    filled: {filled}\n    still zero: {empty}")
    mujoco.mj_comPos(model, data)
    print(f"  after mj_comPos as well: subtree_com, cdof, cinert filled: "
          f"{all(np.abs(getattr(data, f)).max() > 0 for f in ('subtree_com', 'cdof', 'cinert'))}")

    site = model.site("ee").id
    good, stale = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    data = mujoco.MjData(model)
    data.qpos[:] = model.key_qpos[model.key("home").id]
    mujoco.mj_forward(model, data)                                # everything valid for the home pose
    data.qpos[:] = q
    mujoco.mj_kinematics(model, data)                             # new pose: frames updated, cdof is not
    mujoco.mj_jacSite(model, data, stale, None, site)
    mujoco.mj_comPos(model, data)
    mujoco.mj_jacSite(model, data, good, None, site)
    print(f"  Jacobian after mj_kinematics only (cdof from the previous pose) vs after mj_comPos: "
          f"max difference {np.abs(stale - good).max():.3f} m/rad")


def timing() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    data.qpos[:] = model.key_qpos[model.key("home").id]
    stages = {
        "mj_kinematics": lambda: mujoco.mj_kinematics(model, data),
        "mj_kinematics + mj_comPos": lambda: (mujoco.mj_kinematics(model, data), mujoco.mj_comPos(model, data)),
        "mj_fwdPosition": lambda: mujoco.mj_fwdPosition(model, data),
        "mj_forward": lambda: mujoco.mj_forward(model, data),
    }
    n = 5000 if os.environ.get("MJC_FAST") == "1" else 50000
    for name, fn in stages.items():
        fn()
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        print(f"  {name:<27} {1e6 * (time.perf_counter() - t0) / n:6.2f} us per call (arm7, this machine)")


if __name__ == "__main__":
    print("(1) two-link arm: a product of five homogeneous transforms")
    two_link()
    print("(2) arm7: forward kinematics written from mjModel fields")
    seven_dof()
    print("(3) what mj_kinematics computes, and what it does not")
    what_kinematics_fills()
    print("(4) cost of the position pipeline, one call")
    timing()
