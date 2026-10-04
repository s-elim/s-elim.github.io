"""Project 6 starter: operational-space control of arm7.xml tracking a circle, elbow held in the null space.

Fill in the three functions. Run the tests with:

    MJC_IMPL=starter pytest projects/p06_osc_circle
"""

import mujoco
import numpy as np

RADIUS = 0.10          # m
FREQUENCY = 0.5        # Hz


def circle(t: float, start: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Desired position, velocity and acceleration at time t on a horizontal (x-y) circle of RADIUS,
    traversed counter-clockwise at FREQUENCY, that passes through `start` at t = 0 moving in +y."""
    raise NotImplementedError


def null_space_projector(jac: np.ndarray, mass: np.ndarray) -> np.ndarray:
    """The (nv, nv) matrix N^T such that joint torques N^T tau0 produce no acceleration of the task
    (jac, shape (3, nv)) for a robot with joint-space mass matrix `mass`."""
    raise NotImplementedError


def osc_torque(model: mujoco.MjModel, data: mujoco.MjData, site: str, x_des: np.ndarray, v_des: np.ndarray,
               a_des: np.ndarray, q_posture: np.ndarray,
               controller: tuple[mujoco.MjModel, mujoco.MjData] | None = None) -> np.ndarray:
    """Joint torques (inside ctrlrange) for position-only operational-space control of `site`, plus a
    posture term toward q_posture that acts only in the null space of the task.

    Read the robot's state and kinematics from (model, data). Take the mass matrix and bias forces from
    `controller`, the controller's own (model, data), when it is given: that model may be wrong.
    The test calls this right after mj_step.
    """
    raise NotImplementedError
