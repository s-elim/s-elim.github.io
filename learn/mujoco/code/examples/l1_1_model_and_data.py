"""Lesson 1.1: what lives in mjModel, what lives in mjData, and how to save state.

INPUT   cartpole.xml and cube_table.xml
PROCESS (1) print model sizes and show that mj_step writes data, never model;
        (2) show that derived quantities are stale until mj_forward;
        (3) save state at t = 0.5 s with two state specifications, restore each
            into a fresh MjData, and compare the replay with the original run
OUTPUT  printed checks; the replay comparison shows why the integration state,
        not just qpos and qvel, is needed for bit-exact reproduction

Run:  python examples/l1_1_model_and_data.py
"""

import mujoco
import numpy as np

from mjcourse import model_path


def sizes_and_ownership() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
    data = mujoco.MjData(model)
    print(f"cartpole: nq={model.nq} nv={model.nv} nu={model.nu} nbody={model.nbody} "
          f"timestep={model.opt.timestep} s")
    mass_before = model.body_mass.copy()
    qpos_before = data.qpos.copy()
    data.qpos[1] = 0.2                       # tilt the pole
    for _ in range(100):
        mujoco.mj_step(model, data)
    print("mj_step changed model.body_mass:", not np.array_equal(mass_before, model.body_mass))
    print("mj_step changed data.qpos:      ", not np.array_equal(qpos_before, data.qpos))


def stale_until_forward() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    tip = model.site("pole_tip").id
    before = data.site_xpos[tip].copy()
    data.qpos[0] = 0.5                       # move the cart by hand
    print("tip x after writing qpos, no forward: ", round(data.site_xpos[tip][0], 4), "(stale)")
    mujoco.mj_forward(model, data)
    print("tip x after mj_forward:               ", round(data.site_xpos[tip][0], 4),
          f"(moved {data.site_xpos[tip][0] - before[0]:.4f} m)")


def save_and_replay() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("cube_table")))
    data = mujoco.MjData(model)
    for _ in range(250):                     # 0.5 s: the dropped cube is in contact by now
        mujoco.mj_step(model, data)
    print(f"state saved at t = {data.time:.3f} s with {data.ncon} active contacts")
    specs = {"physics (qpos, qvel, act, history)": mujoco.mjtState.mjSTATE_PHYSICS,
             "integration (all forward-dynamics inputs)": mujoco.mjtState.mjSTATE_INTEGRATION}
    saved = {}
    for name, spec in specs.items():
        buf = np.empty(mujoco.mj_stateSize(model, spec))
        mujoco.mj_getState(model, data, buf, spec)
        saved[name] = (spec, buf)
    reference = []
    for _ in range(500):
        mujoco.mj_step(model, data)
        reference.append(data.qpos.copy())
    for name, (spec, buf) in saved.items():
        replay = mujoco.MjData(model)
        mujoco.mj_setState(model, replay, buf, spec)
        worst = 0.0
        for k in range(500):
            mujoco.mj_step(model, replay)
            worst = max(worst, float(np.max(np.abs(replay.qpos - reference[k]))))
        print(f"replay from {name:<42s} max |qpos difference| over 1 s = {worst:.3e}")


if __name__ == "__main__":
    sizes_and_ownership()
    stale_until_forward()
    save_and_replay()
