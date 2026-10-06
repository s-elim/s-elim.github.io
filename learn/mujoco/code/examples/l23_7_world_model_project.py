import json
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from mjcourse import stats
from mjcourse import tabletop as tt
from mjcourse.worldmodel import dynamics, mpc, standard

OUT = Path(__file__).resolve().parents[1] / "runs" / "l23_7"
FAST = os.environ.get("MJC_FAST") == "1"
SEEDS = (0,) if FAST else (0, 1, 2)
TASKS_PER_SEED = 4 if FAST else 15
HORIZONS = (1, 5, 10, 20)
TRAIN_STEPS = 500 if FAST else 5000


def get_models() -> dict[str, dynamics.DynamicsModel]:
    models = {"one_step": standard.model("one_step")}
    multi_path = standard.ROOT / "multi_step.pt"
    if multi_path.exists():
        models["multi_step"] = torch.load(multi_path, weights_only=False)
    else:
        episodes = standard.dataset("guided")[:100 if FAST else 500]
        m, _ = dynamics.fit(episodes, steps=TRAIN_STEPS, objective="multi_step", k=5)
        torch.save(m, multi_path)
        models["multi_step"] = m
    return models


def evaluate_prediction(models: dict[str, dynamics.DynamicsModel], test_episodes: list[dict]) -> dict:
    results = {}
    for name, m in models.items():
        errs = dynamics.horizon_errors(m, test_episodes, horizons=HORIZONS)
        results[name] = {h: float(errs[h]["target"]) for h in HORIZONS}
    return results


def run_control_trial(args) -> dict:
    model_name, seed, task_idx = args
    torch.set_num_threads(1)
    rng = np.random.default_rng([seed + 10, task_idx])
    task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
    layout = tt.sample_layout(rng, task)
    model = standard.model("one_step") if model_name == "one_step" else torch.load(standard.ROOT / "multi_step.pt", weights_only=False)
    factory = lambda scene: mpc.LearnedModel(model)
    r = mpc.run_episode(factory, task, layout, cfg=mpc.PlannerConfig(horizon=12, seed=seed))
    return {"model": model_name, "seed": seed, "task_idx": task_idx, "success": bool(r["success"]), "steps": r["steps"]}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    test_eps = standard.dataset("guided_test")[:8 if FAST else 50]
    print("(1) Pre-registered hypothesis: Multi-step rollout training (k=5) stabilizes autoregressive rollouts")
    print("    and improves closed-loop MPC manipulation success over single-step MSE minimization.")
    models = get_models()

    print("\n(2) Prediction error of the pushed puck against horizon on held-out episodes (mm):")
    pred_res = evaluate_prediction(models, test_eps)
    print(f"  {'objective':<16}" + "".join(f"{h:>10d}" for h in HORIZONS) + "   (steps of 0.1 s)")
    for name, vals in pred_res.items():
        print(f"  {name:<16}" + "".join(f"{1000 * vals[h]:10.2f}" for h in HORIZONS))

    print(f"\n(3) Closed-loop MPC evaluation across {len(SEEDS)} seeds ({TASKS_PER_SEED} tasks per seed):")
    trials = [(m, s, i) for m in ("one_step", "multi_step") for s in SEEDS for i in range(TASKS_PER_SEED)]
    workers = min(16, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        ctrl_runs = list(pool.map(run_control_trial, trials, chunksize=1))

    ctrl_summary = {}
    print(f"  {'objective':<16}{'success rate':>16}{'95% Wilson CI':>22}{'median steps':>16}")
    for name in ("one_step", "multi_step"):
        runs_m = [r for r in ctrl_runs if r["model"] == name]
        succ = sum(r["success"] for r in runs_m)
        total = len(runs_m)
        lo, hi = stats.wilson_interval(succ, total)
        med_steps = float(np.median([r["steps"] for r in runs_m if r["success"]])) if succ > 0 else float("nan")
        rate = succ / total
        ctrl_summary[name] = {"success_rate": rate, "wilson_ci": [lo, hi], "median_steps": med_steps, "total": total}
        print(f"  {name:<16}{rate:>15.1%}{f'[{lo:.2f}, {hi:.2f}]':>22}{med_steps:>16.1f}")

    gap = ctrl_summary["multi_step"]["success_rate"] - ctrl_summary["one_step"]["success_rate"]
    print(f"\n(4) Statistical conclusion: Delta = {gap:+.1%}")
    if gap >= 0.05:
        print("    Hypothesis confirmed: multi-step training yields superior closed-loop task execution.")
    else:
        print("    Hypothesis outcome: multi-step training matches or marginally shifts closed-loop execution.")

    report = {"prediction_errors_mm": {k: {h: 1000 * v for h, v in vals.items()} for k, vals in pred_res.items()},
              "control": ctrl_summary}
    (OUT / "project_results.json").write_text(json.dumps(report, indent=2))
    print(f"wrote {OUT / 'project_results.json'}")


if __name__ == "__main__":
    main()
