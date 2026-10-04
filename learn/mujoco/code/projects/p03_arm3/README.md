# Project 3: a 3-DOF arm with a gripper, from an empty file

**Level** 2 and 5 (after Lessons 2.1 to 2.4 and 5.1 to 5.3) · **Time** 3 to 4 hours · **Difficulty** 2 of 5

## Objective

Write an MJCF model of a three-joint arm with a two-finger gripper, joint limits, position servos, a workspace camera and a keyframe, starting from `arm3.xml`, which is empty. Do not copy a course model: the point is to make every modelling decision yourself and to be able to defend each number.

## Prerequisites

- Lessons 2.1 to 2.4: bodies, joints, geoms, defaults, the compiler's `angle` setting.
- Lesson 5.1 (servos and their stiffness), Lesson 5.3 (the course gripper's "drive one finger, mirror the other" pattern).
- Lesson 2.4 for cameras: a MuJoCo camera looks along its own $-z$ with $+y$ up.

## Starter code

- `arm3.xml`: your model. It starts as an empty `<mujoco>` element.
- `starter.py`: `POSES`, a dictionary of at least three named full `qpos` vectors, and `model_xml()`, which reads `arm3.xml` (leave it as it is).

The tests find the parts by type, so names are yours to choose, with two exceptions: the camera is called `workspace` and the keyframe `home`.

## Expected behaviour

The model must:

- compile with no compiler warning (the tests install a handler with `mujoco.set_mju_user_warning` and require it to stay silent);
- have three limited hinge joints with ranges in radians, two limited slide joints for the fingers, and position servos with control limits on every actuator;
- hold the `home` keyframe under gravity for 5 s with every arm joint within 1 degree of its start, with all of `mjData.warning`'s counters at zero;
- have no contacts at any of the named poses, one of which has the gripper fully closed;
- move the gripper to each end of its control range within 2 mm in 1 s;
- carry a unit comment on every line that sets a number (`<!-- m; kg -->`, or `unitless`).

The reference model holds its keyframe to 0.21 degree. Its shoulder carries a static load of 2.73 N m with the arm horizontal, measured as `qfrc_bias` at that pose; with $k_p$ = 500 N m/rad the predicted steady error is 2.73/500 = 0.0055 rad (0.31 degree). Size your servos the same way: work out the worst gravity load, then pick $k_p$ for the error you can accept.

## Tests

```bash
MJC_IMPL=starter pytest projects/p03_arm3
pytest projects/p03_arm3
```

Six tests: a warning-free compile, the required parts, the 5 s hold, contact-free poses, the gripper response, and the unit comments. Each common failure below is a mutant in `mutants.json`. `python tools/mutate_project.py p03_arm3` applies each one to the reference and checks that the intended test fails; a control mutant (swapped `fromto` ends) must pass.

## Common failures

- **Angles in degrees.** `range="-90 90"` under `angle="radian"` is a range of ±90 rad; the joint is effectively unlimited. The compiler's default is degrees, so state the unit explicitly in `<compiler>`.
- **A link drawn away from the next joint.** Swapping a capsule's two `fromto` ends changes nothing, because a capsule is symmetric. Pointing it the wrong way does: `fromto="0 0 0 0 0 -0.25"` on the upper arm, with the elbow body still at $+0.25$, buries the link in the base. The pose test then reports contacts and the hold test fails.
- **Fingers that collide when closed.** Two finger geoms whose closed positions overlap produce a contact at every closed pose. Leave a gap at the lower limit, or exclude the pair in `<contact>` and say why.
- **Weak servos.** `<position>` defaults to $k_p$ = 1. A servo whose stiffness cannot carry the gravity load sags until the error times $k_p$ equals the load.

## Extension challenges

1. Build the same arm with `mujoco.MjSpec` in Python and test that the compiled models have identical `body_mass`, `jnt_range`, `actuator_gainprm` and `geom_size`.
2. Add a 40 mm cube on a table and a grasp test: close on it, lift 10 cm, hold for 2 s.
3. Replace the stiff shoulder servo with a softer one plus `gravcomp` on the links and `actuatorgravcomp` on the joints, and measure the hold error again.

## Solution

`arm3_solution.xml` (about 60 lines) and `solution.py`, which names its poses.
