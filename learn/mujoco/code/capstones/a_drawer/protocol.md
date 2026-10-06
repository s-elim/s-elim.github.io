# Preregistered Protocol: Capstone A 7-DOF Manipulation Environment

## 1. Research Question and Hypothesis

Can a 7-DOF manipulation environment implemented on MuJoCo with an articulated cabinet and slide joint satisfy Gymnasium compliance, strict sensor provenance, zero privileged state leakage, and support torque, joint delta, and Cartesian end-effector control modes while verifying non-trivial task difficulty?

Hypothesis: A coordinated finite-state policy acting through Cartesian end-effector deltas achieves at least 90% success across 200 held-out start conditions, whereas open-loop constant-action policies fail completely (0% success).

## 2. Specification Along the Seven Axes

1. **Task**: The scene is `models/articulated.xml` on MuJoCo 3.14.0. The robot is a 7-DOF arm with a parallel-jaw gripper facing a static carcass cabinet containing a lower slide drawer (`range="0 0.2"` m, damping 5 N s/m, frictionloss 0.5 N m) equipped with a cylindrical horizontal handle. The objective is to open the drawer past a threshold of 0.10 m.
2. **Observation**: A 23-dimensional float32 vector comprising 7 joint positions (joint encoders), 7 joint velocities (joint encoders, differentiated), 3 end-effector positions (forward kinematics of joint encoders), 1 gripper half-opening (joint encoders), 3 handle positions (camera tracker), 1 drawer slide position (joint encoders), and 1 scalar target opening distance (task specification). No object velocity, mass, friction, or contact stiffness is accessible to the observation.
3. **Action**: Three distinct action representations are supported at 20 Hz control rate (substep 0.002 s, frame skip 25):
   - `ee_delta`: 4-dimensional box in [-1, 1], controlling Cartesian translations (dx, dy, dz) scaled by 0.015 m per step and gripper stroke target;
   - `joint_delta`: 8-dimensional box in [-1, 1], controlling joint displacement targets scaled by 0.05 rad per step and gripper stroke target;
   - `torque`: 8-dimensional box in [-1, 1], supplying direct joint torques scaled to actuator limits on top of gravity compensation bias, plus gripper stroke target.
4. **Episode**: The time limit is 100 environment steps (5.0 seconds of physical time). Early termination occurs once the drawer slide position reaches or exceeds 0.10 m when `terminate_on_success=True`. Reaching the step limit without achieving the threshold is reported as truncation (`truncated=True`, `terminated=False`).
5. **Initialization**: The arm starts in a collision-free pre-grasp configuration positioned 12 cm in front of the drawer handle. Joint angles are perturbed by uniform noise in [-0.01, 0.01] rad drawn from `self.np_random`. The initial drawer position is randomized in [0, 0.015] m.
6. **Evaluation**: Evaluation is conducted across 200 independent held-out seeds (seeds 1000 through 1199). No hyperparameters or policy thresholds are tuned on these seeds.
7. **Metric**: Success rate defined as the proportion of episodes where the drawer is opened to at least 0.10 m within 100 steps. Uncertainty is reported as the two-sided 95% Wilson score interval.

## 3. Falsification Criteria

The primary claim is falsified if any of the following occur:
1. `mjcourse.capstone` checks fail on any of the three action modes.
2. Success rate on the 200 held-out evaluation seeds falls below 90.0%.
3. A constant action policy (such as continuous retract, continuous push, or zero action) achieves a success rate exceeding 5.0%, indicating an uninformative task solvable without closed-loop feedback or coordination.
