A MuJoCo experiment is a measurement of a model, and it supports a claim only as far as its design does. This page is the course's checklist for designing one, a complete small experiment run end to end, and the mistakes that most often invalidate simulation results. Level 21 extends it to full benchmarks.

## The design, written before any code runs

| Item | Write down | The question it answers for a reviewer |
|---|---|---|
| Research question | one sentence | What would we know afterwards that we do not know now? |
| Hypothesis | a directional prediction with its mechanism | Why do you expect the effect? |
| Falsifier | the result that would refute the hypothesis | Could the experiment have come out against you? |
| Conditions and baseline | what varies; the strongest reasonable alternative | Is the comparison fair? |
| Controlled variables | everything held fixed: model file, MuJoCo version, timestep, integrator, contact options, controller gains | Is the difference due to the factor alone? |
| Initial-state distribution | ranges and the generator with its seed | Is the result about one state or a population? |
| Train and evaluation split | which states, objects, instructions, seeds were used for tuning and which for the reported numbers | Was the evaluation seen during development? |
| Metric | exact definition (thresholds, timing, aggregation) | Can someone else compute the same number? |
| Sample size | episodes and seeds, chosen from the interval width you need | Is the result distinguishable from noise? |
| Statistical reporting | intervals and the test, chosen in advance | How sure are you? |
| Ablations | one factor removed at a time | Which part of the method matters? |
| Failure analysis | how failures will be categorized | Where does the method break, and why? |
| Reproducibility record | versions, seeds, configs, code revision | Can it be rerun? |

> [!recommendation] Write the falsifier first
> The most useful line in the table is the falsifier, because it forces the metric, the comparison and the threshold to be fixed before the data exists. An experiment whose every outcome would be reported as support is not testing anything.

## A complete small experiment

**Question.** On the course's gantry gripper, does a slower lift raise grasp-and-lift success when the grasp is imperfect?
**Hypothesis.** A 1.5 s lift succeeds more often than a 0.15 s lift, because the cube's inertial load during a fast lift exceeds the friction budget of an off-centre grasp (Lesson 10.1's mechanism, previewed in Lesson 2.3's lab).
**Falsifier.** A paired difference whose 95% interval includes zero, or lies below it.
**Design.** 200 initial states drawn once from a seeded generator (cube offset $\pm$18 mm and $\pm$12 mm, yaw $\pm$0.6 rad, mass 0.05 to 0.6 kg); both conditions run on every state (a **paired** design, which removes the variance between states from the comparison); everything else fixed. Success: the cube's centre above 0.2 m, 0.5 s after the lift ends.

```io
INPUT: `gantry_gripper.xml`; 200 initial states from seed 2026
PROCESS: run each state under both lift durations; compute intervals, the paired difference, a breakdown by mass; reproduce two evaluation mistakes; write a manifest
OUTPUT: printed results and `runs/research_mode/manifest.json`
```

