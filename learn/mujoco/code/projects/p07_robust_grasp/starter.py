"""Project 7 starter: a grasp-and-lift routine for gantry_gripper.xml that survives randomization.

grasp_scene.py defines the randomization, the episode and the success test; read it, do not edit it.
Tune on grasp_scene.sample_states(seed=0, ...) only: the tests evaluate on a different seed.

    MJC_IMPL=starter pytest projects/p07_robust_grasp
"""

import mujoco


def make_controller(model: mujoco.MjModel, data: mujoco.MjData):
    """Called once at t = 0 with the randomized scene. You may read the cube's pose from `data` here
    (Project 9 takes that privilege away). Return controller(t, data) -> np.ndarray of 4 controls:
    the gantry's x, y, z position targets (m) and the gripper half-opening (m), inside ctrlrange.
    The episode calls it every 10 ms for 5 s.
    """
    raise NotImplementedError
