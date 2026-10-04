"""Lesson 13.3: DDPG, TD3 and SAC against PPO, and how to evaluate any agent (Level 13 checkpoint).

INPUT   mjcourse.envs.ReachEnv (joint_delta actions); mjcourse.rl.offpolicy and mjcourse.rl.ppo
PROCESS (1) DDPG, TD3, SAC (initial temperature 0.1) and SAC (initial temperature 1.0),
            40 000 environment steps, 3 seeds each in parallel: deterministic success on 20
            held-out initial states every 10 000 steps, then on 100;
        (2) PPO, 3 seeds, the same held-out evaluation every 10 000 steps up to 100 000;
        (3) the checkpoint: PPO with and without observation normalization, 5 seeds each,
            300 000 steps; per seed: held-out success on 100 states, mean steps to reach,
            environment steps until held-out success first reaches 90%; across seeds: mean,
            IQM and 95% bootstrap intervals;
        (4) evaluation pitfalls on the checkpoint runs: training success against held-out
            success; how the interval narrows with seeds; pooling episodes across seeds
OUTPUT  printed tables

Run:  python examples/l13_3_evaluation.py          (about fifteen minutes on 17 CPU cores)
"""
# requires: torch

import os
from multiprocessing import Pool

import numpy as np
import torch

from mjcourse import stats
from mjcourse.envs import ReachEnv
from mjcourse.rl import offpolicy, ppo

FAST = os.environ.get("MJC_FAST") == "1"
CURVE_STATES, FINAL_STATES = range(10_000, 10_020), range(10_000, 10_100)   # reset seeds never used in training


def make_env():
    return ReachEnv(action_mode="joint_delta")


def held_out(act, seeds) -> dict:
    """Deterministic episodes from the given reset seeds with `act(obs) -> action`."""
    env = make_env()
    success, length = [], []
    for seed in seeds:
        obs, _ = env.reset(seed=int(seed))
        steps, done = 0, False
        while not done:
            obs, _, terminated, truncated, info = env.step(np.asarray(act(obs), np.float32))
            steps, done = steps + 1, terminated or truncated
        success.append(info["is_success"])
        length.append(steps)
    env.close()
    return {"success": float(np.mean(success)), "length": float(np.mean(length))}


# ---------------------------------------------------------------- (1, 2) off-policy against PPO

