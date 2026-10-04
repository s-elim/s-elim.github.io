# Project 5: inverse kinematics under test

**Level** 6 (after Lessons 6.1 to 6.3) · **Time** 3 to 4 hours · **Difficulty** 3 of 5

## Objective

Six-dimensional inverse kinematics for the `ee` site of `models/arm7.xml`: position and orientation, by damped least squares, inside the joint limits, with a null-space term that picks the solution closest to a preferred posture. The solver must also say when it has failed. An IK routine that returns a wrong answer with a success flag is worse than one that returns nothing.

## Prerequisites

- Lesson 6.1 (Jacobians from `mj_jacSite`), Lesson 6.2 (damped least squares), Lesson 6.3 (redundancy and the null space).
- Lesson 1.2 for quaternions: MuJoCo stores them as $(w, x, y, z)$, and $q$ and $-q$ are the same rotation.

## Starter code

- `pose_error(model, data, site, target_pos, target_quat)`: the 6-vector of position error and rotation-vector error, both in the world frame.
- `solve(model, site, target_pos, target_quat, q_init, posture=None)`: returns `(q, success)`.

## Expected behaviour

"Reachable" is defined without the solver: the tests generate targets by forward kinematics of random joint vectors inside the limits, so every target has at least one exact solution. The tests use seed 2026. The numbers below are from seed 123, which the reference was developed on.

- **Reachable targets.** On the 100 targets, the reference reaches 77 from the `home` start, 85 with up to 2 random restarts, 98 with 5 and 100 with 20, in 2.7 s on one CPU core. The worst final errors are 0.05 mm and 0.0005 degree, far inside the 1 mm and 1 degree acceptance, because the solver keeps iterating until the posture term stops moving.
- **Unreachable targets.** The reference returns `success = False` for positions beyond the 1.05 m reach and below the floor. It also returns `False` for a position 5 cm under the top of the workspace with the tool pointing down. That position is reachable pointing up, but pointing down would need the wrist 21 cm higher than it can go.
- **Posture.** Given the `home` pose as target, a start 0.3 rad away on every joint and `posture = home`, the solver returns `home` to $7 \times 10^{-6}$ rad. The null-space term chose that solution among the arm's one-parameter family of solutions.

## Tests

```bash
MJC_IMPL=starter pytest projects/p05_ik
pytest projects/p05_ik
```

Nine tests:

- the pose error, including $q$ versus $-q$;
- 100 reachable targets, each checked by an independent forward-kinematics test of the returned joints, plus joint limits;
- 20 targets given as negated quaternions;
- five unreachable targets;
- the posture test.

Each common failure below was introduced into the reference as a mutant and fails at least one test.

## Common failures

- **Quaternion sign.** A hand-written conversion such as angle $= 2\arccos w$ along the vector part, without first flipping $q$ to $w \ge 0$, solved all 100 targets as given (forward kinematics happens to return $w \ge 0$) and 0 of 100 when the same targets were negated. MuJoCo's own `mju_quat2Vel` already wraps angles above $\pi$ (`engine_util_spatial.c`), so with it the flip is redundant but harmless.
- **The damped "null-space" projector.** $I - J^\top(JJ^\top + \lambda^2 I)^{-1}J$ is not a projector onto the null space. A posture term passed through it leaks into the task: the reference with this projector solved 0 of 100 targets, even with 20 restarts. Use $I - J^{+}J$ with the pseudo-inverse.
- **A zero Jacobian.** `mj_jacSite` reads `cdof` and `subtree_com`, which `mj_comPos` computes, not `mj_kinematics`. On a fresh `MjData` the Jacobian is then all zeros and the solver does not move.
- **Success claimed from position alone.** A solver that down-weights orientation and checks only position reports success at poses whose orientation is off. The tests check every success claim with their own forward kinematics.
- **Ignoring joint limits.** Without clipping, the solver returned joint angles outside the limits and claimed success below the floor.

## Extension challenges

1. Analytic IK for the 2-link arm (`arm2.xml`) and a comparison with your solver: accuracy, iterations, and what happens at the elbow singularity.
2. Iterations to converge against the damping $\lambda$, from $10^{-3}$ to 0.5; explain the curve.
3. Collision-aware IK: reject solutions where `mj_collision` reports arm self-contact, and measure how many targets that removes.

## Solution

`solution.py`, about 60 lines.
