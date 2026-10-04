# Project 8: scripted pick-and-place on the 7-DOF arm

**Level** 10 (after Lessons 10.1 and 10.2; Projects 5 or 6) · **Time** 4 to 6 hours · **Difficulty** 3 of 5

## Objective

A state machine on `models/pick_place.xml` that puts all three cubes in the tray: approach, descend, close, lift, transport, place, release, retreat, once per cube. It must also tell the truth. For every cube it reports either "success", checked from where the cube ended up, or the stage at which it failed, checked from the world (contacts, positions), never from the plan.

## Prerequisites

- Lesson 10.2 (one cube, the capture region, checks at every transition).
- Project 5 (IK) or Project 6 (operational-space control); `mjcourse.kinematics` and `mjcourse.control` are the course's versions.

## Starter code

- `pick_scene.py` is the evaluation protocol: random layouts, the rules, a 1 s hold that the scene runs after your routine returns, and an independent judge. Read it; do not edit it. Each layout puts the three cubes at uniformly random positions at least 9 cm apart in a 25 × 30 cm area, with random yaw.
- `starter.py` asks for `pick_and_place(model, data)`. It runs the whole episode (writing only `data.ctrl`, advancing only with `mj_step`, within 40 simulated seconds) and returns a category per cube from `pick_scene.CATEGORIES`.

## Expected behaviour

The reference converts each waypoint to joint angles with `mjcourse.kinematics.solve_ik_restarts`, follows minimum-jerk joint paths with PD and gravity compensation, and places the cubes at three slots 3 cm from the tray's centre lines, nearest cube first. It checks the grasp from contacts and the jaw opening after closing, after lifting and after carrying.

- **Results.** 300 of 300 cubes placed on the tuning seed (0) and 300 of 300 on the test seed (11). Every report matched the judge. Each episode takes 28.5 simulated seconds; 100 episodes take 67 s on one core and 7 s on 16 processes.
- **Degraded grasp.** With the pads' friction cut to 0.02, nothing can be lifted. The reference reports all 60 cubes in 20 episodes as "dropped while lifting", with zero mismatches. A routine that reports success from its plan claimed all 60 as successes.

## Tests

```bash
MJC_IMPL=starter pytest projects/p08_pick_place
pytest projects/p08_pick_place
```

Three tests, run on 100 held-out layouts in parallel processes (about 7 s):

- each cube is placed in at least 90% of episodes;
- every report is a valid category, "success" exactly when the judge says placed, and every episode finishes within the time limit;
- with nearly frictionless pads, every cube is reported as failing at a grasp stage ("IK failed", "grasp missed", "dropped while lifting" or "knocked over").

`python tools/mutate_project.py p08_pick_place` checks the mutants in `mutants.json`. One of them, ignoring the cube's yaw, is a control that must pass (see below).

## Common failures

- **Judging grasp success from the plan.** The arm reaching the grasp pose says nothing about the cube. Without the contact checks, the routine still placed every cube in the normal scene, so the success-rate test cannot see the difference. The degraded-grasp test can: there the routine reported 60 false successes.
- **Checking only the final position.** This is honest about success but not about stage: the routine reported "missed the tray" for cubes that never left the table. The stage test catches it.
- **All cubes to one point.** Placing every cube at the tray centre stacks them, and the stacked cubes rest above the 6 cm height limit.
- **Collisions with the tray walls, and releasing above the tray before the cube has stopped swinging.** The specification listed these, but neither appeared in this scene. Slots 5 cm from the centre lines (fingers over the walls) placed 60 of 60 cubes in 20 episodes, and so did releasing from the 15 cm carry height without descending. The tray's 5 cm walls and a 40 mm cube leave a wide margin. Make the cube smaller, the tray shallower or the release faster to meet them.
- **Ignoring the cube's yaw.** Harmless here, as in Project 7: closing the jaws turns the cube square to them, and the routine placed 300 of 300 on each seed with the gripper's yaw fixed at 0. Lesson 10.2's capture region gives the limits of that.

## Extension challenges

1. Stack the three cubes in the tray, and add "fell off the stack" to the categories.
2. Add 5 mm of Gaussian error to the cube positions you read, and keep the 90% rate with retries driven by the contact check.
3. Halve the time per episode. Report which stage you shortened and what it cost, with Wilson intervals.

## Solution

`solution.py`, about 110 lines.