```python file=examples/research_mode_experiment.py
"""Research mode: a small, complete experiment on the gantry gripper.

Question   Does a slower lift raise grasp-and-lift success when the grasp is imperfect?
Hypothesis A 1.5 s lift succeeds more often than a 0.15 s lift, because the cube's
           inertial load during a fast lift exceeds the grasp's friction budget.
Falsifier  A paired difference whose 95% interval includes zero (or is negative).

INPUT   gantry_gripper.xml; 200 initial states drawn once from a seeded generator:
        cube offset from the grasp centre (x +-18 mm, y +-12 mm), yaw +-0.6 rad,
        mass 0.05 to 0.6 kg
PROCESS run every initial state under both lift durations (a paired design: the two
        conditions see identical states); success = cube above 0.2 m, 0.5 s after the lift
OUTPUT  success rates with Wilson intervals, the paired difference with a bootstrap
        interval, a failure breakdown by mass, two common evaluation mistakes
        reproduced, and runs/research_mode/manifest.json with everything needed to rerun

Run:  python examples/research_mode_experiment.py
"""

import json
import os
import platform
from pathlib import Path

import mujoco
import numpy as np

from mjcourse import model_path, stats

SEED = 2026
N_STATES = 60 if os.environ.get("MJC_FAST") == "1" else 200
LIFTS = {"fast (0.15 s)": 0.15, "slow (1.5 s)": 1.5}
OUT = Path(__file__).resolve().parents[1] / "runs" / "research_mode"


def initial_states(seed: int, n: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.column_stack([rng.uniform(-0.018, 0.018, n), rng.uniform(-0.012, 0.012, n),
                            rng.uniform(-0.6, 0.6, n), rng.uniform(0.05, 0.6, n)])


def episode(model: mujoco.MjModel, state: np.ndarray, lift_time: float) -> bool:
    dx, dy, yaw, mass = state
    cube = model.body("cube").id
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    model.body_mass[cube] = mass                       # inertia left as compiled: a mass-only randomization
    mujoco.mj_setConst(model, data)
    data.qpos[5:8] = [0.12 + dx, dy, 0.02]
    data.qpos[8:12] = [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
    data.ctrl[:] = [0.12, 0, 0, 0.04]

    def run(seconds: float) -> None:
        for _ in range(round(seconds / model.opt.timestep)):
            mujoco.mj_step(model, data)

    run(0.3)
    for k in range(100):                               # descend over 1 s
        data.ctrl[2] = -0.33 * (k + 1) / 100
        run(0.01)
    run(0.3)
    data.ctrl[3] = 0.0                                 # close
    run(0.6)
    steps = max(1, round(lift_time / 0.01))
    for k in range(steps):                             # lift 0.33 m over lift_time
        data.ctrl[2] = -0.33 + 0.33 * (k + 1) / steps
        run(lift_time / steps)
    run(0.5)
    return bool(data.xpos[cube][2] > 0.2)


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("gantry_gripper")))
    states = initial_states(SEED, N_STATES)
    results = {name: np.array([episode(model, s, t) for s in states]) for name, t in LIFTS.items()}

    print(f"{N_STATES} initial states (seed {SEED}), MuJoCo {mujoco.__version__}")
    for name, ok in results.items():
        lo, hi = stats.wilson_interval(int(ok.sum()), len(ok))
        print(f"  {name:<14s} success {ok.mean():.3f}  95% Wilson [{lo:.3f}, {hi:.3f}]")
    slow, fast = results["slow (1.5 s)"], results["fast (0.15 s)"]
    est, lo, hi = stats.paired_difference_ci(slow.astype(float), fast.astype(float), seed=SEED)
    print(f"  paired difference slow - fast: {est:+.3f}  95% bootstrap [{lo:+.3f}, {hi:+.3f}]")
    print(f"  states where only slow succeeds: {int(np.sum(slow & ~fast))}, only fast: {int(np.sum(fast & ~slow))}")

    print("failure analysis, success by cube mass:")
    bins = [(0.05, 0.23), (0.23, 0.42), (0.42, 0.6)]
    for a, b in bins:
        sel = (states[:, 3] >= a) & (states[:, 3] < b + 1e-9)
        print(f"  mass {a:.2f}-{b:.2f} kg (n={sel.sum():3d}): fast {fast[sel].mean():.2f}, slow {slow[sel].mean():.2f}")

    print("mistake 1, evaluating on one fixed initial state (the nominal one):")
    nominal = np.array([0.0, 0.0, 0.0, 0.1])
    for name, t in LIFTS.items():
        print(f"  {name:<14s} success on the nominal state: {episode(model, nominal, t)}")
    print("mistake 2, ten episodes instead of", N_STATES)
    for name, ok in results.items():
        lo, hi = stats.wilson_interval(int(ok[:10].sum()), 10)
        print(f"  {name:<14s} first 10 states: {ok[:10].mean():.1f}  95% Wilson [{lo:.2f}, {hi:.2f}]")

    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "question": "Does a slower lift raise grasp-and-lift success under grasp misalignment?",
        "mujoco": mujoco.__version__, "numpy": np.__version__, "python": platform.python_version(),
        "model": "gantry_gripper.xml", "timestep": model.opt.timestep, "integrator": int(model.opt.integrator),
        "cone": int(model.opt.cone), "impratio": model.opt.impratio,
        "seed": SEED, "n_states": N_STATES,
        "randomization": {"dx_m": [-0.018, 0.018], "dy_m": [-0.012, 0.012], "yaw_rad": [-0.6, 0.6], "mass_kg": [0.05, 0.6]},
        "success": "cube centre above 0.2 m, 0.5 s after the lift ends",
        "results": {k: {"successes": int(v.sum()), "n": len(v)} for k, v in results.items()},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"wrote {OUT / 'manifest.json'}")


if __name__ == "__main__":
    main()
```
Output, about 8 s of compute:

