# Project 9: camera-based manipulation without privileged state

**Level** 11 (after Lessons 11.1 and 11.2; Project 8) · **Time** 4 to 6 hours · **Difficulty** 4 of 5

## Objective

Repeat Project 8 with the cube positions estimated from the front camera's depth and segmentation images instead of read from `mjData`. Your routine receives a `Robot`, not `mjData`. A `Robot` offers what a real robot would have: joint encoders, motor commands, a jaw-opening sensor, tactile pad forces and the front camera. Every decision, including whether a cube really landed in the tray, has to come from those.

## Prerequisites

- Lesson 11.1 (intrinsics, extrinsics, MuJoCo's camera axes and the diag(1, −1, −1) conversion to OpenCV's).
- Lesson 11.2 (depth along the optical axis, back-projection, segmentation as [object id, object type]).
- Project 8 (the task, the categories, honest reporting).

## Starter code

- `vision_scene.py` holds Project 8's layouts, hold and judge, plus the `Robot` interface. Read it; do not edit it.
- `starter.py` asks for two functions:
  - `estimate_cubes(model, depth, seg, cam_pos, cam_mat)`, a pure function of one frame. It cannot see the simulation, so its accuracy is measured fairly.
  - `pick_and_place(robot)`, which returns a category per cube.

Rendering needs an OpenGL context. On a machine without a display, set `MUJOCO_GL=egl` or `osmesa`; without one, the tests skip.

## Expected behaviour

**Estimator.** The reference back-projects a cube's pixels and keeps the top face (points within 4 mm of the highest). It returns the midpoint of that face's extent along the face's own principal axes. On the 300 cube views of 100 layouts from the tuning seed, the methods compare as follows:

| Method | Median error | Within 5 mm |
|---|---|---|
| centroid of every visible pixel | 9.6 mm | 0 of 300 |
| centroid of the top face | 2.4 mm | all |
| midpoint of the top face's extent (reference) | 0.45 mm | all (95th percentile 1.2 mm) |

The visible side faces pull the first centroid toward the camera. Nearer pixels of the top face cover less of it, so the second leans toward the camera too, by less. On the test seed (13), the reference's median error is 0.49 mm, with all 300 within 5 mm. In the first frame a cube covers 493 to 860 pixels at 640 × 480 (median 671), and none was hidden by another.

**Task.** The reference is Project 8's state machine, with three changes:

- it looks again before each pick, because an earlier pick may have nudged a cube;
- it judges grasps from the pad forces and the jaw opening, instead of from contacts in `mjData`;
- it checks each placement with a final look into the tray, which the front camera sees over the wall.

It runs its dynamics (bias forces, mass matrix) on its own `MjData` copy, filled from the joint encoders. It placed 300 of 300 cubes on the test seed, every report matched the judge, and 100 episodes took 22 s on 16 processes. Project 8's reference placed 300 of 300 as well, so the gap the specification allows (10 points) is unused.

## Tests

```bash
MJC_IMPL=starter MUJOCO_GL=osmesa pytest projects/p09_vision_pick
MUJOCO_GL=osmesa pytest projects/p09_vision_pick
```

Four tests, about 30 s:

- estimates within 5 mm on at least 95% of 300 cube views, where an unseen cube counts as a miss;
- each cube placed in at least 90% of 100 episodes, 10 points below Project 8's 100%;
- honest reports;
- failures reported at a grasp stage when the pads have no friction.

`python tools/mutate_project.py p09_vision_pick` checks the mutants in `mutants.json`; run it with `MUJOCO_GL` set.

**Parallel episodes.** The scene runs episodes in worker processes started with `spawn`. Workers forked from a process that has created an OpenGL context (pytest's GL check does) inherit Mesa's locks in an unusable state. In this project's first test run they hung without using any CPU. With `spawn`, a script of yours that calls `run_many` must keep its top-level code under `if __name__ == "__main__":`.

## Common failures

- **Camera axes.** Back-projecting in MuJoCo's camera frame as if it were OpenCV's (no diag(1, −1, −1)) mirrors every point. Estimates miss by tens of centimetres and the picks fail.
- **The centroid of the mask.** It is 9.6 mm off. The grasp tolerates that: the routine still placed 300 of 300. But it fails the 5 mm test, and the same error turned up in the routine's own placement check, which once reported a placed cube as "missed the tray".
- **Ids from the wrong table.** Segmentation ids of geoms are geom ids. Matching the cubes' body ids (12 to 14) instead of their geom ids (17 to 19) selects parts of the gripper.
- **Ids without types.** Drawn sites also appear in the segmentation, with type `mjOBJ_SITE`. Matching the id alone is harmless here only because no site's id (0 to 5) equals a cube's geom id; the control mutant confirms it. Check the type anyway.
- **Far-plane depth.** Pixels that see nothing carry the far-plane depth. The front camera sees the floor in every pixel here (largest depth 2.37 m), so this scene cannot catch a routine that forgets them. The side camera's view reaches past the floor, and its background pixels read 80.0 m.
- **Judging success from the plan.** As in Project 8, it is caught by the frictionless-pad test.

## Extension challenges

1. Use only RGB: train a small detector on rendered images with automatic labels from segmentation, and measure the estimate error and the pick rate.
2. Move the camera 5 cm and turn it 3 degrees without telling the routine. Measure the estimate error and the pick rate, then recover with a calibration from the tray's known corners.
3. Add the wrist camera to refine the estimate just before the grasp, and find the camera noise level at which that refinement starts to pay.

## Solution

`solution.py`, about 140 lines.
