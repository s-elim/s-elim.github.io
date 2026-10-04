"""Lesson 21.3: one task name, two benchmarks: Gymnasium's MuJoCo environments v4 against v5 (Level 21).

INPUT   Gymnasium's MuJoCo environments in versions 4 and 5 (the installed gymnasium release, MuJoCo 3.14.0):
        Hopper, Walker2d, HalfCheetah, Ant, Humanoid, Swimmer, Reacher, InvertedPendulum
PROCESS (1) for each pair: observation and action sizes, control timestep, frame skip, time limit, and whether
            the compiled models are identical (mjcourse.experiment.model_fingerprint);
        (2) episodes under uniform random actions and under zero actions, 50 seeds each: mean length and return;
        (3) the initial-state distribution: the standard deviation of qpos and qvel over 200 resets;
        (4) the termination settings the two versions store (healthy z range, termination on unhealthy states)
OUTPUT  printed tables

Run:  python examples/l21_3_benchmark_anatomy.py          (about 2 minutes)
"""

import os
import warnings

import gymnasium as gym
import numpy as np

from mjcourse.experiment import model_fingerprint

warnings.filterwarnings("ignore")                               # v4 environments announce their deprecation
FAST = os.environ.get("MJC_FAST") == "1"
TASKS = ("Hopper", "Walker2d", "HalfCheetah", "Ant", "Humanoid", "Swimmer", "Reacher", "InvertedPendulum")
EPISODES = 5 if FAST else 50


def episodes(env_id: str, policy: str) -> tuple[float, float]:
    env = gym.make(env_id)
    lengths, returns = [], []
    for seed in range(EPISODES):
        obs, _ = env.reset(seed=seed)
        env.action_space.seed(seed)
        done, steps, total = False, 0, 0.0
        while not done:
            action = env.action_space.sample() if policy == "random" else np.zeros(env.action_space.shape)
            obs, reward, terminated, truncated, _ = env.step(action)
            total, steps, done = total + reward, steps + 1, terminated or truncated
        lengths.append(steps)
        returns.append(total)
    env.close()
    return float(np.mean(lengths)), float(np.mean(returns))


def reset_spread(env_id: str, n: int) -> tuple[float, float]:
    env = gym.make(env_id)
    qpos, qvel = [], []
    for seed in range(n):
        env.reset(seed=seed)
        qpos.append(env.unwrapped.data.qpos.copy())
        qvel.append(env.unwrapped.data.qvel.copy())
    env.close()
    return float(np.std(qpos, axis=0).mean()), float(np.std(qvel, axis=0).mean())


if __name__ == "__main__":
    print(f"gymnasium {gym.__version__}; {EPISODES} episodes per row")
    print("(1) the environments as specified")
    print(f"    {'task':<18}{'obs v4/v5':>11}{'act':>5}{'dt v4/v5':>14}{'frame skip':>12}{'time limit':>12}  same compiled model")
    for task in TASKS:
        envs = [gym.make(f"{task}-v{v}") for v in (4, 5)]
        u = [e.unwrapped for e in envs]
        same = model_fingerprint(u[0].model) == model_fingerprint(u[1].model)
        print(f"    {task:<18}{envs[0].observation_space.shape[0]:>5}/{envs[1].observation_space.shape[0]:<5}"
              f"{envs[0].action_space.shape[0]:>5}{u[0].dt:>8.3f}/{u[1].dt:<6.3f}{u[0].frame_skip:>6}/{u[1].frame_skip:<5}"
              f"{envs[0].spec.max_episode_steps:>6}/{envs[1].spec.max_episode_steps:<5}  {'yes' if same else 'no'}")
        for e in envs:
            e.close()
    print("(2) mean episode length and return, uniform random actions and zero actions")
    print(f"    {'task':<18}{'random v4':>22}{'random v5':>22}{'zero v4':>22}{'zero v5':>22}")
    for task in TASKS:
        cells = []
        for policy in ("random", "zero"):
            for v in (4, 5):
                length, ret = episodes(f"{task}-v{v}", policy)
                cells.append(f"{length:7.1f} steps {ret:9.1f}")
        print(f"    {task:<18}" + "".join(f"{c:>22}" for c in cells))
    print("(3) initial states: mean standard deviation over 200 resets, qpos and qvel")
    for task in TASKS:
        cells = [reset_spread(f"{task}-v{v}", 20 if FAST else 200) for v in (4, 5)]
        print(f"    {task:<18} v4 {cells[0][0]:.5f}, {cells[0][1]:.5f}   v5 {cells[1][0]:.5f}, {cells[1][1]:.5f}")
    print("(4) termination settings stored by the environments")
    for task in ("Hopper", "Walker2d", "Ant", "Humanoid"):
        cells = []
        for v in (4, 5):
            u = gym.make(f"{task}-v{v}").unwrapped
            z = getattr(u, "_healthy_z_range", None)
            cells.append(f"v{v}: healthy z {z}, terminate when unhealthy {getattr(u, '_terminate_when_unhealthy', None)}")
        print(f"    {task:<10} " + "; ".join(cells))
