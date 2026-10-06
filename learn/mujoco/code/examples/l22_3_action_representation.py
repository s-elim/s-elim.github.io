import json
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

FAST = os.environ.get("MJC_FAST") == "1"
SEEDS = (0,) if FAST else (0, 1, 2)
DEMOS, TESTS = (40, 10) if FAST else (1000, 100)
TRAIN_LOW, TRAIN_HIGH = np.array([0.35, -0.25, 0.15]), np.array([0.60, 0.10, 0.45])
NEW_LOW, NEW_HIGH = np.array([0.35, 0.15, 0.15]), np.array([0.60, 0.25, 0.45])
CONDITIONS = ("nominal", "payload 1 kg", "10 Hz", "new region")
OUT = Path(__file__).resolve().parents[1] / "runs" / "l22_3"


def demonstrations(rep: str):
    from mjcourse.vla import actions as A

    env, rng = A.ArmReach(rep), np.random.default_rng(0)
    expert = A.Expert(env)
    obs, act = [], []
    for _ in range(DEMOS):
        env.reset(A.start_pose(rng, env.home), A.sample_target(rng, TRAIN_LOW, TRAIN_HIGH))
        expert.plan()
        for _ in range(A.STEPS):
            obs.append(env.obs())
            act.append(expert.act())
            env.step(act[-1])
    return np.array(obs), np.array(act)


def evaluate(policy, rep: str, condition: str) -> dict:
    from mjcourse.vla import actions as A

    env = A.ArmReach(rep, payload=1.0 if condition == "payload 1 kg" else 0.0,
                     frame_skip=2 * A.FRAME_SKIP if condition == "10 Hz" else A.FRAME_SKIP)
    steps = A.STEPS                                                          # 40 decisions in every condition
    low, high = (NEW_LOW, NEW_HIGH) if condition == "new region" else (TRAIN_LOW, TRAIN_HIGH)
    rng = np.random.default_rng(1000)                                        # held-out starts and targets
    ok, pos_err, jerk = [], [], []
    for _ in range(TESTS):
        env.reset(A.start_pose(rng, env.home), A.sample_target(rng, low, high))
        prev = None
        for _ in range(steps):
            a = np.clip(policy(env.obs()), -1, 1)
            if prev is not None:
                jerk.append(np.abs(a - prev).mean())
            prev = a
            env.step(a)
        ok.append(env.success())
        pos_err.append(env.errors()[0])
    return {"success": float(np.mean(ok)), "pos_err": float(np.median(pos_err)), "jerk": float(np.mean(jerk))}


KEEP_NO_VELOCITY = np.r_[np.ones(7), np.zeros(7), np.ones(10)].astype(bool)


def part1_job(args):
    rep, seed, drop_velocity = args
    import torch

    torch.set_num_threads(1)
    from mjcourse.il import bc

    obs, act = demonstrations(rep)
    keep = KEEP_NO_VELOCITY if drop_velocity else np.ones(obs.shape[1], bool)
    policy, info = bc.fit(obs[:, keep], act, steps=600 if FAST else 6000, hidden=256, seed=seed)
    return rep, seed, info["train_mse"], {c: evaluate(lambda o: policy(o[keep]), rep, c) for c in CONDITIONS}


def part1(pool, drop_velocity: bool = False) -> dict:
    from mjcourse.vla.actions import REPRESENTATIONS

    label = "(1b) without joint velocities in the observation" if drop_velocity else "(1) six action representations"
    print(f"{label}, the same reference motions; behaviour cloning, "
          f"{DEMOS} demonstrations, {len(SEEDS)} seed(s), {TESTS} held-out targets per condition")
    results = list(pool.map(part1_job, [(r, s, drop_velocity) for r in REPRESENTATIONS for s in SEEDS]))
    print(f"  {'representation':<17}" + "".join(f"{c:>24}" for c in CONDITIONS) + f"{'train MSE':>11}")
    for rep in REPRESENTATIONS:
        rows = [r for r in results if r[0] == rep]
        cells = []
        for c in CONDITIONS:
            vals = [r[3][c]["success"] for r in rows]
            cells.append(f"{np.mean(vals):.2f} ({', '.join(f'{v:.2f}' for v in vals)})")
        print(f"  {rep:<17}" + "".join(f"{x:>24}" for x in cells) + f"{np.mean([r[2] for r in rows]):>11.4f}")
    print("  median final position error (mm), nominal and payload; mean |change of action| per step (smoothness), nominal")
    for rep in REPRESENTATIONS:
        rows = [r for r in results if r[0] == rep]
        print(f"  {rep:<17} {1000 * np.mean([r[3]['nominal']['pos_err'] for r in rows]):7.1f}"
              f" {1000 * np.mean([r[3]['payload 1 kg']['pos_err'] for r in rows]):7.1f}"
              f"   {np.mean([r[3]['nominal']['jerk'] for r in rows]):.3f}")
    return {rep: {c: [r[3][c]["success"] for r in results if r[0] == rep] for c in CONDITIONS} for rep in REPRESENTATIONS}


