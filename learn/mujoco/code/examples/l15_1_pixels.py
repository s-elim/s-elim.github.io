"""Lesson 15.1: from state to pixels, with equal demonstrations, held-out conditions and a shortcut.

INPUT   mjcourse.il.goalreach (point mass, random goal, top camera), mjcourse.il.bc and .vision
PROCESS (1) 100 expert demonstrations with the distractor placed at random; three policies
            cloned from them: state (position, velocity, goal coordinates), RGB 64 x 64 plus
            proprioception, RGB-D plus proprioception; 3 seeds each; success on 50 held-out
            tasks under nominal conditions, dim light, and a shifted camera;
        (2) the same demonstrations recorded with the distractor always 12 cm from the goal
            (a shortcut); RGB policies cloned from them, tested with the distractor in the
            same place and at random;
        (3) RGB policies cloned from three times as many demonstrations
OUTPUT  printed tables

Run:  MUJOCO_GL=egl python examples/l15_1_pixels.py     (or osmesa without a GPU; about 6 minutes on 18 cores)
"""
# requires: render
# requires: torch

import os
from multiprocessing import Pool

import numpy as np
import torch

from mjcourse import stats
from mjcourse.il import bc, vision
from mjcourse.il import goalreach as gr

FAST = os.environ.get("MJC_FAST") == "1"
DEMOS, TESTS, SEEDS = (12, 8, 1) if FAST else (100, 50, 3)


def record(shortcut: bool, seed: int = 0, demos: int = DEMOS) -> dict:
    """Demonstrations at the policy's rate: state, goal, RGB, RGB-D and the expert's action."""
    env, rng, other = gr.GoalReach("nominal"), np.random.default_rng([seed, 11]), np.random.default_rng([seed, 12])
    out = {"state": [], "goal": [], "rgb": [], "rgbd": [], "action": []}
    for _ in range(demos):
        start, goal = gr.sample_task(rng)
        env.reset(start, goal, gr.distractor_position(goal, shortcut, other))
        for _ in range(gr.MAX_ACTIONS):
            s = env.state()
            a = gr.expert(s, goal)
            for k, v in (("state", s), ("goal", goal), ("rgb", env.image()), ("rgbd", env.image(depth=True)), ("action", a)):
                out[k].append(v)
            if env.step(a):
                break
    env.close()
    return {k: np.array(v) for k, v in out.items()}


def evaluate(kind: str, policy, condition: str, shortcut_at_test: bool) -> float:
    env, rng = gr.GoalReach(condition), np.random.default_rng(5150)            # the same tasks for every policy
    other = np.random.default_rng(5151)                                         # distractors drawn separately
    wins = 0
    for _ in range(TESTS):
        start, goal = gr.sample_task(rng)
        env.reset(start, goal, gr.distractor_position(goal, shortcut_at_test, other))
        for _ in range(gr.MAX_ACTIONS):
            s = env.state()
            if kind == "state":
                a = policy(np.r_[s, goal])
            else:
                a = policy(env.image(depth=kind == "rgbd"), s)
            if env.step(a):
                wins += 1
                break
    env.close()
    return wins / TESTS


def train_and_test(job) -> dict:
    kind, seed, shortcut, demos = job
    torch.set_num_threads(2)
    data = record(shortcut, demos=demos)
    if kind == "state":
        policy, _ = bc.fit(np.c_[data["state"], data["goal"]], data["action"], seed=seed)
    else:
        policy = vision.fit_images(data[kind], data["state"], data["action"], steps=300 if FAST else 3000, seed=seed)
    if shortcut:
        return {"kind": kind, "seed": seed, "shortcut kept": evaluate(kind, policy, "nominal", True),
                "shortcut broken": evaluate(kind, policy, "nominal", False)}
    return {"kind": kind if demos == DEMOS else f"{kind} x3", "seed": seed, **{c: evaluate(kind, policy, c, False) for c in gr.CONDITIONS},
            "frames": len(data["action"])}


def show(rows, columns) -> None:
    for kind in dict.fromkeys(r["kind"] for r in rows):
        sel = [r for r in rows if r["kind"] == kind]
        cells = []
        for c in columns:
            values = [r[c] for r in sel]
            mean, lo, hi = stats.bootstrap_ci(values) if len(values) > 1 else (values[0], values[0], values[0])
            cells.append(f"{c}: {', '.join(f'{v:.2f}' for v in values)} (mean {mean:.2f})")
        print(f"  {kind:<6} " + ";  ".join(cells))


if __name__ == "__main__":
    print(f"{DEMOS} demonstrations, {TESTS} held-out tasks, {SEEDS} seeds; images 64 x 64 from a camera 1.25 m above")
    jobs = ([(k, s, False, DEMOS) for k in ("state", "rgb", "rgbd") for s in range(SEEDS)]
            + [(k, s, True, DEMOS) for k in ("state", "rgb") for s in range(SEEDS)]
            + [("rgb", s, False, 3 * DEMOS) for s in range(SEEDS)])
    if FAST:
        results = [train_and_test(j) for j in jobs]
    else:
        with Pool(len(jobs)) as pool:
            results = pool.map(train_and_test, jobs)
    plain = [r for r in results if "nominal" in r and not r["kind"].endswith("x3")]
    print(f"  demonstration frames: {plain[0]['frames']} (identical data for every policy)")
    print("(1) success on held-out tasks by condition, per seed")
    show(plain, gr.CONDITIONS)
    print("(2) trained with the distractor always 12 cm from the goal; tested with it there and at random")
    show([r for r in results if "shortcut kept" in r], ("shortcut kept", "shortcut broken"))
    more = [r for r in results if r["kind"].endswith("x3")]
    print(f"(3) RGB with {3 * DEMOS} demonstrations ({more[0]['frames']} frames)")
    show(more, gr.CONDITIONS)
