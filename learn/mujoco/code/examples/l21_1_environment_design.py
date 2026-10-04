"""Lesson 21.1: designing a research-grade environment, and three mistakes that invalidate results (Level 21).

INPUT   the point-mass task of Level 14 (start left of a round obstacle, stop within 4 cm of the goal and slower
        than 5 cm/s, within 6 s), its scripted expert, and behaviour cloning (mjcourse.il.bc)
PROCESS (0) a protocol written before running, and the record each run saves (mjcourse.experiment);
        (1) choosing on the evaluation set: 8 BC policies fitted on the same 20 demonstrations with different
            training seeds, scored on 50 development starts with random pushes (1 per second, Level 14); the best is
            then scored on 400 fresh starts with fresh pushes;
        (2) the success definition: the same policies, run for the full 6 s, scored as "stopped at the goal"
            (the task's definition), "within 4 cm at any moment", and "within 4 cm when time runs out";
        (3) a silent model change: the point mass's damping doubled in code after loading; the XML file's hash,
            the compiled model's fingerprint, and the expert's success before and after
OUTPUT  printed tables and a run record in ./runs/l21_1_record.json

Run:  python examples/l21_1_environment_design.py          (about 1 minute)
"""
# requires: torch

import json
import os

import mujoco
import numpy as np

from mjcourse import experiment, model_path
from mjcourse.il import bc, pointmass
from mjcourse.stats import wilson_interval

FAST = os.environ.get("MJC_FAST") == "1"
HELD_OUT = 100 if FAST else 400


def full_rollout(sim: pointmass.PointMass, policy, start: np.ndarray) -> np.ndarray:
    """(T, 4) states over the whole 6 s, without stopping at success."""
    m, d = sim.model, sim.data
    mujoco.mj_resetData(m, d)
    d.qpos[:] = start
    mujoco.mj_forward(m, d)
    states = []
    for _ in range(pointmass.MAX_STEPS):
        s = np.r_[d.qpos, d.qvel]
        d.ctrl[:] = np.clip(np.asarray(policy(s), dtype=float), -1.0, 1.0)
        mujoco.mj_step(m, d)
        states.append(np.r_[d.qpos, d.qvel])
    return np.array(states)


def definitions(states: np.ndarray) -> tuple[bool, bool, bool]:
    dist = np.linalg.norm(states[:, :2] - pointmass.GOAL, axis=1)
    speed = np.linalg.norm(states[:, 2:], axis=1)
    return bool(np.any((dist < 0.04) & (speed < 0.05))), bool(np.any(dist < 0.04)), bool(dist[-1] < 0.04)


def rate(flags) -> str:
    flags = list(flags)
    lo, hi = wilson_interval(int(sum(flags)), len(flags))
    return f"{np.mean(flags):.2f} [{lo:.2f}, {hi:.2f}]"