def figure(tables: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from mjcourse.vla.actions import REPRESENTATIONS

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(tables, indent=1))
    fig, axes = plt.subplots(len(tables), 1, figsize=(9, 3.3 * len(tables)), constrained_layout=True, sharex=True)
    axes = np.atleast_1d(axes)
    colours = ("#0072B2", "#D55E00", "#009E73", "#CC79A7")
    width = 0.2
    for ax, (title, table) in zip(axes, tables.items()):
        for j, (c, colour) in enumerate(zip(CONDITIONS, colours)):
            means = [np.mean(table[r][c]) for r in REPRESENTATIONS]
            xs = np.arange(len(REPRESENTATIONS)) + (j - 1.5) * width
            ax.bar(xs, means, width, color=colour, label=c)
            for x, r in zip(xs, REPRESENTATIONS):
                ax.plot([x] * len(table[r][c]), table[r][c], "k.", markersize=3)
        ax.set_ylabel("success (100 targets)")
        ax.set_ylim(0, 1.05)
        ax.set_title(f"observation {title}", fontsize=10)
        ax.grid(axis="y", alpha=0.3)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncol=4, loc="outside upper center", fontsize=8)
    axes[-1].set_xticks(np.arange(len(REPRESENTATIONS)), [r.replace("_", " ") for r in REPRESENTATIONS])
    fig.savefig(OUT / "representations.png", dpi=150)
    plt.close(fig)


def part2_job(args):
    chunk, seed = args
    import torch
    from torch import nn

    from mjcourse import tabletop as tt

    torch.set_num_threads(1)
    n_demos = 300 if FAST else 2000

    def onehot(task):
        v = np.zeros(7, np.float32)
        v[tt.OBJECTS.index(task[0])] = 1
        v[3 + list(tt.ZONES).index(task[1])] = 1
        return v

    xs, ys = [], []
    for i in range(n_demos):
        rng = np.random.default_rng([0, i])
        task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
        scene = tt.Tabletop()
        scene.reset(tt.sample_layout(rng, task))
        states, acts = [], []
        for _ in range(tt.EPISODE_STEPS):
            s = scene.state()
            states.append(np.r_[s, onehot(task)])
            acts.append(tt.expert(s, task))
            scene.step(acts[-1])
            if scene.success(task):
                break
        if not scene.success(task):
            continue
        padded = np.concatenate([acts, np.zeros((chunk, 2))])
        for t in range(len(states)):
            xs.append(states[t])
            ys.append(padded[t:t + chunk].ravel())
    torch.manual_seed(seed)
    x, y = torch.as_tensor(np.array(xs, np.float32)), torch.as_tensor(np.array(ys, np.float32))
    net = nn.Sequential(nn.Linear(23, 256), nn.ReLU(), nn.Linear(256, 256), nn.ReLU(), nn.Linear(256, 2 * chunk), nn.Tanh())
    opt = torch.optim.Adam(net.parameters(), 1e-3)
    for _ in range(1500 if FAST else 15000):
        idx = torch.randint(0, len(x), (256,))
        loss = ((net(x[idx]) - y[idx]) ** 2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    out = {}
    for mode in ("first action", "open-loop chunk", "temporal ensemble"):
        if chunk == 1 and mode != "first action":
            continue
        ok = []
        for i in range(30 if FAST else 100):
            rng = np.random.default_rng([99, i])
            task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
            scene = tt.Tabletop()
            scene.reset(tt.sample_layout(rng, task))
            history, plan = [], []
            for t in range(tt.EPISODE_STEPS):
                with torch.no_grad():
                    c = net(torch.as_tensor(np.r_[scene.state(), onehot(task)], dtype=torch.float32)).numpy().reshape(chunk, 2)
                if mode == "first action":
                    a = c[0]
                elif mode == "open-loop chunk":
                    if not plan:
                        plan = list(c)
                    a = plan.pop(0)
                else:
                    history = [(t0, h) for t0, h in history if t - t0 < chunk] + [(t, c)]
                    a = np.mean([h[t - t0] for t0, h in history], axis=0)
                scene.step(a)
                if scene.success(task):
                    break
            ok.append(scene.success(task))
        out[mode] = float(np.mean(ok))
    return chunk, seed, out


def part2(pool) -> None:
    print(f"(2) action chunks on the tabletop: state policies, {300 if FAST else 2000} demonstrations, "
          f"success on {30 if FAST else 100} held-out tasks")
    results = list(pool.map(part2_job, [(c, s) for c in (1, 4, 8) for s in SEEDS]))
    for chunk in (1, 4, 8):
        for mode in ("first action", "open-loop chunk", "temporal ensemble"):
            vals = [r[2][mode] for r in results if r[0] == chunk and mode in r[2]]
            if vals:
                print(f"  chunk {chunk}, {mode:<18} {np.mean(vals):.2f} ({', '.join(f'{v:.2f}' for v in vals)})")


if __name__ == "__main__":
    with ProcessPoolExecutor(min(32, os.cpu_count() or 1), mp_context=multiprocessing.get_context("spawn")) as pool:
        part, tables = os.environ.get("MJC_PART", "all"), {}
        if part in ("all", "1"):
            tables["with joint velocities"] = part1(pool)
        if part in ("all", "1b"):
            tables["without joint velocities"] = part1(pool, drop_velocity=True)
        if tables:
            figure(tables)
        if part in ("all", "2"):
            part2(pool)
