import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from mjcourse import stats
from mjcourse import tabletop as tt
from mjcourse.worldmodel import dynamics, mpc, standard

OUT = Path(__file__).resolve().parents[1] / "runs" / "l23_5"
FAST = os.environ.get("MJC_FAST") == "1"
MODELS = {"guided": "one_step", "small": "small_data", "random": "random_data"}
PLAN_HORIZONS = (4, 8, 12, 20)
TASKS = 6 if FAST else 30
PRED_HORIZONS = (1, 5, 10, 20, 50)


def task_and_layout(i: int):
    rng = np.random.default_rng([5, i])
    task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
    return task, tt.sample_layout(rng, task)


def control(args) -> dict:
    name, horizon, i = args
    torch.set_num_threads(1)
    task, layout = task_and_layout(i)
    cfg = mpc.PlannerConfig(horizon=horizon)
    if name == "MuJoCo":
        factory = lambda scene: mpc.MujocoModel(scene)
    else:
        model = standard.model(MODELS[name])
        factory = lambda scene: mpc.LearnedModel(model)
    r = mpc.run_episode(factory, task, layout, cfg=cfg)
    i_t = 4 + 4 * tt.OBJECTS.index(task[0])
    states, zone = r["states"], np.array(tt.ZONES[task[1]])
    gap = np.linalg.norm(states[:, 0:2] - states[:, i_t:i_t + 2], axis=1).min() - tt.PUCK_RADIUS - tt.PUSHER_RADIUS
    progress = np.linalg.norm(states[0, i_t:i_t + 2] - zone) - np.linalg.norm(states[-1, i_t:i_t + 2] - zone)
    return {"model": name, "horizon": horizon, "i": i, "success": bool(r["success"]), "touched": bool(gap < 0.003),
            "progress": float(progress)}


def exploitation(args) -> list[tuple[float, float]]:
    name, i = args
    torch.set_num_threads(1)
    task, layout = task_and_layout(i)
    scene = tt.Tabletop()
    scene.reset(layout)
    planner = mpc.Planner(mpc.LearnedModel(standard.model(MODELS[name])), task, mpc.PlannerConfig(horizon=12))
    truth = mpc.MujocoModel(scene)
    i_t, zone = 4 + 4 * tt.OBJECTS.index(task[0]), np.array(tt.ZONES[task[1]])
    pairs = []
    for _ in range(tt.EPISODE_STEPS):
        state = scene.state()
        a = planner.act(state)
        best = planner.last["best"]
        chosen = planner.last["actions"][best:best + 1]
        start = np.linalg.norm(state[i_t:i_t + 2] - zone)
        predicted = start - np.linalg.norm(planner.last["states"][best, -1, i_t:i_t + 2] - zone)
        true = start - np.linalg.norm(truth.predict(state, chosen)[0, -1, i_t:i_t + 2] - zone)
        pairs.append((float(predicted), float(true)))
        scene.step(a)
        if scene.success(task):
            break
    scene.close()
    return pairs


def one_step_error(model, episodes) -> float:
    s = np.concatenate([e["states"][:-1] for e in episodes])
    a = np.concatenate([e["actions"] for e in episodes])
    s2 = np.concatenate([e["states"][1:] for e in episodes])
    with torch.no_grad():
        p = model(torch.as_tensor(s), torch.as_tensor(a)).numpy()
    idx = [0, 1, 4, 5, 8, 9, 12, 13]
    return float(np.linalg.norm((p - s2)[:, idx].reshape(-1, 4, 2), axis=-1).mean())


