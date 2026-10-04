# Project 11: PPO on a manipulation task

**Level** 13 (after Lessons 13.2 and 13.3) · **Time** 3 to 5 hours, mostly waiting · **Difficulty** 3 of 5

## Objective

Train PPO on the reach task and report the result the way a paper should: five training seeds, each evaluated deterministically on 100 initial states that training never used, summarized as an interquartile mean with a bootstrap interval. Add one ablation with exactly the same budget, and say what it changed. The algorithm can be the course's (`mjcourse.rl.ppo`) or your own; the experiment is what this project grades.

## Prerequisites

- Lesson 13.2 (PPO: the clipped surrogate, GAE, bootstrapping at truncation).
- Lesson 13.3 (deterministic held-out evaluation, seeds as the unit of replication, IQM, intervals, metrics that still discriminate when success saturates).

## Starter code

- `rl_protocol.py` fixes the task (`ReachEnv`, joint-delta actions), the budget (100 000 steps), the seeds (0 to 4), the held-out states (reset seeds 10 000 to 10 099), the evaluation and the report. Read it; do not edit it.
- `starter.py` asks for `ABLATION`, a sentence, and `train(seed, variant, budget)`, which returns `(act, steps)`.

The tests train all ten runs in parallel processes: about 45 s on 48 cores.

## Expected behaviour

The reference trains the course's PPO (16 environments, 128 steps each per iteration, so 100 000 steps become 48 iterations and 98 304 steps). It ablates PPO's central mechanism, the clipping, by raising the clip range from 0.2 to 10. That leaves ten epochs of unconstrained updates on each batch.

| Measure | Main (clip 0.2) | Ablation (clip 10) | Main − ablation, by seed |
|---|---|---|---|
| held-out success, per seed | 1.00, 1.00, 1.00, 1.00, 1.00 | 0.93, 1.00, 0.74, 0.91, 0.96 | |
| success, IQM [95% interval] | 1.000 [1.000, 1.000] | 0.933 [0.797, 0.987] | +0.092 [+0.028, +0.182] (mean) |
| steps per episode, IQM | 8.53 [8.38, 8.83] | 14.3 [9.7, 31.5] | −9.6 [−20.3, −2.6] (mean) |
| final distance (m), mean | 0.015 | 0.019 | −0.004 [−0.007, −0.001] |

On seed 0, the ablation's KL divergence between successive policies was 0.27 per iteration in the last iteration, against 0.011 with clipping.

Read the table with three things in mind:

- **Success saturates for the main run.** All five seeds reach 1.00, so the steps per episode and the final distance carry the comparison.
- **The ablation's spread is the finding.** One seed is untouched (1.00) and another drops to 0.74. Reporting each variant's best seed would show 1.00 against 1.00.
- **Five-seed percentile bootstrap intervals are rough.** They undercover at this sample size. Lesson 13.3 showed an interval over 2 seeds narrower than one over 5, which is the same defect. Report the per-seed values beside them, as here.

## Tests

```bash
MJC_IMPL=starter pytest projects/p11_ppo_reach
pytest projects/p11_ppo_reach
```

Five tests:

- the ablation is declared;
- the main runs' mean held-out success over five seeds is above 90%;
- both variants used the same number of steps for each seed, between 90% and 100% of the budget;
- `act` is deterministic and does not change after seeing other observations;
- the report holds an IQM inside its interval for both variants.

`python tools/mutate_project.py p11_ppo_reach` checks the three mutants in `mutants.json` (about 3 minutes).

## Common failures

- **Evaluating stochastic actions.** Sampling from the policy at evaluation measures the exploration noise as well as the policy. The determinism test catches it.
- **Normalization statistics that learn from evaluation data.** If `act` updates the running mean and variance, the policy changes while it is being evaluated, and the result depends on the order of the evaluation states. The same test catches it: an observation seen first and seen again later gets a different action.
- **Unequal budgets.** The ablation with twice the steps answers a different question. The budget test compares the steps each run actually used, not the number it asked for: here 98 304 for a 100 000 request.
- **Reporting the best seed.** The protocol reports every seed, and the table shows why: the ablation's best seed equals the main run.
- **Bootstrapping at truncation as an ablation.** Treating time limits as terminal is a real bug class (Lesson 13.2), but on this task it changed little: 1.00 success and 8.9 against 8.7 steps per episode on seed 0. Episodes end on success long before the limit, so truncation is rare. An ablation should test something the task can show.

## Extension challenges

1. Measure where the time goes: simulation in the environment workers against learning in the main process, at 4, 16 and 32 environments.
2. Halve the budget until the main run's success no longer saturates, and repeat the comparison on success alone.
3. Replace the percentile bootstrap with a stratified bootstrap over seeds and states, and compare the interval widths.

## Solution

`solution.py`, about 10 lines: the experiment, not the algorithm, is the work.
