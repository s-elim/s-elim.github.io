"""Project 3 starter: a 3-DOF arm with a two-finger gripper, written in MJCF from an empty file.

Write the model in arm3.xml (same folder), then fill in POSES. Run the tests with:

    MJC_IMPL=starter pytest projects/p03_arm3
"""

from pathlib import Path

import numpy as np

MODEL_FILE = Path(__file__).with_name("arm3.xml")

# Three named poses, each a full qpos vector (yaw, shoulder, elbow, finger_left, finger_right),
# at which no two geoms may touch. One of them must have the gripper fully closed.
POSES: dict[str, np.ndarray] = {}


def model_xml() -> str:
    """The MJCF text of your model."""
    return MODEL_FILE.read_text()
