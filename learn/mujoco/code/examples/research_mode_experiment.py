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
