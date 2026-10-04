"""Project 8 scene: the randomized initial states and the independent judge. Shared by the tests,
the starter and the solution; do not edit it.

Each episode places the three cubes (red, green, blue) at random, uniformly and independently:
    centre x in [0.35, 0.60] m, y in [-0.25, 0.05] m, at least 0.09 m apart (redrawn until they are)
    yaw in [-pi/4, pi/4] rad
The tray (inner floor 0.14 x 0.14 m, centre at the `tray_center` site) is fixed.

Judgement, after your routine returns: the scene holds the arm where it is (PD with gravity
compensation on the current joint angles) with the gripper command unchanged, for 1 s, then calls
a cube placed when its centre is within 0.05 m of the tray centre in x and y and lower than
0.06 m (so it rests on the tray floor, not on a wall or another cube).

Rules for routines: write only data.ctrl and advance time only with mujoco.mj_step; finish within
EPISODE_LIMIT simulated seconds.
"""

import importlib.util
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

import mujoco
import numpy as np

from mjcourse import model_path

CUBES = ("red_cube", "green_cube", "blue_cube")
GRASP_STAGE = ("IK failed", "grasp missed", "dropped while lifting", "knocked over")
CATEGORIES = ("success", "IK failed", "grasp missed", "dropped while lifting", "dropped while carrying",
              "missed the tray", "knocked over")
EPISODE_LIMIT = 40.0       # s of simulated time
HOLD = 1.0                 # s
INSIDE, BELOW = 0.05, 0.06  # m


def make_model() -> mujoco.MjModel:
    return mujoco.MjModel.from_xml_path(str(model_path("pick_place")))


def sample_states(seed: int, n: int) -> np.ndarray:
    """(n, 3, 3) array: for each episode and cube, [x, y, yaw]."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, 3, 3))
    for i in range(n):
        while True:
            xy = np.column_stack([rng.uniform(0.35, 0.60, 3), rng.uniform(-0.25, 0.05, 3)])
            gaps = [np.linalg.norm(xy[a] - xy[b]) for a, b in ((0, 1), (0, 2), (1, 2))]
            if min(gaps) >= 0.09:
                break
        out[i, :, :2] = xy
        out[i, :, 2] = rng.uniform(-np.pi / 4, np.pi / 4, 3)
    return out


def reset(model: mujoco.MjModel, state: np.ndarray) -> mujoco.MjData:
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    for name, (x, y, yaw) in zip(CUBES, state):
        adr = model.jnt_qposadr[model.joint(name).id]
        data.qpos[adr:adr + 7] = [x, y, 0.02, np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
    mujoco.mj_forward(model, data)
    return data


def hold(model: mujoco.MjModel, data: mujoco.MjData, seconds: float) -> None:
    """PD with gravity compensation on the arm's current joint angles."""
    mujoco.mj_forward(model, data)
    target = data.qpos[:7].copy()
    mass = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, mass)
    kp, kd = np.diag(mass)[:7] * 400.0, np.diag(mass)[:7] * 40.0
    for _ in range(round(seconds / model.opt.timestep)):
        mujoco.mj_forward(model, data)
        tau = kp * (target - data.qpos[:7]) - kd * data.qvel[:7] + data.qfrc_bias[:7]
        data.ctrl[:7] = np.clip(tau, *model.actuator_ctrlrange[:7].T)
        mujoco.mj_step(model, data)


def judge(model: mujoco.MjModel, data: mujoco.MjData) -> dict[str, bool]:
    mujoco.mj_forward(model, data)
    tray = data.site("tray_center").xpos
    placed = {}
    for name in CUBES:
        p = data.body(name).xpos
        placed[name] = bool(abs(p[0] - tray[0]) < INSIDE and abs(p[1] - tray[1]) < INSIDE and p[2] < BELOW)
    return placed


def run_episode(model: mujoco.MjModel, state: np.ndarray, pick_and_place) -> dict:
    data = reset(model, state)
    start = {name: data.body(name).xpos[:2].copy() for name in CUBES}
    reported = pick_and_place(model, data)
    elapsed = data.time
    hold(model, data, HOLD)
    moved = {name: float(np.linalg.norm(data.body(name).xpos[:2] - start[name])) for name in CUBES}
    return {"reported": reported, "placed": judge(model, data), "seconds": elapsed, "moved": moved}


def degrade_grasp(model: mujoco.MjModel) -> None:
    """Pads with almost no friction (0.02): no grasp can lift a cube. For testing failure reports."""
    for pad in ("gripper/pad_left", "gripper/pad_right"):
        model.geom_friction[model.geom(pad).id, 0] = 0.02


_CACHE: dict = {}


def _episode(module_file: str, state: np.ndarray, degraded: bool) -> dict:
    if module_file not in _CACHE:
        spec = importlib.util.spec_from_file_location(f"routine_{len(_CACHE)}", module_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CACHE[module_file] = module
    model = make_model()
    if degraded:
        degrade_grasp(model)
    return run_episode(model, state, _CACHE[module_file].pick_and_place)


def run_many(module_file: str, states: np.ndarray, degraded: bool = False, workers: int | None = None) -> list[dict]:
    """Episodes in parallel processes; the routine is the module at `module_file`."""
    workers = workers or min(16, os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        return list(pool.map(_episode, [module_file] * len(states), list(states), [degraded] * len(states)))
