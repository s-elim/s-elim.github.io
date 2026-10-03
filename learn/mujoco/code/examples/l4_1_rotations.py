"""Lesson 4.1: rotations and transforms, checked against MuJoCo.

INPUT   mjcourse.spatial (the lesson's formulas in NumPy) and tutorial_tree.xml
PROCESS (1) the same three Euler angles read intrinsically and extrinsically;
        (2) rotating a vector with a matrix and with a quaternion sandwich;
        (3) the double cover and what it does to a naive loss;
        (4) why arccos is a poor way to measure small rotation errors;
        (5) a site's world pose composed by hand from its parent body's pose
OUTPUT  printed comparisons

Run:  python examples/l4_1_rotations.py
"""

import mujoco
import numpy as np

from mjcourse import model_path, spatial


def intrinsic_vs_extrinsic() -> None:
    e = np.radians([90.0, 90.0, 0.0])
    for seq in ("xyz", "XYZ"):
        r = spatial.quat_to_mat(spatial.euler_to_quat(e, seq))
        print(f"  seq {seq}: body x axis in world = {np.round(r[:, 0], 3)}, z axis = {np.round(r[:, 2], 3)}")


def sandwich() -> None:
    q = spatial.euler_to_quat(np.radians([20.0, -35.0, 60.0]), "xyz")
    v = np.array([0.3, -0.1, 0.8])
    by_matrix = spatial.quat_to_mat(q) @ v
    by_quat = spatial.quat_mul(spatial.quat_mul(q, np.r_[0.0, v]), spatial.quat_conj(q))[1:]
    ref = np.zeros(3)
    mujoco.mju_rotVecQuat(ref, v, q)
    print(f"  R v = {np.round(by_matrix, 6)}; q v q* = {np.round(by_quat, 6)}; mju_rotVecQuat = {np.round(ref, 6)}")


def double_cover() -> None:
    q = spatial.euler_to_quat(np.radians([10.0, 20.0, 30.0]), "xyz")
    print(f"  q and -q: same matrix = {np.allclose(spatial.quat_to_mat(q), spatial.quat_to_mat(-q))}; "
          f"||q - (-q)|| = {np.linalg.norm(q - (-q)):.3f}; geodesic angle = {spatial.geodesic_angle(q, -q):.2e} rad")


def small_angle_precision() -> None:
    q1 = spatial.euler_to_quat(np.radians([10.0, 20.0, 30.0]), "xyz")
    for true_angle in (1e-3, 1e-6, 1e-9):
        q2 = spatial.quat_mul(q1, spatial.axis_angle_to_quat([1.0, 2.0, 3.0], true_angle))
        naive = 2.0 * np.arccos(min(1.0, abs(float(np.dot(q1, q2)))))
        print(f"  true {true_angle:.0e} rad: arccos formula {naive:.3e}, atan2 formula {spatial.geodesic_angle(q1, q2):.3e}")


def compose_site_pose() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("tutorial_tree")))
    data = mujoco.MjData(model)
    data.qpos[:] = [0.5, -0.8]
    mujoco.mj_forward(model, data)
    site = model.site("tip")
    parent = site.bodyid[0]
    t_world_body = spatial.transform(data.xmat[parent].reshape(3, 3), data.xpos[parent])
    t_body_site = spatial.transform(spatial.quat_to_mat(model.site_quat[site.id]), model.site_pos[site.id])
    t_world_site = t_world_body @ t_body_site
    print(f"  by hand: {np.round(t_world_site[:3, 3], 6)}; MuJoCo site_xpos: {np.round(data.site_xpos[site.id], 6)}")
    print(f"  max matrix difference: {np.max(np.abs(t_world_site[:3, :3] - data.site_xmat[site.id].reshape(3, 3))):.1e}")


if __name__ == "__main__":
    print("one set of angles (90, 90, 0) deg, two conventions:")
    intrinsic_vs_extrinsic()
    print("rotating a vector:")
    sandwich()
    print("double cover:")
    double_cover()
    print("measuring small rotations:")
    small_angle_precision()
    print("composing transforms:")
    compose_site_pose()
