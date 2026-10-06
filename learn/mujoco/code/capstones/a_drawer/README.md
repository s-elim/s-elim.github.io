# Capstone A: 7-DOF Manipulation Environment (Drawer Opening)

## 1. Objective and Overview

This capstone implements a Gymnasium environment and evaluation suite for 7-DOF manipulation on `models/articulated.xml`. The task requires a robotic manipulator with a parallel gripper to approach, grasp, and pull open a cabinet slide drawer past a 0.10 m threshold under physical contact.

The environment adheres to the course instrument specification (`mjcourse.capstone`):
- Full Gymnasium API compliance (`check_env`);
- Independent observation copies on step and reset;
- Time limits reported strictly as truncation, never termination;
- Deterministic reproducibility under explicit seeding;
- Strict sensor declarations matching real-robot instruments;
- Zero privileged state leakage (tested against object velocity, mass, friction, and contact stiffness perturbations).

Three control representations are provided: Cartesian end-effector deltas (`ee_delta`), joint angle target deltas (`joint_delta`), and direct joint torques (`torque`).

## 2. Specification Along the Seven Axes

| Axis | Choice in Capstone A |
|---|---|
| **Task** | Cabinet drawer opening on `models/articulated.xml` (MuJoCo 3.14.0). Lower slide drawer (`range="0 0.2"` m, damping 5 N s/m, frictionloss 0.5 N m). Target displacement threshold is 0.10 m. |
| **Observation** | 23-dimensional float32 vector: 7 joint positions (`joint encoders`), 7 joint velocities (`joint encoders, differentiated`), 3 TCP Cartesian coordinates (`forward kinematics of the joint encoders`), 1 gripper opening (`joint encoders`), 3 handle coordinates (`camera tracker`), 1 drawer slide coordinate (`joint encoders`), 1 target opening distance (`task specification`). |
| **Action** | Three operational spaces at 20 Hz control rate (0.002 s timestep, frame skip 25): `ee_delta` (4D: dx, dy, dz translation in meters, gripper command), `joint_delta` (8D: joint displacement deltas in radians, gripper command), `torque` (8D: joint torques in N m with gravity compensation, gripper command). |
| **Episode** | Horizon is 100 steps (5.0 seconds). Early termination occurs upon opening the drawer to 0.10 m. Step expiration is reported as truncation (`truncated=True`, `terminated=False`). |
| **Initialization** | Robot arm initialized at collision-free pre-grasp pose 12 cm ahead of the handle, perturbed with uniform noise in [-0.01, 0.01] rad from `self.np_random`. Initial drawer slide position is randomized in [0.0, 0.015] m. |
| **Evaluation** | 200 independent held-out evaluation seeds (1000 to 1199). Zero evaluation data used for tuning. |
| **Metric** | Binomial success rate with exact two-sided 95% Wilson score confidence interval. |

## 3. Acceptance Verification

Running the acceptance checker across all three action representations:

```bash
python -m mjcourse.capstone capstones.a_drawer.env:DrawerEnv --kwargs '{"action_mode": "ee_delta"}' --object drawer
python -m mjcourse.capstone capstones.a_drawer.env:DrawerEnv --kwargs '{"action_mode": "joint_delta"}' --object drawer
python -m mjcourse.capstone capstones.a_drawer.env:DrawerEnv --kwargs '{"action_mode": "torque"}' --object drawer
```

Each mode passes all six criteria:
```text
PASS  gymnasium check_env
PASS  observations are copies
PASS  time limit reported as truncation
PASS  reproducible with a seed
PASS  observation sources are sensors
PASS  no privileged quantity leaks
PASS  model fingerprint: a113e5528ae5a96643342c88a428d9a9a729e62f7c043db75c71021adf67a586
```

When privileged quantities are introduced (for example `extra_observations=("drawer_velocity",)`), the checker halts with exit code 1, isolating both the undeclared sensor provenance and the parameter leak.

## 4. Experimental Results

Evaluated across the 200 held-out evaluation seeds (seeds 1000 through 1199):

| Policy | Control Representation | Success Count | Success Rate | 95% Wilson Score Interval |
|---|---|---|---|---|
| **Scripted finite-state** | `ee_delta` (4D) | 200 / 200 | **100.0%** | [98.1%, 100.0%] |
| Constant pull | `ee_delta` (4D) | 0 / 200 | 0.0% | [0.0%, 1.9%] |
| Constant push | `ee_delta` (4D) | 0 / 200 | 0.0% | [0.0%, 1.9%] |
| Zero action | `ee_delta` (4D) | 0 / 200 | 0.0% | [0.0%, 1.9%] |

The scripted policy exceeds the 90.0% threshold mandated by the rubric. Open-loop constant action baselines fail completely (0.0%), confirming that the task cannot be solved by open-loop drift or static commands.

## 5. Failure Mode Taxonomy

While the scripted policy achieves 100% on the nominal held-out distribution, stress-testing under extreme out-of-distribution perturbations identifies four distinct failure classes:

1. **Pre-grasp misalignment**: When initial robot pose perturbation exceeds the finger clearance (greater than 40 mm lateral offset), the gripper closes outside the handle envelope, yielding zero drawer traction.
2. **Premature clamp**: Triggering gripper closure before Cartesian position error drops below 12 mm causes the fingertips to collide with the handle front face, pushing the drawer inward rather than enclosing the bar.
3. **Grasp slip under high impedance velocity**: Pulling at step velocities above 0.03 m per step induces contact normal forces that exceed the friction cone limit (mu = 1.2), causing the pads to slip off the cylindrical handle.
4. **Kinematic limit stall**: When the cabinet position is shifted beyond x = 0.88 m, arm joints 2 and 4 reach their mechanical stops before the 0.10 m opening distance is reached, truncating the episode.

## 6. Reproduction Commands

To execute the test suite and evaluation protocol:

```bash
# Run acceptance test suite
pytest tests/test_capstone_a.py

# Run preregistered evaluation and generate run_record.json
python capstones/a_drawer/eval.py
```