def off_policy_run(job: tuple[str, float, int, int]) -> tuple[str, int, list[dict], dict]:
    algo, alpha, seed, steps = job
    torch.set_num_threads(1)
    cfg = offpolicy.OffPolicyConfig(algo=algo, init_alpha=alpha, total_steps=steps, seed=seed, eval_every=steps // 4)
    learner, history = offpolicy.train(make_env, cfg, lambda l: held_out(lambda o: l.act(o, explore=False), CURVE_STATES), log=None)
    final = held_out(lambda o: learner.act(o, explore=False), FINAL_STATES)
    name = f"{algo.upper()}" + (f" (temperature {alpha:g})" if algo == "sac" else "")
    return name, seed, history, final


def part1_2() -> None:
    steps, seeds = (2_000, 1) if FAST else (40_000, 3)
    jobs = [(algo, alpha, seed, steps) for algo, alpha in (("ddpg", 0.1), ("td3", 0.1), ("sac", 0.1), ("sac", 1.0))
            for seed in range(seeds)]
    if FAST:
        results = [off_policy_run(j) for j in jobs]
    else:
        with Pool(len(jobs)) as pool:
            results = pool.map(off_policy_run, jobs)
    marks = [h["steps"] for h in results[0][2]]
    print(f"  held-out success (20 states) at {', '.join(f'{m // 1000}k' for m in marks)} steps, then on 100 states; per seed")
    for name in dict.fromkeys(r[0] for r in results):
        rows = [r for r in results if r[0] == name]
        curves = "; ".join("/".join(f"{h['success']:.2f}" for h in r[2]) for r in rows)
        finals = ", ".join(f"{r[3]['success']:.2f}" for r in rows)
        print(f"  {name:<26} {curves:<44} final {finals}   ({rows[0][2][-1]['seconds']:.0f} s each)")
    ppo_steps = 10_000 if FAST else 100_000
    for seed in range(seeds):
        cfg = ppo.PPOConfig(total_steps=ppo_steps, seed=seed)
        agent, history = ppo.train(make_env, cfg, log=None, evaluate_fn=lambda a: held_out(a.act, CURVE_STATES), eval_every=10_000)
        evals = [(h["steps"], h["eval"]["success"]) for h in history if "eval" in h]
        print(f"  PPO seed {seed} (16 environments): " + ", ".join(f"{s // 1000}k {v:.2f}" for s, v in evals)
              + f"; final on 100 states {held_out(agent.act, FINAL_STATES)['success']:.2f} ({history[-1]['seconds']:.0f} s)")


# ---------------------------------------------------------------- (3, 4) the checkpoint

def checkpoint_run(normalize: bool, seed: int, steps: int) -> dict:
    cfg = ppo.PPOConfig(total_steps=steps, seed=seed, normalize_obs=normalize)
    agent, history = ppo.train(make_env, cfg, log=None, evaluate_fn=lambda a: held_out(a.act, CURVE_STATES), eval_every=10_000)
    final = held_out(agent.act, FINAL_STATES)
    reached = [h["steps"] for h in history if "eval" in h and h["eval"]["success"] >= 0.9]
    return {"success": final["success"], "length": final["length"], "steps_to_90": reached[0] if reached else np.nan,
            "train_success": history[-1]["success"], "seconds": history[-1]["seconds"]}


def summary(values) -> str:
    values = np.asarray(values, float)
    if np.isnan(values).any():
        return f"{np.isnan(values).sum()} seeds never reached it"
    mean, lo, hi = stats.bootstrap_ci(values)
    return f"mean {mean:.3g} [{lo:.3g}, {hi:.3g}], IQM {stats.iqm(values):.3g}"


def part3_4() -> None:
    steps, seeds = (10_000, 2) if FAST else (300_000, 5)
    runs = {}
    for normalize in (True, False):
        label = "normalized observations" if normalize else "raw observations"
        runs[label] = [checkpoint_run(normalize, seed, steps) for seed in range(seeds)]
        r = runs[label]
        print(f"  {label}: {steps // 1000}k steps per seed, {r[0]['seconds']:.0f} s each")
        print(f"    held-out success per seed  {', '.join(format(x['success'], '.2f') for x in r)}   {summary([x['success'] for x in r])}")
        print(f"    mean steps to reach        {', '.join(format(x['length'], '.1f') for x in r)}   {summary([x['length'] for x in r])}")
        print(f"    steps until 90% held-out   {', '.join('never' if np.isnan(x['steps_to_90']) else format(x['steps_to_90'] / 1000, '.0f') + 'k' for x in r)}   "
              f"{summary([x['steps_to_90'] / 1000 for x in r])} (thousands)")
    a, b = runs["normalized observations"], runs["raw observations"]
    for key, name in (("length", "mean steps to reach"), ("steps_to_90", "steps until 90%")):
        if not any(np.isnan([x[key] for x in a + b])):
            diff, lo, hi = stats.paired_difference_ci([x[key] for x in b], [x[key] for x in a])
            print(f"  raw minus normalized, {name}, matched by seed: {diff:.3g} [{lo:.3g}, {hi:.3g}]")
    print("(4) evaluation pitfalls, normalized runs")
    r = a
    print(f"  training success (stochastic policy, last 100 training episodes) per seed: "
          f"{', '.join(format(x['train_success'], '.2f') for x in r)}; held-out deterministic: {', '.join(format(x['success'], '.2f') for x in r)}")
    lengths = [x["length"] for x in r]
    for k in range(1, len(lengths) + 1):
        if k == 1:
            print(f"  mean steps to reach from 1 seed: {lengths[0]:.2f}, no interval possible")
        else:
            mean, lo, hi = stats.bootstrap_ci(lengths[:k])
            print(f"  mean steps to reach from {k} seeds: {mean:.2f} [{lo:.2f}, {hi:.2f}], width {hi - lo:.2f}")


if __name__ == "__main__":
    print(f"torch {torch.__version__}; ReachEnv joint_delta; held-out reset seeds 10000-10099")
    print("(1, 2) off-policy and PPO, deterministic evaluation on held-out states")
    part1_2()
    print("(3) checkpoint: PPO with and without observation normalization")
    part3_4()
