"""Project 9 scene: Project 8's task seen through a camera. Shared by the tests, the starter and the
solution; do not edit it.

The layouts, the 1 s hold and the judge are Project 8's. What changes is what your routine gets: not
mjData but a Robot, which offers what a real robot would have:

    robot.model          the MjModel (robot geometry, cameras; the cubes' poses in it are not the
                         randomized ones)
    robot.qpos, .qvel    the 9 arm and finger joint positions, velocities
    robot.time           seconds since the episode started
    robot.step(ctrl)     apply the 8 controls for one timestep
    robot.grip_opening() the gripper tendon length (the average finger opening), m
    robot.pad_forces()   normal contact force on the left and right pad, N (tactile sensing)
    robot.observe()      the front camera: depth (H, W) in m along the optical axis, segmentation
                         (H, W, 2) of [object id, object type], the camera position (3,) and
                         orientation (3, 3) in the world

Cube poses are never exposed; Robot keeps the simulation in a private attribute and the rules
forbid reaching into it.
"""

import importlib.util
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

import mujoco
import numpy as np

from mjcourse import model_path

CUBES = ("red_cube", "green_cube", "blue_cube")
GRASP_STAGE = ("not seen", "IK failed", "grasp missed", "dropped while lifting", "knocked over")
CATEGORIES = ("success", "not seen", "IK failed", "grasp missed", "dropped while lifting",
              "dropped while carrying", "missed the tray", "knocked over")
EPISODE_LIMIT = 45.0       # s of simulated time
HOLD = 1.0                 # s
INSIDE, BELOW = 0.05, 0.06  # m
CAMERA, WIDTH, HEIGHT = "front", 640, 480


def make_model() -> mujoco.MjModel:
    return mujoco.MjModel.from_xml_path(str(model_path("pick_place")))


def sample_states(seed: int, n: int) -> np.ndarray:
    """(n, 3, 3) array: for each episode and cube, [x, y, yaw]. Project 8's distribution."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, 3, 3))
    for i in range(n):
        while True:
            xy = np.column_stack([rng.uniform(0.35, 0.60, 3), rng.uniform(-0.25, 0.05, 3)])
            if min(np.linalg.norm(xy[a] - xy[b]) for a, b in ((0, 1), (0, 2), (1, 2))) >= 0.09:
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


class Robot:
    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData, renderer: mujoco.Renderer):
        self.model, self._data, self._renderer = model, data, renderer
        self._pads = (model.geom("gripper/pad_left").id, model.geom("gripper/pad_right").id)
        self._grip = model.tendon("gripper/grip").id

    @property
    def qpos(self) -> np.ndarray:
        return self._data.qpos[:9].copy()

    @property
    def qvel(self) -> np.ndarray:
        return self._data.qvel[:9].copy()

    @property
    def time(self) -> float:
        return float(self._data.time)

    def step(self, ctrl: np.ndarray) -> None:
        self._data.ctrl[:] = ctrl
        mujoco.mj_step(self.model, self._data)

    def grip_opening(self) -> float:
        mujoco.mj_forward(self.model, self._data)
        return float(self._data.ten_length[self._grip])

    def pad_forces(self) -> np.ndarray:
        mujoco.mj_forward(self.model, self._data)
        forces, wrench = np.zeros(2), np.zeros(6)
        for i, c in enumerate(self._data.contact[:self._data.ncon]):
            for k, pad in enumerate(self._pads):
                if pad in (c.geom1, c.geom2) and set(self._pads) != {c.geom1, c.geom2}:
                    mujoco.mj_contactForce(self.model, self._data, i, wrench)
                    forces[k] += abs(wrench[0])
        return forces

    def observe(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        mujoco.mj_forward(self.model, self._data)
        r, cam = self._renderer, self.model.camera(CAMERA).id
        r.update_scene(self._data, CAMERA)
        r.enable_depth_rendering()
        depth = r.render().copy()
        r.disable_depth_rendering()
        r.enable_segmentation_rendering()
        seg = r.render().copy()
        r.disable_segmentation_rendering()
        return depth, seg, self._data.cam_xpos[cam].copy(), self._data.cam_xmat[cam].reshape(3, 3).copy()


def hold(model: mujoco.MjModel, data: mujoco.MjData, seconds: float) -> None:
    """PD with gravity compensation on the arm's current joint angles (the scene's, not yours)."""
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
    return {name: bool(abs(data.body(name).xpos[0] - tray[0]) < INSIDE and abs(data.body(name).xpos[1] - tray[1]) < INSIDE
                       and data.body(name).xpos[2] < BELOW) for name in CUBES}


def run_episode(model: mujoco.MjModel, state: np.ndarray, pick_and_place, renderer: mujoco.Renderer) -> dict:
    data = reset(model, state)
    reported = pick_and_place(Robot(model, data, renderer))
    elapsed = data.time
    hold(model, data, HOLD)
    return {"reported": reported, "placed": judge(model, data), "seconds": elapsed}


def first_frame(model: mujoco.MjModel, state: np.ndarray, renderer: mujoco.Renderer):
    """The camera's view of a layout at t = 0, and the true cube centres (x, y) for scoring estimators."""
    data = reset(model, state)
    truth = {name: data.body(name).xpos[:2].copy() for name in CUBES}
    return Robot(model, data, renderer).observe(), truth


_CACHE: dict = {}


def _load(module_file: str):
    if module_file not in _CACHE:
        spec = importlib.util.spec_from_file_location(f"routine_{len(_CACHE)}", module_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        model = make_model()
        _CACHE[module_file] = (module, model, mujoco.Renderer(model, HEIGHT, WIDTH))
    return _CACHE[module_file]


def degrade_grasp(model: mujoco.MjModel) -> None:
    """Pads with almost no friction (0.02): no grasp can lift a cube. For testing failure reports."""
    for pad in ("gripper/pad_left", "gripper/pad_right"):
        model.geom_friction[model.geom(pad).id, 0] = 0.02


def _episode(module_file: str, state: np.ndarray, degraded: bool = False) -> dict:
    module, model, renderer = _load(module_file)
    if degraded:
        model = make_model()
        degrade_grasp(model)
        renderer = mujoco.Renderer(model, HEIGHT, WIDTH)
    return run_episode(model, state, module.pick_and_place, renderer)


def _estimate(module_file: str, state: np.ndarray) -> tuple[dict, dict]:
    module, model, renderer = _load(module_file)
    (depth, seg, cam_pos, cam_mat), truth = first_frame(model, state, renderer)
    return module.estimate_cubes(model, depth, seg, cam_pos, cam_mat), truth


def _pool(workers):
    # spawn, not fork: a process forked after an OpenGL context was created (pytest's GL check does
    # that) inherits Mesa's locks in an unusable state, and its workers hang without using any CPU.
    return ProcessPoolExecutor(max_workers=workers or min(16, os.cpu_count() or 1),
                               mp_context=multiprocessing.get_context("spawn"))


def run_many(module_file: str, states: np.ndarray, degraded: bool = False, workers: int | None = None) -> list[dict]:
    with _pool(workers) as pool:
        return list(pool.map(_episode, [module_file] * len(states), list(states), [degraded] * len(states)))


def estimate_many(module_file: str, states: np.ndarray, workers: int | None = None) -> list[tuple[dict, dict]]:
    with _pool(workers) as pool:
        return list(pool.map(_estimate, [module_file] * len(states), list(states)))
