"""Lesson 14.1: behaviour cloning, covariate shift and DAgger on the point-mass task (Level 14 checkpoint).

INPUT   mjcourse.il.pointmass (task and scripted expert), mjcourse.il.bc (cloning and DAgger)
PROCESS (1) the expert on 100 held-out starts, without and with random pushes (1 per second
            on average, 0.4 m/s each);
        (2) behaviour cloning on 20 expert demonstrations recorded without pushes, evaluated
            without and with pushes; covariate shift measured as the distance from every
            visited state to the nearest demonstrated state, for the expert and the clone;
        (3) success under pushes against the number of expert labels, 3 seeds: DAgger (5
            iterations of 4 rollouts), cloning on more demonstrations without pushes, and
            cloning on demonstrations recorded with pushes; a figure;
        (4) the expert's discontinuity at y = 0 and what regression makes of it
OUTPUT  printed tables and runs/l14_1/labels.png

Run:  python examples/l14_1_bc_dagger.py
"""
# requires: torch

import os
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import torch

from mjcourse.il import bc
from mjcourse.il import pointmass as pm

FAST = os.environ.get("MJC_FAST") == "1"
PUSH = 1.0                                         # pushes per second at evaluation
HELD_OUT = pm.sample_starts(np.random.default_rng(999), 30 if FAST else 100)
FIGURE = Path(__file__).resolve().parents[1] / "runs" / "l14_1" / "labels.png"


