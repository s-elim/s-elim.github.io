"""Lesson 13.2: PPO from scratch on a seven-joint arm, and how its diagnostics read.

INPUT   mjcourse.envs.ReachEnv (joint_delta actions, 7 joints), mjcourse.rl.ppo
PROCESS (1) PPO with the default configuration, 300 000 steps: learning curve with the
            diagnostics (approximate KL, clip fraction, entropy, value loss, explained
            variance, policy standard deviation), then 100 held-out initial states;
        (2) the same with two bad settings, learning rate x10 and 40 epochs per batch:
            what each does to the diagnostics and to the result;
        (3) reach and hold (no termination on success, every episode truncated at 5 s),
            500 000 steps, with truncation bootstrapped and with it treated as terminal,
            3 seeds each
OUTPUT  printed tables

Run:  python examples/l13_2_ppo.py          (about ten minutes on 17 CPU cores)
"""
# requires: torch

import os

import numpy as np
import torch

from mjcourse.envs import ReachEnv
from mjcourse.rl.ppo import PPOConfig, evaluate, train

FAST = os.environ.get("MJC_FAST") == "1"
HELD_OUT = range(10_000, 10_100)                  # reset seeds never seen in training
COLUMNS = ("steps", "return", "success", "length", "kl", "clipfrac", "entropy", "value_loss", "explained_variance", "std")
HEADERS = ("steps", "return", "success", "length", "approx KL", "clip frac", "entropy", "value loss", "explained var", "policy std")


def show_curve(history: list[dict], every: int) -> None:
    print("    " + "".join(f"{c:>14}" if c == "explained var" else f"{c:>12}" for c in HEADERS))
    for row in history[every - 1::every]:
        print("    " + "".join(f"{row[c]:>12.0f}" if c == "steps" else f"{row[c]:>14.3f}" if c == "explained_variance" else f"{row[c]:>12.3f}" for c in COLUMNS))


def run(label: str, make, cfg: PPOConfig, every: int | None) -> dict:
    agent, history = train(make, cfg, log=None)
    result = evaluate(agent, make, HELD_OUT if not FAST else range(10_000, 10_010))
    print(f"  {label}: {history[-1]['seconds']:.0f} s")
    if every:
        show_curve(history, every)
    print(f"    held-out: success {result['success'].mean():.0%}, final distance median "
          f"{1000 * np.median(result['final_distance']):.1f} mm, 90th percentile {1000 * np.percentile(result['final_distance'], 90):.1f} mm, "
          f"mean return {result['return'].mean():.2f}")
    return result


if __name__ == "__main__":
    torch.set_num_threads(1)
    scale = 0.1 if FAST else 1.0
    reach = lambda: ReachEnv(action_mode="joint_delta")                                   # noqa: E731
    hold = lambda: ReachEnv(action_mode="joint_delta", terminate_on_success=False)        # noqa: E731
    base = dict(num_envs=16, steps_per_env=128, seed=0)
    print(f"torch {torch.__version__}; 16 environments x 128 steps = 2048 transitions per iteration")
    print("(1) default configuration: lr 3e-4, 10 epochs, minibatch 512, clip 0.2, gamma 0.99, lambda 0.95")
    run("reach, default", reach, PPOConfig(total_steps=int(300_000 * scale), **base), every=15)
    print("(2) bad settings")
    run("reach, learning rate 3e-3", reach, PPOConfig(total_steps=int(300_000 * scale), lr=3e-3, **base), every=15)
    run("reach, 40 epochs per batch", reach, PPOConfig(total_steps=int(300_000 * scale), epochs=40, **base), every=15)
    print("(3) reach and hold: every episode is truncated at 100 steps (5 s); curves for seed 0")
    medians = {}
    for label, boot in (("truncation bootstrapped", True), ("truncation treated as terminal", False)):
        medians[label] = []
        for seed in range(1 if FAST else 3):
            cfg = PPOConfig(total_steps=int(500_000 * scale), bootstrap_truncation=boot, **{**base, "seed": seed})
            result = run(f"hold, {label}, seed {seed}", hold, cfg, every=40 if seed == 0 else None)
            medians[label].append(1000 * np.median(result["final_distance"]))
    for label, values in medians.items():
        print(f"  {label}: held-out median final distance per seed {', '.join(f'{v:.1f}' for v in values)} mm")
