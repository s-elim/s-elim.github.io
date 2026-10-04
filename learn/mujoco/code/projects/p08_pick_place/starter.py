"""Project 8 starter: scripted pick-and-place of all three cubes into the tray on pick_place.xml.

pick_scene.py defines the randomization, the rules and the judge; read it, do not edit it.
Use your IK from Project 5 or your controller from Project 6 (or mjcourse.kinematics / control).

    MJC_IMPL=starter pytest projects/p08_pick_place
"""

import mujoco


def pick_and_place(model: mujoco.MjModel, data: mujoco.MjData) -> dict[str, str]:
    """Put red_cube, green_cube and blue_cube in the tray, then return, for each cube, one category from
    pick_scene.CATEGORIES: "success" only if you checked that the cube rests in the tray, otherwise the
    stage at which it failed. Judge from the world (contacts, positions), never from the plan.
    """
    raise NotImplementedError