if __name__ == "__main__":
    protocol = experiment.Protocol(
        name="bc-held-out-starts",
        hypothesis="Behaviour cloning from 20 clean demonstrations, chosen among 8 training seeds on a development set, "
                   "succeeds in at least 0.6 of held-out episodes with random pushes (1 per second).",
        task="point mass: from the left of a round obstacle, stop at the goal on its right (Level 14)",
        initial_states="positions uniform in x [-0.40, -0.30] m, y [-0.25, 0.25] m, at rest",
        success="within 4 cm of the goal and slower than 5 cm/s at some step within 6 s (600 steps of 10 ms)",
        metric="success rate on 400 held-out starts with pushes and a 95% Wilson interval; the policy is chosen on "
               "50 separate development starts",
        train_seeds=(1,), eval_seeds=(2,),
        falsified_if="the held-out interval lies entirely below 0.6")
    print(f"MuJoCo {mujoco.__version__}; protocol '{protocol.name}' written before the runs")
    sim = pointmass.PointMass()
    held_out = pointmass.sample_starts(np.random.default_rng(2), HELD_OUT)
    print("(1) eight training seeds, one data set: success with pushes on 50 development starts and on fresh starts")
    train = pointmass.sample_starts(np.random.default_rng(1), 20)
    demos = [sim.rollout(pointmass.expert, s) for s in train]
    x, y = np.vstack([r.states for r in demos]), np.vstack([r.actions for r in demos])
    dev = pointmass.sample_starts(np.random.default_rng(3), 50)
    scores, results = [], {}
    for seed in range(2 if FAST else 8):
        policy, _ = bc.fit(x, y, steps=500 if FAST else 3000, seed=seed)
        d = pointmass.evaluate(policy, dev, push_rate=1.0, seed=11)["success"]
        f = pointmass.evaluate(policy, held_out, push_rate=1.0, seed=12)["success"]
        scores.append((d, f))
        print(f"    training seed {seed}: development {d:.2f}, fresh {f:.3f}")
    scores = np.array(scores)
    best = int(np.argmax(scores[:, 0]))
    results["selection"] = {"selected_seed": best, "dev": float(scores[best, 0]), "fresh": float(scores[best, 1]),
                            "fresh_mean": float(scores[:, 1].mean())}
    lo, hi = wilson_interval(round(scores[best, 1] * HELD_OUT), HELD_OUT)
    verdict = "falsified" if hi < 0.6 else "not falsified"
    print(f"    chosen on the development set: seed {best}, which scored {scores[best, 0]:.2f} there and {scores[best, 1]:.3f} on "
          f"{HELD_OUT} fresh starts; the fresh scores of all seeds range from {scores[:, 1].min():.3f} to {scores[:, 1].max():.3f} "
          f"(mean {scores[:, 1].mean():.3f})")
    print(f"    the protocol's test: held-out interval [{lo:.3f}, {hi:.3f}] against 0.6: hypothesis {verdict}")
    policies = {}
    for n in ((5, 80) if not FAST else (5,)):
        starts = pointmass.sample_starts(np.random.default_rng(1), n)
        runs = [sim.rollout(pointmass.expert, s) for s in starts]
        policies[n], _ = bc.fit(np.vstack([r.states for r in runs]), np.vstack([r.actions for r in runs]),
                                steps=500 if FAST else 3000)
    print("(2) the same policies over the full 6 s, three definitions of success on the held-out starts")
    print(f"    {'policy':<22}{'stopped at the goal':>24}{'reached at any time':>24}{'at the goal at 6 s':>24}")
    for label, policy in [("expert", pointmass.expert)] + [(f"BC, {n} demonstrations", p) for n, p in policies.items()]:
        flags = np.array([definitions(full_rollout(sim, policy, s)) for s in held_out])
        print(f"    {label:<22}" + "".join(f"{rate(flags[:, k]):>24}" for k in range(3)))
    print("(3) the model edited in code after loading")
    path = model_path("point_mass")
    model = sim.model
    before_fp = experiment.model_fingerprint(model)
    probe = policies[5]
    before = [np.mean([sim.rollout(pol, s).success for s in held_out]) for pol in (pointmass.expert, probe)]
    model.dof_damping[:] *= 2
    after_fp = experiment.model_fingerprint(model)
    after = [np.mean([sim.rollout(pol, s).success for s in held_out]) for pol in (pointmass.expert, probe)]
    print(f"    XML file sha256 {experiment.file_sha256(path)[:16]}... before and after (the file did not change)")
    print(f"    model fingerprint {before_fp[:16]}... before, {after_fp[:16]}... after")
    print(f"    success on the held-out starts before and after doubling the damping: expert {before[0]:.2f} -> {after[0]:.2f}, "
          f"BC from 5 demonstrations {before[1]:.3f} -> {after[1]:.3f}")
    model.dof_damping[:] /= 2
    record = experiment.run_record(protocol, {"point_mass": (model, path)}, {"bc_steps": 3000, "held_out": HELD_OUT, "push_rate": 1.0}, results)
    out = experiment.save(record, "runs/l21_1_record.json")
    print(f"(0) run record written to {out}: keys {list(record)}")
    print("    " + json.dumps({k: record["software"][k] for k in ("mujoco", "numpy", "torch")}))
    print("    " + json.dumps({k: v for k, v in record["models"]["point_mass"].items() if k != "file_sha256"})[:120] + "...")