def figure(errors: dict, success: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.8), constrained_layout=True)
    colours = {"guided": "#0072B2", "small": "#E69F00", "random": "#D55E00"}
    for name, err in errors.items():
        ax1.plot(PRED_HORIZONS, [1000 * err[h]["target"] for h in PRED_HORIZONS], marker="o", color=colours[name], label=name)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("prediction horizon (steps of 0.1 s)")
    ax1.set_ylabel("open-loop error of the pushed puck (mm)")
    ax1.grid(alpha=0.3, which="both")
    ax1.legend(frameon=False)
    ax1.set_title("prediction error on held-out data", fontsize=10)
    for name in ("MuJoCo", "guided", "small", "random"):
        y = [success[(name, h)] for h in PLAN_HORIZONS]
        kw = {"color": "#000000", "marker": "s", "mfc": "none"} if name == "MuJoCo" else {"color": colours[name], "marker": "o"}
        ax2.plot([h * 0.1 for h in PLAN_HORIZONS], y, **kw, label=name)
    ax2.set_xlabel("planning horizon (s)")
    ax2.set_ylabel("MPC success rate")
    ax2.set_ylim(-0.05, 1.05)
    ax2.grid(alpha=0.3)
    ax2.legend(frameon=False)
    ax2.set_title("control success against planning horizon", fontsize=10)
    fig.savefig(OUT / "horizons.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    models = {k: standard.model(v) for k, v in MODELS.items()}
    guided_test, random_test = standard.dataset("guided_test"), standard.dataset("random_test")
    print("(1) one-step error on held-out transitions (mm)")
    print(f"  {'model':<12}{'random test':>16}{'guided test':>16}")
    for name, m in models.items():
        print(f"  {name:<12}{1000 * one_step_error(m, random_test):>16.2f}{1000 * one_step_error(m, guided_test):>16.2f}")
    pred_errors = {name: dynamics.horizon_errors(m, guided_test, PRED_HORIZONS) for name, m in models.items()}
    print(f"(2) open-loop error of the pushed puck against horizon (mm)")
    print(f"  {'model':<12}" + "".join(f"{h:>9d}" for h in PRED_HORIZONS) + "   (steps of 0.1 s)")
    for name, err in pred_errors.items():
        print(f"  {name:<12}" + "".join(f"{1000 * err[h]['target']:9.1f}" for h in PRED_HORIZONS))
    with ProcessPoolExecutor(min(32, os.cpu_count() or 1), mp_context=multiprocessing.get_context("spawn")) as pool:
        runs = list(pool.map(control, [(m, h, i) for m in ("MuJoCo", "guided", "small", "random") for h in PLAN_HORIZONS
                                       for i in range(TASKS)]))
        expl = {name: list(pool.map(exploitation, [(name, i) for i in range(TASKS)])) for name in MODELS}
    print(f"(3) MPC success against planning horizon, {TASKS} tasks per cell [95% Wilson interval]")
    print(f"  {'model':<12}" + "".join(f"{f'H = {h * 0.1:.1f} s':>22}" for h in PLAN_HORIZONS))
    success_by_cell = {}
    for name in ("MuJoCo", "guided", "small", "random"):
        cells = []
        for h in PLAN_HORIZONS:
            k = sum(r["success"] for r in runs if r["model"] == name and r["horizon"] == h)
            lo, hi = stats.wilson_interval(k, TASKS)
            cells.append(f"{k / TASKS:.2f} [{lo:.2f}, {hi:.2f}]")
            success_by_cell[(name, h)] = k / TASKS
        print(f"  {name:<12}" + "".join(f"{c:>22}" for c in cells))
    print(f"(4) model exploitation at planning horizon 12: predicted against true progress (m) per decision")
    print(f"  {'model':<12}{'decisions':>12}{'mean predicted':>16}{'mean true':>14}{'true < predicted':>18}")
    for name in MODELS:
        flat = [p for ep in expl[name] for p in ep]
        pred, true = np.array([p[0] for p in flat]), np.array([p[1] for p in flat])
        print(f"  {name:<12}{len(flat):12d}{pred.mean():>16.3f}{true.mean():>14.3f}{(true < pred).mean():>18.1%}")
    print(f"(5) failures at planning horizon 12: {TASKS} tasks")
    print(f"  {'model':<12}{'never reached puck':>20}{'mean progress (m)':>20}")
    for name in MODELS:
        h12 = [r for r in runs if r["model"] == name and r["horizon"] == 12]
        print(f"  {name:<12}{sum(not r['touched'] for r in h12):>20d}{np.mean([r['progress'] for r in h12]):>20.3f}")
    figure(pred_errors, success_by_cell)
    print(f"wrote {OUT / 'horizons.png'}")
