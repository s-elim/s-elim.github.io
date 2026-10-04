# Project 10: a Gymnasium environment that passes review

**Level** 12 (after Lessons 12.1 and 12.2) · **Time** 4 hours · **Difficulty** 3 of 5

## Objective

A `gymnasium.Env` for the push task, written from scratch on `models/push.xml`, with three action spaces: joint torques, joint targets and end-effector deltas. Every quantity in the observation must have a real-robot source. The environment is reviewed by machine: Gymnasium's own checker, the course's five further checks (`mjcourse.capstone`), and tests of what the actions and observations mean.

## Prerequisites

- Lesson 12.1 (the Gymnasium API, `terminated` versus `truncated`, seeding through `self.np_random`).
- Lesson 12.2 (observation sources, the perturbation test for privileged leaks).
- Project 5 or 6 for the end-effector action; `mjcourse.kinematics` is the course's version.

## Starter code

`starter.py` declares `PushEnv(action_mode, max_episode_steps, frame_skip, render_mode)`; its docstring is the specification. Do not subclass `mjcourse.envs`. Follow the course's conventions so the checker can inspect your environment: attributes `model`, `data`, `max_episode_steps` and `observation_sources`, and a method `_get_obs()`.

## Expected behaviour

The reference passes `mjcourse.capstone.check` in all three modes, in 0.1 to 0.2 s each. Its actions do what the docstring says:

- **End-effector deltas.** Ten steps at +1 in x move the tool 8.3 cm of the 10 cm commanded, with 0.4 mm of sideways and 0.6 mm of vertical drift. The step is 0.05 s and the joint tracking lags behind the target.
- **Joint targets.** Five steps at +1 on joint 1 move it 0.175 rad of the 0.25 rad commanded.
- **Torques.** A zero action holds the arm: the environment adds gravity compensation, so torque actions are what the policy adds on top. With the arm still and the puck untouched, the joints did not move at all over 20 steps.
- **Termination.** A puck placed on the goal ends the episode with `terminated=True, truncated=False` on the first step.

## Tests

```bash
MJC_IMPL=starter pytest projects/p10_gym_env
pytest projects/p10_gym_env
```

Ten tests:

- the full checker in each mode: Gymnasium's `check_env`, observations that are copies, truncation at the time limit, bit-identical replay from a seed, every source a real sensor, and no change in the observation when the puck's velocity, mass, friction or contact stiffness changes;
- the tool position equal to forward kinematics of the observed joint angles, at reset and after each step, in each mode;
- a reset after an episode giving the same observation as a fresh environment;
- different seeds giving different layouts;
- success that terminates rather than truncates;
- actions whose effect matches the docstring.

`python tools/mutate_project.py p10_gym_env` checks the seven mutants in `mutants.json`.

## Common failures

- **Stale observations.** There are two kinds. After `mj_resetData`, without `mj_forward`, the first observation puts the tool at the origin: `mj_resetData` zeroes the derived fields. After `mj_step`, without `mj_kinematics`, the tool position is the one from before the last substep, 0.42 mm behind at most in this environment. Neither breaks reproducibility, so `check_env` and the replay test pass. The forward-kinematics test catches both.
- **A misleading leak report.** Before this project, the course's leak check took its baseline observation without refreshing the state. A stale observation therefore changed after its `mj_forward`, and all four perturbations were reported as leaks. `mjcourse.envs.checks.perturbation_leaks` now calls `mj_forward` first, so staleness is reported only by the test that names it.
- **Time limits reported as termination.** A value function then learns that the last state is terminal, which it is not. The truncation check catches it.
- **An observation buffer reused between steps.** Every stored observation changes when the next one is written. The copy check catches it.
- **Privileged observations.** These include the puck's velocity, whether declared honestly ("simulator state") or under a false label ("camera tracker"). The source check catches the first and the perturbation check the second.
- **Randomness outside `self.np_random`.** Two environments reset with the same seed differ. The replay test catches it.
- **Rewards that read privileged state.** Not tested here: a training reward may use simulator state the policy never sees, but you should be able to say which reward terms would survive on the real robot.

## Extension challenges

1. A vectorized version (`gymnasium.vector.AsyncVectorEnv` over 16 processes, started with `spawn`); measure steps per second against the single environment.
2. Add an RGB observation from the `overview` camera, with its source declared, and make the checker accept it.
3. Add actuator delay and observation noise, both seeded, and confirm that replay is still bit-identical.

## Solution

`solution.py`, about 140 lines.
