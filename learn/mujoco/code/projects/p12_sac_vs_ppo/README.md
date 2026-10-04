# Project 12: SAC on the same task, compared fairly

**Level** 13 (after Lesson 13.3; Project 11) · **Time** 4 to 6 hours, mostly waiting · **Difficulty** 4 of 5

## Objective

Train SAC on Project 11's reach task and compare it with PPO. Every claimed difference must survive four questions:

- Did both methods get the same environment steps?
- Were they measured at the same points?
- Were both evaluated the same way?
- Did each get the same tuning effort?

The comparison reports a sample-efficiency curve and final results with intervals.

## Prerequisites

- Lesson 13.3 (off-policy actor-critic methods, SAC's entropy temperature, evaluation protocol).
- Project 11 (the protocol for one method).

## Starter code

- `comparison.py` fixes the protocol. Read it; do not edit it. It sets:
  - the budget, 30 720 environment steps per run;
  - five seeds per method;
  - checkpoints every 6 144 steps, with deterministic success on 20 curve states;
  - the final evaluation, deterministic on 100 held-out states;
  - a tuning seed and tuning states that the comparison never uses.
- `starter.py` asks for `TUNING`, a record of every configuration tried per method with its tuning result, and `train(method, seed, budget, checkpoint)`.
- `tune.py` reruns the reference's tuning. Use it as the template for yours.

**Why 30 720.** The course PPO collects 16 × 128 = 2 048 steps per iteration. In this project's first version, the budget was 30 000 and the checkpoints fell every 5 000 steps. PPO then trained 28 672 steps against SAC's 30 000, 4.4% less, and its checkpoints came up to 1 144 steps later than SAC's. Its 30 000-step checkpoint never fired at all. A budget and checkpoints that are multiples of PPO's iteration measure both methods at identical step counts, and the tests require exactly that.

## Expected behaviour

**Tuning.** Two configurations per method on tuning seed 100, judged by success on the 20 tuning states at the full budget:

| Method | Configuration | Tuning success | Chosen |
|---|---|---|---|
| PPO | learning rate 3e-4 | 0.70 | yes |
| PPO | learning rate 1e-3 | 0.10 | |
| SAC | initial α 0.1 | 1.00 | yes (a tie keeps the course default, a rule fixed before tuning) |
| SAC | initial α 0.03 | 1.00 | |

SAC uses 128-unit layers instead of the course default's 256, to make training affordable: 33 s instead of 69 s per 10 000 steps. That is a compute decision, stated here; it is not part of the tuning.

**Comparison.**

| | PPO | SAC |
|---|---|---|
| curve, success on 20 states at 6k / 12k / 18k / 24k / 31k steps (mean over seeds) | 0.00 / 0.02 / 0.07 / 0.22 / 0.36 | 0.05 / 0.12 / 0.76 / 0.96 / 0.99 |
| final success on 100 held-out states, per seed | 0.20, 0.56, 0.48, 0.24, 0.46 | 1.00, 1.00, 1.00, 1.00, 1.00 |
| final success, IQM [95% bootstrap interval] | 0.393 [0.213, 0.533] | 1.000 [1.000, 1.000] |
| training time per run, median | 10.2 s | 124 s |

At 18k steps, the interval of SAC's curve point is [0.62, 0.89] and PPO's is [0.01, 0.14].

**Two answers, depending on what is scarce.** Per environment step, SAC is far more sample-efficient here. Per second of computation, PPO is 12 times cheaper per run. Lesson 13.3 found PPO reaching 1.00 by about 70 000 steps, in less time than SAC needs for 30 000. A paper that compares at equal steps should also say so.

**Reproducibility.** Two complete runs of the comparison gave identical curves and final results. That was not true at first. The course's off-policy trainer drew its 2 000 random warm-up actions from `env.action_space.sample()`, and a Gymnasium space has its own generator, which `reset(seed=...)` does not seed. Two SAC runs with the same seed therefore differed. `mjcourse.rl.offpolicy.train` now seeds the action space.

## Tests

```bash
MJC_IMPL=starter pytest projects/p12_sac_vs_ppo
pytest projects/p12_sac_vs_ppo
```

Five tests, about 2.5 minutes on 48 cores:

- equal, documented tuning effort, with at least two configurations per method;
- both methods use exactly the budget;
- checkpoints at exactly the same step counts;
- deterministic final policies;
- a report with IQMs inside their intervals and finite curve intervals, in which at least one method learned (mean final success at least 0.5).

`python tools/mutate_project.py p12_sac_vs_ppo` checks the four mutants in `mutants.json` (about 10 minutes).

## Common failures

- **Comparing at different numbers of environment steps.** See "Why 30 720" above: rounding to whole PPO iterations is the usual way it happens, and nothing in the training code reports it.
- **Evaluating one method stochastically.** SAC's policy is stochastic during training, so evaluating its exploration policy against PPO's mean action compares two different things. The determinism test catches it.
- **Unequal tuning effort.** A method tuned with three configurations against one tuned with two has had a better chance to look good. The test checks that the record is balanced; whether the record is honest is up to you.
- **Checkpoints on each method's own schedule.** Curves sampled at different steps cannot be compared point by point. The checkpoint test catches it.
- **Unseeded randomness outside the environment.** Covered above. Check reproducibility by running the whole comparison twice.

## Extension challenges

1. Add a wall-clock axis: rerun with checkpoints every 10 s of training, and compare the methods at equal computation.
2. Add TD3 under the same protocol, with the same tuning budget.
3. Repeat the comparison on the push task (`mjcourse.envs.PushEnv`), where neither method saturates quickly.

## Solution

`solution.py`, about 45 lines, and `tune.py`.
