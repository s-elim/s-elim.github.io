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
from mjcourse.worldmodel import mpc, standard

OUT = Path(__file__).resolve().parents[1] / "runs" / "l23_4"
FAST = os.environ.get("MJC_FAST") == "1"
TASKS, PROBES = (6, 2) if FAST else (50, 10)


def task_and_layout(i: int):
    rng = np.random.default_rng([4, i])
    task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
    return task, tt.sample_layout(rng, task)


def episode(args) -> dict:
    kind, i = args
    torch.set_num_threads(1)
    task, layout = task_and_layout(i)
    if kind == "MuJoCo":
        factory = lambda scene: mpc.MujocoModel(scene)
    else:
        model = standard.model("one_step")
        factory = lambda scene: mpc.LearnedModel(model)
    start = time.perf_counter()
    r = mpc.run_episode(factory, task, layout)
    return {"kind": kind, "i": i, "success": bool(r["success"]), "steps": r["steps"],
            "seconds_per_step": (time.perf_counter() - start) / r["steps"]}


def probe(i: int) -> dict:
    torch.set_num_threads(1)
    task, layout = task_and_layout(i)
    scene = tt.Tabletop()
    scene.reset(layout)
    planner = mpc.Planner(mpc.LearnedModel(standard.model("one_step")), task)
    truth = mpc.MujocoModel(scene)
    decisions, kept = [], None
    for _ in range(tt.EPISODE_STEPS):
        state = scene.state()
        a = planner.act(state)
        actions, cost_pred, chosen = planner.last["actions"], planner.last["costs"], planner.last["best"]
        true_states = truth.predict(state, actions)
        cost_true = mpc.cost(true_states, task, actions)
        gap = min(np.linalg.norm(state[:2] - state[4 + 4 * k:6 + 4 * k]) for k in range(3))
        contact = gap < tt.PUCK_RADIUS + tt.PUSHER_RADIUS + 0.003
        ranks = (np.argsort(np.argsort(cost_pred)), np.argsort(np.argsort(cost_true)))
        decisions.append({"contact": bool(contact), "spearman": float(np.corrcoef(*ranks)[0, 1]),
                          "true_rank": int((cost_true < cost_true[chosen]).sum()),
                          "regret": float(cost_true[chosen] - cost_true.min())})
        if contact and kept is None:
            kept = {"task": list(task), "predicted": planner.last["states"].tolist(), "true": true_states.tolist(),
                    "cost_pred": cost_pred.tolist(), "cost_true": cost_true.tolist(), "chosen": int(chosen)}
        scene.step(a)
        if scene.success(task):
            break
    scene.close()
    return {"i": i, "decisions": decisions, "example": kept}


def figure(p: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    i = 4 + 4 * tt.OBJECTS.index(p["task"][0])
    pred, true = np.array(p["predicted"]), np.array(p["true"])
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), constrained_layout=True, sharex=True, sharey=True)
    for ax, states, title in ((axes[0], pred, "predicted by the learned model"), (axes[1], true, "what MuJoCo says happens")):
        for k in range(len(states)):
            ax.plot(states[k, :, 1], states[k, :, 0], color="#7a7a7a", alpha=0.25, lw=0.8)
            ax.plot(states[k, :, i + 1], states[k, :, i], color="#E69F00", alpha=0.25, lw=0.8)
        c = p["chosen"]
        ax.plot(states[c, :, 1], states[c, :, 0], color="#0072B2", lw=2, label="chosen plan: pusher")
        ax.plot(states[c, :, i + 1], states[c, :, i], color="#D55E00", lw=2, label="chosen plan: puck")
        zone = tt.ZONES[p["task"][1]]
        ax.add_patch(plt.Circle((zone[1], zone[0]), tt.SUCCESS_RADIUS, color="#009E73", alpha=0.3))
        ax.set_title(title, fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlabel("y (m)")
    axes[0].invert_xaxis()
    axes[0].set_ylabel("x (m)")
    axes[0].legend(frameon=False, fontsize=8)
    fig.savefig(OUT / "candidates.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    standard.model("one_step")
    with ProcessPoolExecutor(min(32, os.cpu_count() or 1), mp_context=multiprocessing.get_context("spawn")) as pool:
        runs = list(pool.map(episode, [(k, i) for k in ("MuJoCo", "learned model") for i in range(TASKS)]))
        probes = list(pool.map(probe, range(PROBES)))
    print(f"(1) the same planner, two models, {TASKS} held-out tasks")
    for kind in ("MuJoCo", "learned model"):
        rows = [r for r in runs if r["kind"] == kind]
        k = sum(r["success"] for r in rows)
        lo, hi = stats.wilson_interval(k, len(rows))
        steps = [r["steps"] for r in rows if r["success"]]
        print(f"  {kind:<14} success {k}/{len(rows)} [{lo:.2f}, {hi:.2f}]   median time to success "
              f"{np.median(steps) / 10:.1f} s   planning {1000 * np.median([r['seconds_per_step'] for r in rows]):.0f} ms per step")
    both = {r["i"]: r["success"] for r in runs if r["kind"] == "MuJoCo"}
    learned = {r["i"]: r["success"] for r in runs if r["kind"] == "learned model"}
    print(f"  tasks solved by MuJoCo only {sum(both[i] and not learned[i] for i in both)}, "
          f"by the learned model only {sum(learned[i] and not both[i] for i in both)}")
    decisions = [d for p in probes for d in p["decisions"]]
    print(f"(2) inside the decisions of {PROBES} learned-model episodes ({len(decisions)} decisions, 64 candidates each)")
    for label, contact in (("pusher not touching a puck", False), ("pusher touching a puck", True)):
        rows = [d for d in decisions if d["contact"] == contact]
        print(f"  {label:<28} {len(rows):4d} decisions; rank correlation of predicted and true costs: median "
              f"{np.median([d['spearman'] for d in rows]):.2f}, 10th percentile {np.percentile([d['spearman'] for d in rows], 10):.2f}; "
              f"chosen candidate truly best in {np.mean([d['true_rank'] == 0 for d in rows]):.2f}, in the true top 5 in "
              f"{np.mean([d['true_rank'] < 5 for d in rows]):.2f}")
    example = next(p["example"] for p in probes if p["example"] is not None)
    figure(example)
    (OUT / "candidates.json").write_text(json.dumps(example))
    print(f"(3) wrote {OUT / 'candidates.png'} and {OUT / 'candidates.json'}")