def demonstrations(n: int, seed: int, push_rate: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    sim, rng = pm.PointMass(), np.random.default_rng(seed)
    runs = [sim.rollout(pm.expert, s, push_rate=push_rate, rng=np.random.default_rng([seed, 7, i]))
            for i, s in enumerate(pm.sample_starts(rng, n))]
    return np.vstack([r.states for r in runs]), np.vstack([r.actions for r in runs])


def scores(policy, push_rate: float = PUSH) -> dict:
    out = pm.evaluate(policy, HELD_OUT, push_rate=push_rate)
    return {k: out[k] for k in ("success", "hit", "steps")} | {"runs": out["runs"]}


def nearest_distance(points: np.ndarray, data: np.ndarray, scale: np.ndarray) -> np.ndarray:
    """Distance from each point to its nearest neighbour in `data`, in units of the data's std."""
    a, b = points / scale, data / scale
    out = np.empty(len(a))
    for i in range(0, len(a), 2000):
        out[i:i + 2000] = np.sqrt(((a[i:i + 2000, None, :] - b[None, :, :]) ** 2).sum(-1)).min(axis=1)
    return out


def part1_2() -> None:
    torch.set_num_threads(4)
    for label, rate in (("without pushes", 0.0), ("with pushes", PUSH)):
        s = scores(pm.expert, rate)
        print(f"  expert {label:<16} success {s['success']:.2f}, obstacle touched {s['hit']:.2f}, mean time {s['steps'] / 100:.2f} s")
    states, actions = demonstrations(20, seed=0)
    policy, info = bc.fit(states, actions, seed=0)
    print(f"  20 demonstrations: {len(states)} state-action pairs; training MSE {info['train_mse']:.4f} (normalized units)")
    for label, rate in (("without pushes", 0.0), ("with pushes", PUSH)):
        s = scores(policy, rate)
        print(f"  clone  {label:<16} success {s['success']:.2f}, obstacle touched {s['hit']:.2f}, mean time {s['steps'] / 100:.2f} s")
    scale = states.std(axis=0)
    print(f"  distance from visited states to the nearest demonstrated state (units of the demonstrations' std), with pushes:")
    for name, pol in (("expert", pm.expert), ("clone", policy)):
        runs = scores(pol)["runs"]
        visited = np.vstack([r.states for r in runs])
        dist = nearest_distance(visited, states, scale)
        per_run = np.array([nearest_distance(r.states, states, scale).max() for r in runs])
        failed = np.array([not r.success for r in runs])
        line = f"    {name:<7} median {np.median(dist):.2f}, 90th percentile {np.percentile(dist, 90):.2f}, 99th {np.percentile(dist, 99):.2f}"
        if failed.any() and (~failed).any():
            line += (f"; largest distance per episode: successes median {np.median(per_run[~failed]):.2f}, "
                     f"failures median {np.median(per_run[failed]):.2f}")
        print(line)


def curve(seed: int) -> dict:
    torch.set_num_threads(1)
    rng = np.random.default_rng([seed, 1])
    states, actions = demonstrations(20, seed=seed)
    sim = pm.PointMass()
    evaluate = lambda p: {k: v for k, v in scores(p).items() if k != "runs"}         # noqa: E731
    iterations = 2 if FAST else 5
    dagger_rows = bc.dagger(sim, pm.expert, states, actions, pm.sample_starts(rng, iterations * 4).reshape(iterations, 4, 2),
                            iterations, evaluate, seed=seed, push_rate=PUSH)
    more, pushed = [], []
    for n in ((20, 40) if FAST else (20, 30, 40, 50)):
        for rows, rate in ((more, 0.0), (pushed, PUSH)):
            s, a = demonstrations(n, seed=seed, push_rate=rate)
            policy, _ = bc.fit(s, a, seed=seed)
            rows.append({"labels": len(s), **evaluate(policy)})
    return {"seed": seed, "dagger": dagger_rows, "more": more, "pushed": pushed}


def part3() -> list[dict]:
    seeds = 1 if FAST else 3
    if FAST:
        results = [curve(0)]
    else:
        with Pool(seeds) as pool:
            results = pool.map(curve, range(seeds))
    for name, key in (("DAgger (iteration: labels, success)", "dagger"), ("more demonstrations without pushes", "more"),
                      ("demonstrations recorded with pushes", "pushed")):
        print(f"  {name}")
        for r in results:
            print(f"    seed {r['seed']}: " + ", ".join(f"{row['labels']}: {row['success']:.2f}" for row in r[key]))
    final = {key: [r[key][-1]["success"] for r in results] for key in ("dagger", "more", "pushed")}
    print(f"  at the largest label budget, success per seed: DAgger {final['dagger']}, more demonstrations {final['more']}, "
          f"pushed demonstrations {final['pushed']}")
    return results


def part4() -> None:
    states, actions = demonstrations(20, seed=0)
    policy, _ = bc.fit(states, actions, seed=0)
    print(f"  {'y (m)':>8}{'expert fy (N)':>15}{'clone fy (N)':>14}     at x = -0.2 m, at rest")
    for y in (-0.03, -0.01, -0.003, 0.0, 0.003, 0.01, 0.03):
        s = np.array([-0.2, y, 0.0, 0.0])
        print(f"  {y:>8.3f}{pm.expert(s)[1]:>15.2f}{float(policy(s)[1]):>14.2f}")


def figure(results: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 3.8), constrained_layout=True)
    styles = (("dagger", "DAgger", "#0072B2", "o"), ("more", "more demonstrations, no pushes", "#D55E00", "s"),
              ("pushed", "demonstrations recorded with pushes", "#009E73", "^"))
    for key, label, colour, marker in styles:
        for i, r in enumerate(results):
            xs = [row["labels"] / 1000 for row in r[key]]
            ys = [row["success"] for row in r[key]]
            ax.plot(xs, ys, color=colour, marker=marker, alpha=0.8, label=label if i == 0 else None)
    ax.set_xlabel("expert labels (thousands of state-action pairs)")
    ax.set_ylabel("success with pushes (100 held-out starts)")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, loc="lower right")
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    print(f"torch {torch.__version__}; {len(HELD_OUT)} held-out starts; pushes {PUSH} per second, 0.4 m/s")
    print("(1, 2) the expert, and a clone of 20 demonstrations")
    part1_2()
    print("(3) success with pushes against expert labels, one line per seed")
    results = part3()
    figure(results)
    print(f"  figure: {FIGURE.relative_to(FIGURE.parents[2])}")
    print("(4) the expert's choice of side, and the clone's")
    part4()
