"""Project 7 scene: the randomized initial states and the success test. Shared by the tests, the
starter and the solution; do not edit it (the evaluation protocol is not yours to tune).

Randomization, all uniform and independent:
    cube centre x, y   in [-0.2, 0.2] m          (the gantry reaches +-0.4 m)
    cube yaw           in [-pi/4, pi/4] rad      (a cube repeats every pi/2)
    cube mass          in [0.05, 0.5] kg         (inertia scaled with it: a uniform cube)
    cube friction      in [0.4, 1.2]             (sliding coefficient)

The pads have geom priority 1, so a contact between a pad and a cube of equal or lower priority
uses the pad's friction (1.5) whatever the cube's is. To make the cube's sampled friction govern
its contacts, the randomizer gives the cube priority 2.

Success: during the whole final second of the 5 s episode the cube centre is at least 0.10 m
above its starting height, and at the end it moves slower than 0.02 m/s and touches both pads.
"""

import mujoco
import numpy as np

from mjcourse import model_path

EPISODE_SECONDS = 5.0
LIFT_REQUIRED = 0.10      # m
HOLD_SECONDS = 1.0
MAX_SPEED = 0.02          # m/s


def make_model() -> mujoco.MjModel:
    return mujoco.MjModel.from_xml_path(str(model_path("gantry_gripper")))


def sample_states(seed: int, n: int) -> np.ndarray:
    """(n, 5) array of [x, y, yaw, mass, friction]."""
    rng = np.random.default_rng(seed)
    return np.column_stack([rng.uniform(-0.2, 0.2, n), rng.uniform(-0.2, 0.2, n),
                            rng.uniform(-np.pi / 4, np.pi / 4, n), rng.uniform(0.05, 0.5, n),
                            rng.uniform(0.4, 1.2, n)])


def reset(model: mujoco.MjModel, state: np.ndarray) -> mujoco.MjData:
    x, y, yaw, mass, friction = state
    cube, geom = model.body("cube").id, model.geom("cube").id
    nominal = make_model()
    model.body_mass[cube] = mass
    model.body_inertia[cube] = nominal.body_inertia[cube] * mass / nominal.body_mass[cube]
    model.geom_friction[geom, 0] = friction
    model.geom_priority[geom] = 2
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("open_above").id)
    mujoco.mj_setConst(model, data)
    data.qpos[0:2] = 0.0                                   # gripper parked above the origin
    data.ctrl[0:2] = 0.0
    adr = model.jnt_qposadr[model.joint("cube").id]
    data.qpos[adr:adr + 3] = [x, y, 0.02]
    data.qpos[adr + 3:adr + 7] = [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
    mujoco.mj_forward(model, data)
    return data


def run_episode(model: mujoco.MjModel, state: np.ndarray, make_controller) -> dict:
    """Run one episode; the controller is called every 10 ms and returns the 4 control values."""
    data = reset(model, state)
    controller = make_controller(model, data)
    cube = model.body("cube").id
    z0 = data.xpos[cube][2]
    h = model.opt.timestep
    every = round(0.01 / h)
    lowest_in_hold = np.inf
    for k in range(round(EPISODE_SECONDS / h)):
        if k % every == 0:
            data.ctrl[:] = controller(k * h, data)
        mujoco.mj_step(model, data)
        if (k + 1) * h > EPISODE_SECONDS - HOLD_SECONDS:
            mujoco.mj_kinematics(model, data)
            lowest_in_hold = min(lowest_in_hold, data.xpos[cube][2] - z0)
    mujoco.mj_forward(model, data)
    velocity = np.zeros(6)
    mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_BODY, cube, velocity, 0)
    pads = {model.geom("gripper/pad_left").id, model.geom("gripper/pad_right").id}
    cube_geom = model.geom("cube").id
    touching = {c.geom1 if c.geom2 == cube_geom else c.geom2 for c in data.contact[:data.ncon]
                if cube_geom in (c.geom1, c.geom2)}
    held = pads <= touching
    speed = float(np.linalg.norm(velocity[3:]))
    return {"success": bool(lowest_in_hold >= LIFT_REQUIRED and speed < MAX_SPEED and held),
            "lift": float(lowest_in_hold), "speed": speed, "held": bool(held)}
