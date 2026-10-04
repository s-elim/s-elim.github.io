# Project 6: Cartesian circle tracking

**Level** 8 (after Lessons 8.3 and 6.3) · **Time** 3 to 4 hours · **Difficulty** 3 of 5

## Objective

Operational-space control of `models/arm7.xml`: the `ee` site follows a horizontal circle of radius 10 cm at 0.5 Hz, while a posture term in the null space of the task keeps the elbow where it started. Then give the controller a wrong model of the robot (every link's mass and inertia halved) and measure what that costs.

## Prerequisites

- Lesson 8.3 (operational-space control, task-space inertia $\Lambda = (JM^{-1}J^\top)^{-1}$).
- Lesson 6.3 (redundancy and null spaces).
- Lesson 8.2 for bias forces, and the course fact that `mjData`'s derived fields describe the pre-step state after `mj_step`.

## Starter code

- `circle(t, start)`: desired position, velocity and acceleration on the circle, which passes through `start` at $t = 0$.
- `null_space_projector(jac, mass)`: the matrix $N^\top$ such that torques $N^\top\tau_0$ cause no task acceleration.
- `osc_torque(model, data, site, x_des, v_des, a_des, q_posture, controller=None)`: the joint torques. When `controller` is given, the mass matrix and bias forces come from that model, not from the robot.

## Expected behaviour

The arm starts at the `home` keyframe and tracks for 6 s (three cycles). The error is measured after the first cycle.

- **Exact model.** The reference's RMS error is 0.074 mm, its largest error 0.08 mm, and the elbow (the `link4` body) moves 0.14 cm vertically. No torque reaches its limit. The task-space gains are 400 s⁻² and 40 s⁻¹ on unit mass ($\omega_n$ = 20 rad/s, critically damped), and $\Lambda$ turns them into forces.
- **Halved masses in the controller.** The RMS error rises to 21.2 mm, the largest error to 24.6 mm, and the elbow drops 5.1 cm. The likely mechanism (an inference, not measured term by term) is this: the controller's bias forces supply only half the gravity load, and the feedback that must make up the rest acts through a $\Lambda$ that is also halved.
- **Distance from singularity.** The smallest singular value of the position Jacobian is 0.363 m/rad along the whole path, so $\Lambda$ is well conditioned. This circle does not test regularization.

**A measurement trap.** In a first version of this project's own measurement script, the end-effector position was read right after `mj_step`. That position is the pre-step pose, one step of travel behind (0.314 m/s × 2 ms = 0.63 mm). It reported an RMS error of 0.61 mm, eight times the true 0.074 mm. The test calls `mj_kinematics` before reading.

## Tests

```bash
MJC_IMPL=starter pytest projects/p06_osc_circle
pytest projects/p06_osc_circle
```

Four tests:

- the circle: start point, period, speed, and centripetal acceleration;
- dynamic consistency, $JM^{-1}N^\top = 0$ at five random poses, and $N^\top$ being a projector;
- tracking: RMS error under 5 mm after the first cycle, elbow within 2 cm, every torque inside `ctrlrange`;
- the mismatch run, which must differ from the exact run. This shows the controller uses the model it is given.

The common failures are mutants in `mutants.json`; `python tools/mutate_project.py p06_osc_circle` checks that each one fails a test.

## Common failures

- **The Jacobian of the wrong site.** Using `flange` instead of `ee` makes the flange trace the circle, and the tool tip misses it by the 10 cm between the two sites (measured RMS error 100.0 mm).
- **Null-space torques that leak into the task.** Adding the posture torque without the projector raised the RMS error to 16.2 mm. Removing the posture term altogether let the elbow move 5.4 cm.
- **The kinematic projector.** $I - J^\top (J^{+})^\top$ projects onto the kinematic null space, not the dynamically consistent one. Its torques still accelerate the task: the error went from 0.074 to 1.52 mm. That is inside the 5 mm acceptance, so the projector test, not the tracking test, catches it.
- **Inverting $\Lambda$ near singularities without regularization.** Not exercised by this circle (see above); move the circle toward the edge of the workspace to meet it.
- **Dropping $\dot J \dot q$.** Not one of the spec's failures, but measured: without `mj_jacDot` the error is 0.66 mm, nine times the reference.

## Extension challenges

1. Add orientation control: keep the tool pointing down to within 1 degree around the whole circle.
2. Close the mismatch gap without fixing the model: add an integral term or an online estimate of the gravity load, and report the error with halved masses again.
3. Cartesian impedance: replace the circle with a wall at a known height and press on it with 10 N; measure the force from the contact.

## Solution

`solution.py`, about 50 lines.
