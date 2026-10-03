"""Lesson 4.2: the inertia tensor, principal axes, and the intermediate-axis flip.

INPUT   an L-shaped body built from two boxes (written below); tumbling_box.xml
PROCESS (1) compute the L's centre of mass and inertia tensor by hand with the
            parallel-axis theorem, diagonalize it, compare with MuJoCo's
            body_ipos, body_inertia and body_iquat;
        (2) spin the tumbling box about each principal axis and count flips;
        (3) compare how four integrators conserve energy and angular momentum
OUTPUT  printed comparisons

Run:  python examples/l4_2_inertia.py
"""

import mujoco
import numpy as np

from mjcourse import model_path, spatial

L_SHAPE = """
<mujoco><option gravity="0 0 0"/><worldbody><body name="L"><freejoint/>
  <geom type="box" size="0.10 0.02 0.02" pos="0.10 0 0" mass="2"/>
  <geom type="box" size="0.02 0.06 0.02" pos="0.02 0.08 0" mass="1"/>
</body></worldbody></mujoco>
"""


def box_inertia(m: float, half: np.ndarray) -> np.ndarray:
    a, b, c = half
    return m / 3 * np.diag([b * b + c * c, a * a + c * c, a * a + b * b])


def l_shape() -> None:
    parts = [(2.0, np.array([0.10, 0, 0]), np.array([0.10, 0.02, 0.02])),
             (1.0, np.array([0.02, 0.08, 0]), np.array([0.02, 0.06, 0.02]))]
    mass = sum(m for m, _, _ in parts)
    com = sum(m * c for m, c, _ in parts) / mass
    inertia = np.zeros((3, 3))
    for m, c, half in parts:
        d = c - com
        inertia += box_inertia(m, half) + m * (d @ d * np.eye(3) - np.outer(d, d))   # parallel-axis theorem
    moments, axes = np.linalg.eigh(inertia)                                          # principal moments, ascending

    model = mujoco.MjModel.from_xml_string(L_SHAPE)
    b = model.body("L")
    mj_axes = spatial.quat_to_mat(b.iquat)                                            # columns: principal axes
    print(f"  centre of mass: by hand {np.round(com, 6)}, MuJoCo body_ipos {np.round(b.ipos, 6)}")
    print(f"  principal moments: by hand {np.round(moments, 8)}, MuJoCo body_inertia {np.round(b.inertia, 8)}")
    for k in range(3):                       # match MuJoCo's moment ordering, compare axes up to sign
        j = int(np.argmin(np.abs(moments - b.inertia[k])))
        print(f"    axis for {b.inertia[k]:.6f}: |cos| between hand and MuJoCo = {abs(axes[:, j] @ mj_axes[:, k]):.9f}")


def flips(key: str, seconds: float = 20.0) -> int:
    model = mujoco.MjModel.from_xml_path(str(model_path("tumbling_box")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key(key).id)
    mujoco.mj_forward(model, data)
    axis = 1 if key == "intermediate" else 2
    mujoco.mj_subtreeVel(model, data)
    momentum = data.subtree_angmom[1].copy()
    sign, count = np.sign(data.xmat[1].reshape(3, 3)[:, axis] @ momentum), 0
    for _ in range(round(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)
        s = np.sign(data.xmat[1].reshape(3, 3)[:, axis] @ momentum)
        count += int(s != sign)
        sign = s
    return count


def conservation() -> None:
    for code, name in ((1, "RK4"), (0, "Euler"), (3, "implicitfast"), (2, "implicit")):
        model = mujoco.MjModel.from_xml_path(str(model_path("tumbling_box")))
        model.opt.integrator = code
        model.opt.enableflags |= mujoco.mjtEnableBit.mjENBL_ENERGY
        data = mujoco.MjData(model)
        mujoco.mj_resetDataKeyframe(model, data, 0)
        mujoco.mj_forward(model, data)
        mujoco.mj_subtreeVel(model, data)
        l0, e0 = data.subtree_angmom[1].copy(), data.energy[1]
        for _ in range(round(20.0 / model.opt.timestep)):
            mujoco.mj_step(model, data)
        mujoco.mj_subtreeVel(model, data)
        print(f"  {name:<13s} kinetic energy {100 * (data.energy[1] - e0) / e0:+7.3f} %   "
              f"|angular momentum change| {np.linalg.norm(data.subtree_angmom[1] - l0):.1e} kg m^2/s")


if __name__ == "__main__":
    print("an L-shaped body from two boxes:")
    l_shape()
    print("tumbling box, 20 s at 6 rad/s, axis flips:")
    print(f"  about the largest-moment axis (z): {flips('major')} flips")
    print(f"  about the intermediate axis (y):   {flips('intermediate')} flips")
    print("conservation over 20 s of tumbling, by integrator:")
    conservation()
