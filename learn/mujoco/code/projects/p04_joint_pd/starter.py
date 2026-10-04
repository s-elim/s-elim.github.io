"""Project 4 starter: joint-space PD and PD with gravity compensation on arm7.xml.

Fill in the constants and the three functions. Run the tests with:

    MJC_IMPL=starter pytest projects/p04_joint_pd
"""

import mujoco
import numpy as np

OMEGA: float = 0.0   # closed-loop natural frequency you design for, rad/s
ZETA: float = 0.0    # damping ratio you design for


def design_gains(model: mujoco.MjModel, data: mujoco.MjData, omega: float, zeta: float) -> tuple[np.ndarray, np.ndarray]:
    """Per-joint (kp, kd) that give each joint, treated alone, natural frequency omega and damping ratio zeta.

    Hint: the inertia each joint sees is the diagonal of the joint-space mass matrix (mujoco.mj_fullM),
    which already includes armature. The joints' own damping (model.dof_damping) adds to kd.
    """
    raise NotImplementedError


def pd_torque(model: mujoco.MjModel, data: mujoco.MjData, q_des: np.ndarray, kp: np.ndarray, kd: np.ndarray,
              compensate: bool) -> np.ndarray:
    """Joint torques for a PD law toward q_des, plus gravity compensation if `compensate`, inside ctrlrange.

    The test calls this right after mj_step, when the derived fields of data describe the previous state.
    """
    raise NotImplementedError


def predicted_steady_error(model: mujoco.MjModel, q_des: np.ndarray, kp: np.ndarray) -> np.ndarray:
    """q_des - q at rest under PD without compensation, predicted without simulating the dynamics."""
    raise NotImplementedError
