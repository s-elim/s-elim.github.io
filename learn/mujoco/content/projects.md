Twenty projects, from a pendulum simulator to a research-grade benchmark. Each one is a self-contained folder in `code/projects/` with a README (objective, prerequisites, starter code, expected behaviour, tests, common failures, extension challenges), a `starter.py` with the functions you write, a reference `solution.py`, and pytest tests that run against either:

```bash
MJC_IMPL=starter pytest projects/p01_pendulum    # test your own implementation
pytest projects/p01_pendulum                     # test the reference solution
```

Projects get harder in three ways as you go down the list: more of the system is yours to design, the acceptance criteria move from "matches a known answer" to "meets a measured standard on held-out conditions", and the instructions shrink. By Project 16 the README states a goal and an evaluation protocol, not a recipe.

**Status.** Projects marked **built** have their folder, starter, solution and tests in the repository, and the tests pass. Projects marked **specified** have a fixed specification below (objective, acceptance criteria, failure modes) but no code yet. The specification is the contract the code will be written against.

| # | Project | Level | Status |
|---|---|---|---|
| 1 | [Pendulum simulator that matches MuJoCo](#/project/p01_pendulum) | 1 | built |
| 2 | [Cart-pole balance by LQR on MuJoCo's linearization](#/project/p02_cartpole) | 8 | built |
| 3 | [A 3-DOF arm with a gripper, from an empty file](#/project/p03_arm3) | 2, 5 | built |
| 4 | [Joint PD and gravity compensation on the 7-DOF arm](#/project/p04_joint_pd) | 8 | built |
| 5 | [Inverse kinematics under test](#/project/p05_ik) | 6 | built |
| 6 | Cartesian (operational-space) circle tracking | 8 | specified |
| 7 | A grasp that survives randomization | 10 | specified |
| 8 | Scripted pick-and-place on the 7-DOF arm | 10 | specified |
| 9 | Camera-based manipulation without privileged state | 11 | specified |
| 10 | A Gymnasium environment that passes review | 12 | specified |
| 11 | PPO on a manipulation task | 13 | specified |
| 12 | SAC on the same task, compared fairly | 13 | specified |
| 13 | Behaviour cloning, and what DAgger fixes | 14 | specified |
| 14 | A vision-based policy, and the price of pixels | 15 | specified |
| 15 | Language-conditioned pick-and-place | 16 | specified |
| 16 | A domain-randomized policy, tested out of range | 17 | specified |
| 17 | System identification of a hidden model | 18 | specified |
| 18 | A sim-to-sim transfer experiment | 19 | specified |
| 19 | Bimanual box lift | 5, 8, 10 | specified |
| 20 | A research-grade embodied-AI benchmark | 21 | specified |

## Specifications

### 6. Cartesian circle tracking

**Objective.** Operational-space control of `arm7.xml` tracking a 10 cm circle at 0.5 Hz while a null-space term keeps the elbow up. **Accept when** RMS tracking error is under 5 mm after the first cycle, the elbow's height stays within 2 cm of its initial value, and the result is reported with the controller's model mismatch test (halve the controller's link masses; report the error). **Common failures:** using the Jacobian of the wrong site; inverting the task-space inertia near singularities without regularization; null-space torques that leak into the task. **Extensions:** add orientation control; add Cartesian impedance and press against a wall with a set force.

### 7. A grasp that survives randomization

**Objective.** On `gantry_gripper.xml`, design a grasp-and-lift routine that succeeds under randomized cube position, yaw, mass and friction. **Accept when** success is at least 95% with a 95% Wilson lower bound above 90%, on 400 held-out initial states from a seed you did not tune on. **Common failures:** tuning on the evaluation seed; lifting too fast for heavy cubes (Research mode shows the effect); success tested before the cube has settled. **Extensions:** add grasp-success detection from contact forces and retry on failure.

### 8. Scripted pick-and-place on the 7-DOF arm

**Objective.** A state machine on `pick_place.xml` (approach, descend, close, lift, transport, place, release, retreat) using Project 5's IK or Project 6's controller. **Accept when** each cube is placed in the tray on 90% of 100 randomized episodes, with success judged from the final cube position after release and a hold period, and every failure categorized. **Common failures:** judging grasp success from the plan rather than from contacts; collisions between the gripper and the tray walls; releasing above the tray before the cube has stopped swinging. **Extensions:** stack all three cubes.

### 9. Camera-based manipulation without privileged state

**Objective.** Repeat Project 8 with the cube positions estimated from the front camera's depth and segmentation images, not read from `mjData`. **Accept when** estimated cube centres are within 5 mm of the truth on 95% of frames and the pick success rate is within 10 points of Project 8's. **Common failures:** depth pixels at the far plane (80 m) left in the point cloud; camera extrinsics with the wrong axis convention; segmentation ids confused between geoms and sites. **Extensions:** use only RGB with a learned detector trained on rendered data.

### 10. A Gymnasium environment that passes review

**Objective.** A `gymnasium.Env` for the push task built from scratch on `push.xml`, with three action-space variants (joint torques, joint targets, end-effector deltas). **Accept when** `gymnasium.utils.env_checker.check_env` passes, seeding reproduces trajectories bit for bit, `terminated` and `truncated` are separated correctly, and a test fails if any observation component has no real-robot source. **Common failures:** stale observations after reset (Debugging clinic, case 11); time limits reported as termination; rewards that read privileged state the observation hides. **Extensions:** a vectorized version and its throughput.

### 11. PPO on a manipulation task

**Objective.** Train PPO, implemented in the course package or your own, on the reach task. **Accept when** 5 training seeds reach a mean success above 90% on 100 held-out initial states each, reported as an interquartile mean with a bootstrap interval, plus one ablation with the same budget. **Common failures:** evaluating stochastic actions; normalizing observations with statistics that leak evaluation data; reporting the best seed. **Extensions:** measure wall-clock time split between simulation and learning.

### 12. SAC on the same task, compared fairly

**Objective.** Train SAC on Project 11's task and compare with PPO. **Accept when** both methods get the same environment steps, the same evaluation protocol and a documented tuning budget, and the comparison reports intervals and a sample-efficiency curve. **Common failures:** unequal tuning effort; comparing at different numbers of environment steps; one method evaluated deterministically and the other stochastically. **Extensions:** add TD3 and a third task.

### 13. Behaviour cloning, and what DAgger fixes

**Objective.** On `point_mass.xml`, collect demonstrations from a scripted expert, train behaviour cloning, then run DAgger. **Accept when** closed-loop success (not validation loss) is reported against the number of expert labels, with state-distribution plots before and after DAgger, and the log passes a replay test (Debugging clinic, case 12). **Common failures:** observation-action misalignment; judging the policy by loss; the expert itself failing on some states. **Extensions:** a diffusion or mixture policy for multimodal demonstrations.

### 14. A vision-based policy, and the price of pixels

**Objective.** Behaviour cloning on `pick_place.xml` from state and from RGB-D with proprioception, with equal data. **Accept when** both are evaluated on the same held-out states and on a held-out camera pose and lighting, with intervals, and one failure mode of the vision policy is identified from rollouts. **Common failures:** shortcut features (a background pattern that predicts the target); evaluation images rendered with the training camera. **Extensions:** compare depth-only, RGB-only and RGB-D.

### 15. Language-conditioned pick-and-place

**Objective.** Thirty instruction templates over `pick_place.xml` ("put the red cube in the tray", "move the blue cube to the left zone"), split into training templates, held-out paraphrases and held-out object-goal combinations, and a policy or pipeline evaluated per split. **Accept when** per-split success rates are reported with errors separated into language grounding and execution. **Common failures:** paraphrases that leak into training; evaluating only on seen combinations. **Extensions:** replace the parser with a pretrained language model and measure what changes.

### 16. A domain-randomized policy, tested out of range

**Objective.** Train a controller or policy for the push task on nominal and on randomized dynamics, and evaluate both on parameters outside the training range. **Accept when** performance is plotted against the size of the mismatch for both, and the held-out range is disjoint from the training range. **Common failures:** randomization so wide the task becomes impossible; held-out values inside the training range. **Extensions:** curriculum over randomization width.

### 17. System identification of a hidden model

**Objective.** Given trajectories from a pendulum with hidden mass, damping and friction loss plus sensor noise, estimate all three. **Accept when** each estimate is within 5% of the truth with an uncertainty that covers it, validated on a held-out trajectory. **Common failures:** poorly exciting trajectories (check the regressor's condition number); fitting noise. **Extensions:** use MuJoCo's own sysid toolbox and compare.

### 18. A sim-to-sim transfer experiment

**Objective.** Treat a perturbed model (different friction, masses, actuator gains, a 20 ms delay, sensor noise) as "the real robot", unknown to you, and transfer a controller from the nominal model to it. **Accept when** you predict the transfer gap before measuring it, measure it, and explain the difference. **Common failures:** tuning on the "real" model; changing more than you can attribute. **Extensions:** close the gap with system identification (Project 17) and with randomization (Project 16), and compare their costs.

### 19. Bimanual box lift

**Objective.** On `bimanual.xml`, lift the long box with both arms and hold it level. **Accept when** the box rises 10 cm and stays within 5 degrees of level for 3 s on 90% of 50 randomized box poses. **Common failures:** the two arms fighting through the box (internal forces); asymmetric grasps that tilt the box. **Extensions:** hand the box over from one arm to the other.

### 20. A research-grade embodied-AI benchmark

**Objective.** A benchmark of at least five manipulation tasks on the course's scenes with documented task, observation, action, episode, initialization, training and evaluation splits, metrics, seeds and logging, and a baseline evaluated on it. **Accept when** another person can reproduce your baseline numbers from your repository and manifest alone, and the benchmark separates in-distribution success from at least two generalization axes. **Common failures:** evaluation states seen during development; per-episode and per-task aggregation mixed; unversioned simulator. **Extensions:** the final capstone (Level 22).
