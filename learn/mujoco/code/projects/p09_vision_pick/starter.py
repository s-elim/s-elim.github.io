"""Project 9 starter: Project 8 without privileged state. Cube positions come from the front camera.

vision_scene.py defines the Robot your routine receives (no mjData) and the evaluation; read it, do
not edit it. Rendering needs an OpenGL context: MUJOCO_GL=egl or osmesa on a headless machine.

    MJC_IMPL=starter MUJOCO_GL=osmesa pytest projects/p09_vision_pick
"""

import mujoco
import numpy as np


def estimate_cubes(model: mujoco.MjModel, depth: np.ndarray, seg: np.ndarray,
                   cam_pos: np.ndarray, cam_mat: np.ndarray) -> dict[str, np.ndarray]:
    """World (x, y) of the centre of each cube visible in one front-camera frame, keyed by body name
    ("red_cube", "green_cube", "blue_cube"); leave out cubes you cannot see.

    depth (H, W): metres along the camera's optical axis. seg (H, W, 2): [object id, object type] per pixel.
    cam_pos (3,), cam_mat (3, 3): the camera's position and orientation (columns are its axes) in the world;
    a MuJoCo camera looks along its own -z with +y up.
    """
    raise NotImplementedError


def pick_and_place(robot) -> dict[str, str]:
    """Project 8's task through vision_scene.Robot: put all three cubes in the tray, using only the Robot's
    methods, and return a category from vision_scene.CATEGORIES for each cube, judged from what the robot
    can sense (camera, pad forces, jaw opening)."""
    raise NotImplementedError
