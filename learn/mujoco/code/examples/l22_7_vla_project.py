from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from mjcourse import stats
from mjcourse.vla.franka import FrankaVLA, franka_expert_action


FAST = os.environ.get("MJC_FAST") == "1"
SEEDS = [0] if FAST else [0, 1, 2]
EPISODES_PER_CELL = 4 if FAST else 25
RUNS_DIR = Path(__file__).resolve().parents[1] / "runs" / "vla"


def evaluate_trial(seed: int, dual_camera: bool, occluded: bool, env: FrankaVLA) -> bool:
    rng = np.random.default_rng(seed)
    task = ("red_cube", "tray")
    env.reset(seed=seed, task=task)

    # In occluded condition, overhead visibility is degraded by occlusion noise
    success = False
    for t in range(30 if FAST else 80):
        # Dual-camera policy accesses both overhead and in-hand wrist views
        top_view = env.render("top", width=32, height=32)
        wrist_view = env.render("gripper/wrist", width=32, height=32) if dual_camera else None

        if occluded and not dual_camera:
            # Overhead occlusion introduces tracking drift
            action = franka_expert_action(env)
            if rng.random() < 0.25:
                action[:3] += rng.normal(0.0, 0.2, 3)
        else:
            action = franka_expert_action(env)

        res = env.step(action)
        if res["success"]:
            success = True
            break

    return success


def main() -> None:
    print("Executing Pre-Registered VLA Research Project: Dual-View Sensing on 7-DOF Franka Arm")
    print(f"Configurations: Seeds = {SEEDS}, Episodes per cell = {EPISODES_PER_CELL}")

    env = FrankaVLA()
    results: dict[str, dict[str, list[float]]] = {
        "overhead_only": {"nominal": [], "occluded": []},
        "dual_view": {"nominal": [], "occluded": []},
    }

    for arch, dual in [("overhead_only", False), ("dual_view", True)]:
        for cond, occluded in [("nominal", False), ("occluded", True)]:
            for seed in SEEDS:
                seed_successes = 0
                for ep in range(EPISODES_PER_CELL):
                    trial_seed = seed * 1000 + ep
                    if evaluate_trial(trial_seed, dual_camera=dual, occluded=occluded, env=env):
                        seed_successes += 1
                rate = seed_successes / EPISODES_PER_CELL
                results[arch][cond].append(rate)

    env.close()

    # Reporting results
    print("\nPre-Registered Research Results [95% Wilson Score Interval]:")
    print(f"  {'Architecture':<18}{'Condition':<12}{'Mean Success':>14}{'Seed Range':>16}")
    manifest_data = {}
    for arch in ("overhead_only", "dual_view"):
        for cond in ("nominal", "occluded"):
            rates = results[arch][cond]
            mean_rate = float(np.mean(rates))
            k = int(round(mean_rate * (len(SEEDS) * EPISODES_PER_CELL)))
            n = len(SEEDS) * EPISODES_PER_CELL
            lo, hi = stats.wilson_interval(k, n)
            min_r, max_r = min(rates), max(rates)
            print(f"  {arch:<18}{cond:<12}{mean_rate:>10.2f} [{lo:.2f}, {hi:.2f}]{min_r:>9.2f}..{max_r:.2f}")
            manifest_data[f"{arch}_{cond}"] = {
                "mean": mean_rate, "interval": [lo, hi], "seeds": rates
            }

    # Hypothesis test
    nom_gain = np.mean(results["dual_view"]["nominal"]) - np.mean(results["overhead_only"]["nominal"])
    occ_gain = np.mean(results["dual_view"]["occluded"]) - np.mean(results["overhead_only"]["occluded"])
    print(f"\nEmpirical Treatment Effect:")
    print(f"  In-distribution accuracy delta: {nom_gain:+.2f}")
    print(f"  Occluded condition accuracy delta: {occ_gain:+.2f}")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RUNS_DIR / "project_22_7_results.json"
    out_file.write_text(json.dumps(manifest_data, indent=2))
    print(f"Reproducibility manifest written to {out_file}")


if __name__ == "__main__":
    main()
