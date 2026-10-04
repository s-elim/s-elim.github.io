# Project 7: a grasp that survives randomization

**Level** 10 (after Lessons 10.1 and 9.3; Research mode for the statistics) · **Time** 3 hours · **Difficulty** 3 of 5

## Objective

On `models/gantry_gripper.xml`, write a grasp-and-lift routine that works whatever cube it is given. The cube's position, yaw, mass and friction are randomized. The routine is judged on 400 initial states drawn from a seed you did not tune on, and must succeed on at least 95% of them with a 95% Wilson lower bound above 90%.

## Prerequisites

- Lesson 10.1 (the friction budget of a grasp, and why fast lifts drop heavy objects).
- Lesson 9.3 (how MuJoCo combines the friction of two geoms, including `priority`).
- The Research mode page (Wilson intervals, paired designs, held-out seeds).

## Starter code

- `grasp_scene.py` is the evaluation protocol: the randomization, the episode loop and the success test. Read it; do not edit it.
- `starter.py` asks for `make_controller(model, data)`. It is called once at $t = 0$ and may read the cube's pose; it returns `controller(t, data)`, which gives the four gantry and gripper commands every 10 ms.

The randomization is uniform and independent over these ranges:

| Quantity | Range |
|---|---|
| cube centre x, y | ±0.2 m |
| yaw | ±π/4 rad (a cube repeats every π/2) |
| mass | 0.05 to 0.5 kg, inertia scaled with it |
| sliding friction | 0.4 to 1.2 |

Success means three things. Through the whole final second of the 5 s episode, the cube is at least 0.10 m above where it started. At the end it moves slower than 0.02 m/s. And it touches both pads.

**A randomization that does nothing.** The gripper's pads have geom priority 1. When two geoms of different priority touch, MuJoCo uses the higher-priority geom's friction, so a pad-cube contact uses the pad's 1.5 whatever the cube's friction is set to. A randomizer that only edits the cube's `geom_friction` leaves the grasp unchanged. Measured with the cube's friction set to 0.3, the pad-cube contacts still reported 1.5. `grasp_scene.py` therefore raises the cube's priority to 2, so the sampled friction governs both its contacts.

## Expected behaviour

The reference reads the cube's position once, moves above it, descends with the gripper open, closes for 0.6 s, and lifts 0.15 m along a 1.5 s minimum-jerk profile. It never rotates: the gantry cannot, and closing the jaws turns a yawed cube square to them.

- **Results.** 200 of 200 on the tuning seed (0). 400 of 400 on the test seed (7), Wilson interval [0.990, 1.000]. All 32 corner states, where every quantity is at an end of its range, also succeed.
- **Lift speed.** On the tuning seed, success is 1.000 with a 0.6 s lift, 0.985 [0.957, 0.995] with 0.3 s, and 0.690 [0.623, 0.750] with 0.15 s. The fast-lift failures follow the friction budget, as the table shows: heavy, slippery cubes fail, and yaw hardly matters (0.66 below 0.4 rad, 0.73 above).

  | Fast lift (0.15 s), mass | μ 0.40 to 0.67 | μ 0.67 to 0.93 | μ 0.93 to 1.20 |
  |---|---|---|---|
  | 0.05 to 0.20 kg | 0.95 (n = 21) | 1.00 (n = 26) | 1.00 (n = 23) |
  | 0.20 to 0.35 kg | 0.22 (n = 18) | 0.87 (n = 23) | 1.00 (n = 20) |
  | 0.35 to 0.50 kg | 0.13 (n = 15) | 0.18 (n = 28) | 0.69 (n = 26) |

- **What the ineffective randomizer would have reported.** With the cube's priority left at 0, the same 0.15 s lift scores 200 of 200. The evaluation would have overstated it by 31 points.

## Tests

```bash
MJC_IMPL=starter pytest projects/p07_robust_grasp
pytest projects/p07_robust_grasp
```

Three tests: commands inside `ctrlrange`; the 32 corner states; and the held-out rate on 400 states from seed 7 (about 12 s). The common failures that a routine can make are mutants in `mutants.json`; `python tools/mutate_project.py p07_robust_grasp` checks that each one fails.

## Common failures

- **Tuning on the evaluation seed.** The tests' seed is visible, so nothing stops you; the number you report is then a training score. Tune on seed 0 and run the tests once at the end.
- **Lifting too fast for heavy cubes.** See the table: a 0.15 s lift fails the corner test and the held-out bound.
- **Aiming at the nominal position.** A routine tuned on one cube placement fails as soon as the cube moves.
- **Checking success before the cube has settled.** The protocol requires a 1 s hold and a speed limit. In this scene, a check at the end of a fast lift happened not to inflate the rate (0.62 against 0.69 with the hold). No episode passed early and failed later, because slipping cubes slip as the lift starts and never rise. A slower slip, such as a swinging or slowly creeping cube, would pass an early check. The hold is there for those.

## Extension challenges

1. Detect grasp failure from the pad contact forces before lifting (sum of normal forces against $mg/2\mu$), and retry. Measure the gain under a 0.15 s lift.
2. Widen the friction range down to 0.2 and find the fastest lift that still meets the bound.
3. Make the routine closed loop: correct the gantry's position from the cube's pose during the descent, and test with a cube that is nudged sideways after $t = 0$.

## Solution

`solution.py`, about 35 lines.
