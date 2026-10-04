"""Project 3 reference solution: the model is arm3_solution.xml; this module names its poses."""

from pathlib import Path

import numpy as np

MODEL_FILE = Path(__file__).with_name("arm3_solution.xml")

POSES: dict[str, np.ndarray] = {
    "home": np.array([0.0, 0.6, 1.2, 0.02, 0.02]),        # the keyframe
    "reach": np.array([0.8, 1.0, 0.6, 0.035, 0.035]),     # leaning out, gripper open
    "folded": np.array([-1.0, -0.5, 2.2, 0.002, 0.002]),  # elbow tucked, gripper closed
}


def model_xml() -> str:
    return MODEL_FILE.read_text()
