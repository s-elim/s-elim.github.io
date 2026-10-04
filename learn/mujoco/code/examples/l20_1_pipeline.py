"""Lesson 20.1: inside mj_step, stage by stage (Level 20).

INPUT   pick_place.xml (arm, gripper with a tendon and an equality, cube, sensors) simulated for 0.5 s from
        its keyframe so that contacts are active; MuJoCo 3.14.0, whose mj_step is in src/engine/engine_forward.c
PROCESS (1) every float array of mjData that is not an input is filled with NaN; the public stage functions
            then run one at a time in the order mj_forward calls them, and each stage's newly written fields are
            listed; the resulting qacc is compared with mj_forward's;
        (2) the fields no stage wrote, and why;
        (3) after mj_step: how far the positions and sensors stored in mjData are from the new state;
        (4) mj_forwardSkip: after a change of velocity only, the position stage can be skipped; equality with
            mj_forward and the time saved
OUTPUT  printed tables

Run:  python examples/l20_1_pipeline.py
"""

import time

import mujoco
import numpy as np

from mjcourse import model_path

INPUTS = {"qpos", "qvel", "act", "ctrl", "qfrc_applied", "xfrc_applied", "mocap_pos", "mocap_quat", "userdata",
          "qacc_warmstart", "plugin_state", "history", "eq_active"}
STAGES = [("mj_fwdPosition", mujoco.mj_fwdPosition), ("mj_sensorPos", mujoco.mj_sensorPos),
          ("mj_fwdVelocity", mujoco.mj_fwdVelocity), ("mj_sensorVel", mujoco.mj_sensorVel),
          ("mj_fwdActuation", mujoco.mj_fwdActuation), ("mj_fwdAcceleration", mujoco.mj_fwdAcceleration),
          ("mj_fwdConstraint", mujoco.mj_fwdConstraint), ("mj_sensorAcc", mujoco.mj_sensorAcc)]


def float_fields(data: mujoco.MjData) -> dict[str, np.ndarray]:
    """Every non-empty float64 array of mjData that is not an input (fresh views: the arena moves)."""
    out = {}
    for name in dir(data):
        if name.startswith("_") or name in INPUTS:
            continue
        try:
            value = getattr(data, name)
        except Exception:
            continue
        if isinstance(value, np.ndarray) and value.dtype == np.float64 and value.size:
            out[name] = value
    return out


def scene() -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(model_path("pick_place")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    while data.time < 0.5:
        mujoco.mj_step(model, data)
    return model, data


if __name__ == "__main__":
    model, data = scene()
    mujoco.mj_forward(model, data)
    reference_qacc = data.qacc.copy()
    print(f"MuJoCo {mujoco.__version__}; pick_place after 0.5 s: nv {model.nv}, ncon {data.ncon}, nefc {data.nefc}, "
          f"solver {mujoco.mjtSolver(model.opt.solver).name}, integrator {mujoco.mjtIntegrator(model.opt.integrator).name}")
    print("(1) fields each stage writes (filled with NaN beforehand)")
    for name, value in float_fields(data).items():
        value[...] = np.nan
    written = set()
    for stage, fn in STAGES:
        fn(model, data)
        now = {name for name, value in float_fields(data).items() if np.isfinite(value).all()}
        new = sorted(now - written)
        written |= now
        partial = [f"{n} ({int(np.isfinite(v).sum())} of {v.size})" for n, v in float_fields(data).items()
                   if n not in now and np.isfinite(v).any()]
        print(f"    {stage:<19} {', '.join(new) if new else '(nothing complete)'}"
              + (f"; partly: {', '.join(partial)}" if partial else ""))
    print(f"    qacc from the stages against mj_forward: max difference {np.abs(data.qacc - reference_qacc).max():.1e}")
    print("(2) fields no stage wrote")
    untouched = sorted(name for name, value in float_fields(data).items() if not np.isfinite(value).all())
    print("    " + ", ".join(untouched))
    print("(3) after one mj_step, with the arm's joints moving at 1 rad/s")
    model, data = scene()
    data.qvel[:7] = 1.0
    mujoco.mj_forward(model, data)
    before_xpos, before_sensor = data.xpos.copy(), data.sensordata.copy()
    mujoco.mj_step(model, data)
    fresh = mujoco.MjData(model)
    fresh.qpos[:], fresh.qvel[:], fresh.act[:], fresh.ctrl[:] = data.qpos, data.qvel, data.act, data.ctrl
    mujoco.mj_forward(model, fresh)
    print(f"    body positions in mjData against those of the new qpos: max difference "
          f"{1000 * np.abs(data.xpos - fresh.xpos).max():.3f} mm; against those before the step: "
          f"{1000 * np.abs(data.xpos - before_xpos).max():.3f} mm")
    print(f"    sensordata in mjData against the new state's: max difference {np.abs(data.sensordata - fresh.sensordata).max():.2e}; "
          f"against the state before the step: {np.abs(data.sensordata - before_sensor).max():.2e}")
    print("(4) mj_forwardSkip after a change of qvel only")
    model, data = scene()
    mujoco.mj_forward(model, data)
    work = mujoco.MjData(model)
    work.qpos[:], work.qvel[:], work.act[:], work.ctrl[:] = data.qpos, data.qvel, data.act, data.ctrl
    mujoco.mj_forward(model, work)
    rng = np.random.default_rng(0)
    errors, t_full, t_skip, n = [], 0.0, 0.0, 2000
    for _ in range(n):
        dv = rng.normal(0.0, 0.01, model.nv)
        work.qvel[:] = data.qvel + dv
        t0 = time.perf_counter()
        mujoco.mj_forwardSkip(model, work, mujoco.mjtStage.mjSTAGE_POS, 0)
        t_skip += time.perf_counter() - t0
        skipped = work.qacc.copy()
        t0 = time.perf_counter()
        mujoco.mj_forward(model, work)
        t_full += time.perf_counter() - t0
        errors.append(np.abs(work.qacc - skipped).max())
    print(f"    {n} random velocity perturbations: max |qacc(skip) - qacc(full)| {max(errors):.1e}; "
          f"mj_forward {1e6 * t_full / n:.1f} us, mj_forwardSkip(mjSTAGE_POS) {1e6 * t_skip / n:.1f} us")
