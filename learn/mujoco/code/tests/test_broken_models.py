"""The debugging clinic's broken models really show their symptom, and the
documented fix really removes it. Each test measures the symptom on the broken
model, applies the fix the clinic describes (as a text edit of the MJCF), and
measures again."""

import mujoco
import numpy as np

from mjcourse import MODELS_DIR


def load(name: str, fix: tuple[str, str] | None = None) -> mujoco.MjModel:
    path = MODELS_DIR / f"broken_{name}.xml"
    if fix is None:
        return mujoco.MjModel.from_xml_path(str(path))
    text = path.read_text()
    assert fix[0] in text, f"fix target {fix[0]!r} not found in {path.name}"
    fixed = MODELS_DIR / f"_fixed_{name}.xml"            # same directory, so relative asset paths resolve
    fixed.write_text(text.replace(*fix))
    try:
        return mujoco.MjModel.from_xml_path(str(fixed))
    finally:
        fixed.unlink()


def run(model, data, seconds, ctrl=None):
    for _ in range(round(seconds / model.opt.timestep)):
        if ctrl is not None:
            ctrl(model, data)
        mujoco.mj_step(model, data)


def test_fall_through():
    for fix, falls in ((None, True), (('contype="2" conaffinity="2"', ""), False)):
        m = load("fall_through", fix)
        d = mujoco.MjData(m)
        run(m, d, 1.5)
        assert (d.qpos[2] < -0.5) == falls


def test_explode():
    m = load("explode")
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 0)
    run(m, d, 1.0)
    assert d.warning[mujoco.mjtWarning.mjWARN_BADQACC].number > 0
    for fix in (('<option timestep="0.01"/>', '<option timestep="0.01" integrator="discrete"/>'),
                ('<option timestep="0.01"/>', '<option timestep="0.0005"/>')):
        m = load("explode", fix)
        d = mujoco.MjData(m)
        mujoco.mj_resetDataKeyframe(m, d, 0)
        run(m, d, 1.0)
        assert d.warning[mujoco.mjtWarning.mjWARN_BADQACC].number == 0
        assert np.all(np.abs(d.qpos) < 1.0)


def test_degrees():
    for fix, max_bend in ((None, 0.1), (("<mujoco model=\"degrees\">", "<mujoco model=\"degrees\">\n  <compiler angle=\"radian\"/>"), None)):
        m = load("degrees", fix)
        d = mujoco.MjData(m)
        run(m, d, 1.0, ctrl=lambda m_, d_: d_.ctrl.__setitem__(0, 2.0))
        elbow = d.joint("elbow").qpos[0]
        if max_bend is not None:
            assert elbow < max_bend
        else:
            assert elbow > 1.0


def _grasp_and_lift(m):
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 0)
    cube = m.body("cube").id
    d.ctrl[:] = [0.12, 0, -0.33, 0.04]
    run(m, d, 1.0)
    d.ctrl[3] = 0.0
    run(m, d, 1.0)
    for k in range(200):                      # raise the carriage 0.3 m over 2 s: slow on purpose
        d.ctrl[2] = -0.33 + 0.3 * (k + 1) / 200
        run(m, d, 0.01)
    run(m, d, 0.5)
    return d.xpos[cube][2]


def test_weak_grip():
    assert _grasp_and_lift(load("weak_grip")) < 0.05
    assert _grasp_and_lift(load("weak_grip", (' priority="2"', ""))) > 0.25


def test_wrong_axis():
    for fix, stays in ((None, True), (('axis="0 0 1"', 'axis="0 1 0"'), False)):
        m = load("wrong_axis", fix)
        d = mujoco.MjData(m)
        run(m, d, 1.0)
        mujoco.mj_forward(m, d)
        tip_z = (d.xpos[2] + d.xmat[2].reshape(3, 3) @ np.array([0.3, 0, 0]))[2]
        assert (abs(tip_z - 1.0) < 1e-3) == stays


def test_upside_down_camera():
    for fix, up_z in ((None, -1.0), (('xyaxes="0 -1 0 0 0 -1"', 'xyaxes="0 1 0 0 0 1"'), 1.0)):
        m = load("upside_down_camera", fix)
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        cam = d.cam_xmat[0].reshape(3, 3)
        np.testing.assert_allclose(cam[:, 1], [0, 0, up_z], atol=1e-9)      # image "up" in world
        np.testing.assert_allclose(cam[:, 2], [1, 0, 0], atol=1e-9)         # looks along -x either way


def test_tunneling():
    """What looks like tunneling is a soft contact too weak for the impact speed."""
    def final_z_and_contact(fix):
        m = load("tunneling", fix)
        d = mujoco.MjData(m)
        mujoco.mj_resetDataKeyframe(m, d, 0)
        touched = False
        for _ in range(round(1.0 / m.opt.timestep)):
            mujoco.mj_step(m, d)
            touched |= d.ncon > 0
        return d.qpos[2], touched

    z, touched = final_z_and_contact(None)
    assert z < 0.4 and touched                        # it passed through, although contact WAS detected
    z, _ = final_z_and_contact(('<option timestep="0.01"/>', '<option timestep="0.001"/>'))
    assert z < 0.4                                    # a smaller timestep alone does not fix it
    fix = ('<option timestep="0.01"/>', '<option timestep="0.001"/>\n  <default><geom solref="0.002 1"/></default>')
    z, _ = final_z_and_contact(fix)
    assert z > 0.49                                   # stiffer contact (allowed by the smaller timestep) holds


def test_sagging_servo():
    for fix, sags in ((None, True), (('<position name="shoulder" joint="shoulder"/>',
                                      '<position name="shoulder" joint="shoulder" kp="500" kv="20"/>'), False)):
        m = load("sagging_servo", fix)
        d = mujoco.MjData(m)
        run(m, d, 3.0)
        q = d.joint("shoulder").qpos[0]
        assert (q < -0.5) == sags
        if not sags:
            assert abs(q) < 0.02


def test_xyzw_quat():
    for fix, x_axis in ((None, None), (('quat="0 0 0.7071068 0.7071068"', 'quat="0.7071068 0 0 0.7071068"'), [0, 1, 0])):
        m = load("xyzw_quat", fix)
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        r = d.xmat[1].reshape(3, 3)
        if x_axis is None:
            assert abs(r[2, 2]) < 0.9        # the box's z axis is no longer vertical: it lies on its side
        else:
            np.testing.assert_allclose(r[:, 0], x_axis, atol=1e-6)


def test_undamped_servo():
    def swing(m):
        d = mujoco.MjData(m)
        d.ctrl[0] = 0.5
        run(m, d, 3.0)
        qs = []
        for _ in range(500):
            mujoco.mj_step(m, d)
            qs.append(d.qpos[0])
        return np.ptp(qs), d.qpos[0]
    amp, _ = swing(load("undamped_servo"))
    assert amp > 0.3
    amp, q = swing(load("undamped_servo", ('kp="200"/>', 'kp="200" kv="11.5"/>')))
    assert amp < 1e-3 and abs(q - 0.5) < 0.01