```text
200 initial states (seed 2026), MuJoCo 3.14.0
  fast (0.15 s)  success 0.495  95% Wilson [0.426, 0.564]
  slow (1.5 s)   success 0.885  95% Wilson [0.833, 0.922]
  paired difference slow - fast: +0.390  95% bootstrap [+0.320, +0.460]
  states where only slow succeeds: 78, only fast: 0
failure analysis, success by cube mass:
  mass 0.05-0.23 kg (n= 47): fast 0.91, slow 0.98
  mass 0.23-0.42 kg (n= 65): fast 0.72, slow 0.78
  mass 0.42-0.60 kg (n= 88): fast 0.10, slow 0.91
mistake 1, evaluating on one fixed initial state (the nominal one):
  fast (0.15 s)  success on the nominal state: True
  slow (1.5 s)   success on the nominal state: True
mistake 2, ten episodes instead of 200
  fast (0.15 s)  first 10 states: 0.7  95% Wilson [0.40, 0.89]
  slow (1.5 s)   first 10 states: 1.0  95% Wilson [0.72, 1.00]
wrote .../runs/research_mode/manifest.json
```

**Reading the result.** The hypothesis survives its falsifier: the paired difference is +39 points with an interval of [+32, +46], far from zero, and the paired table shows no state where the fast lift succeeded and the slow one failed. The failure breakdown supports the proposed mechanism, because the gap is concentrated where the inertial load is largest: above 0.42 kg, 10% for the fast lift against 91% for the slow one. The middle mass band shows a smaller residual failure rate under both conditions, which the mass alone does not explain and which a follow-up would examine by offset and yaw.

> [!research] What this experiment does not show
> It shows that, in this simulated gripper with these contact parameters and this controller, lift speed matters for heavy, off-centre cubes. It does not show the size of the effect on a real gripper, whose friction, compliance and servo bandwidth differ (Lesson 0.3), and it says nothing about lift durations between 0.15 and 1.5 s. Note also that the seeded draw happens to contain more heavy cubes than a uniform draw would on average (88 of 200 in the top third, where 65 would be expected): the per-band rates are unaffected, but the pooled rates depend on the mass distribution. Report pooled rates together with the distribution they were pooled over.

The two "mistakes" at the end of the output are the commonest ways this result could have been missed or overstated:

- **Evaluating on the nominal state.** Both conditions succeed on the centred, light, unrotated cube. An evaluation that always starts from the same state measures one point of the distribution; here it would have reported no difference.
- **Ten episodes.** The first ten states give 70% and 100%, with intervals [0.40, 0.89] and [0.72, 1.00] that overlap. The conclusion would rest on noise, and in either direction.

## How many episodes

For a success rate near $p$ and a target 95% half-width $w$, the normal approximation gives $n \approx 1.96^2\,p(1-p)/w^2$. The worst case is $p = 0.5$:

| Half-width | 10 points | 5 points | 3 points | 2 points |
|---|---:|---:|---:|---:|
| Episodes (worst case) | 97 | 385 | 1068 | 2401 |

`mjcourse.stats.episodes_for_halfwidth` computes this. For a *difference* between two methods, a paired design on shared initial states needs far fewer episodes than two independent samples, because the variation between states cancels; the worked example detects a 39-point difference with 200 pairs, with room to spare.

> [!established] Intervals used in this course
> Success rates are reported with **Wilson** score intervals (`stats.wilson_interval`), which keep sensible width at 0% and 100% and for small samples, unlike the textbook normal interval. Differences and non-binary metrics use **percentile bootstrap** intervals (`stats.bootstrap_ci`, `stats.paired_difference_ci`). Results over training seeds use the **interquartile mean** with a bootstrap interval (`stats.iqm`), following the recommendation of Agarwal and colleagues for reinforcement-learning evaluation ([arXiv:2108.13264](https://arxiv.org/abs/2108.13264)).

## Aggregation is part of the metric

A benchmark with several tasks has two different "overall success rates": the mean over episodes (tasks with more episodes weigh more) and the mean over tasks of each task's rate (every task weighs the same). With 8 episodes of an easy task all succeeding and 2 of a hard task all failing, the first is 80% and the second 50%. Neither is wrong; mixing them across papers is. State which one you report, and report per-task rates alongside.

## Mistakes that invalidate simulation results

**Training and evaluating on identical initial states.** A policy tuned or trained on the evaluation states has memorized them. Hold out evaluation states (and objects, instructions, layouts) and never touch them during development. Generate them from a separate seed.

**Privileged information leakage.** A policy that receives object poses, contact flags or simulator internals that the real robot does not have can succeed for reasons that do not transfer. List every observation component with its real-world source; anything without a source is privileged. A test that fails when the observation contains a simulator-only quantity is cheap (Level 12.2).

**Reward and success definitions that can be gamed.** A reward for "cube height" can be maximized by flinging the cube; a success test that checks height once can be passed by a cube in flight. Check success after a hold period, as the worked example does, and watch rollouts of high-reward episodes.

**Unfair baselines.** A new method tuned for weeks against a baseline run with defaults measures tuning effort. Give baselines the same tuning budget, the same observation and action spaces, and the same number of training samples, or report the asymmetry.

**Improper randomization.** Randomizing a parameter outside its physical range, or randomizing something that changes the task (an object too heavy for the gripper to lift at all), inflates difficulty without testing robustness. Randomize within identified or measured ranges, and check that every randomized task remains solvable.

**Simulator-specific overfitting.** A method can exploit an approximation: slow slip (Lesson 0.3), soft-contact penetration, a missing collision. Test the result's sensitivity to the simulator: timestep, integrator, contact parameters, and, where possible, a second simulator.

**Insufficient seeds.** Learning results vary across training seeds, sometimes more than across methods. Use at least 3 seeds for a development decision and 5 to 10 for a reported result, and report the spread, not the best seed.

**Reporting only successes.** A video of a success shows that success is possible, not how often. Report rates with intervals, and show failures with the same care as successes: a failure taxonomy is often the most informative table in a paper.

## A reporting template

> **Setup.** MuJoCo 3.14.0, `<model>`, timestep `<h>` s, `<integrator>`, `<cone>` cones with impratio `<x>`; contact parameters `<defaults or listed>`. Initial states: `<distribution>`, `<n>` states from seed `<s>`, disjoint from the `<m>` development states (seed `<s'>`).
> **Metric.** `<exact definition>`; reported as `<per-episode / per-task>` mean with 95% Wilson intervals; differences with paired bootstrap intervals (10 000 resamples).
> **Results.** `<table>`; per-condition failure categories in `<table>`.
> **Reproduction.** `<repository and commit>`; command `<...>`; manifest with all of the above attached.

The worked example's `manifest.json` follows this template and is written automatically by the script.
