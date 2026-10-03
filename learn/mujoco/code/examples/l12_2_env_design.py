"""Lesson 12.2: action spaces, rewards and observations of the push task, measured.

INPUT   mjcourse.envs.PushEnv
PROCESS (1) random actions in each action space (torque, joint_delta, ee_delta): how far the
            tool travels, whether it reaches the puck, joint-limit and floor contacts, cost;
        (2) four rewards (dense, shaped, sparse, contact) each optimized by the cross-entropy
            method over open-loop plans: the return found against the task's success;
        (3) privileged information, with mjcourse.envs.checks: a test of declared observation
            sources and a test that perturbs quantities a robot cannot sense, on the standard
            observation and on four leaky ones (one of them mislabelled)
OUTPUT  printed tables

Run:  python examples/l12_2_env_design.py
"""

import os
import time

import gymnasium as gym
import mujoco
import numpy as np

import mjcourse.envs  # noqa: F401  (registers the environments)
from mjcourse.envs import checks
from mjcourse.envs.push import OBSERVATION, PushEnv

FAST = os.environ.get("MJC_FAST") == "1"
TASK = {"puck": np.array([0.47, 0.0]), "goal": np.array([0.62, 0.10])}   # one fixed task for part (2)
HORIZON, KNOTS = 60, 6                                                   # 3 s plans with 6 piecewise-constant knots


# ---------------------------------------------------------------- (1) action spaces

def random_rollouts(mode: str, episodes: int) -> dict:
    env = PushEnv(action_mode=mode, reward="dense")
    m, d = env.model, env.data
    floor = m.geom("floor").id
    arm_bodies = {b for b in range(m.nbody) if b not in (0, m.body("puck").id)}
    out = {"path": [], "reach": 0, "moved": [], "near_limit": [], "floor": 0}
    start = time.perf_counter()
    steps = 0
    for i in range(episodes):
        env.reset(seed=i)
        env.action_space.seed(i)
        tcp_prev, path, touched, floor_hit, limit_steps = d.site("gripper/tcp").xpos.copy(), 0.0, False, False, 0
        puck0 = env.puck_xy()
        for _ in range(env.max_episode_steps):
            _, _, terminated, _, info = env.step(env.action_space.sample())
            steps += 1
            tcp = d.site("gripper/tcp").xpos.copy()
            path += np.linalg.norm(tcp - tcp_prev)
            tcp_prev = tcp
            touched |= info["contact"]
            q, lo, hi = d.qpos[:7], m.jnt_range[:7, 0], m.jnt_range[:7, 1]
            limit_steps += bool(np.any((q - lo < 0.02 * (hi - lo)) | (hi - q < 0.02 * (hi - lo))))
            floor_hit |= any((c.geom1 == floor and m.geom_bodyid[c.geom2] in arm_bodies) or
                             (c.geom2 == floor and m.geom_bodyid[c.geom1] in arm_bodies) for c in d.contact[:d.ncon])
            if terminated:
                break
        out["path"].append(path)
        out["reach"] += touched
        out["moved"].append(np.linalg.norm(env.puck_xy() - puck0))
        out["near_limit"].append(limit_steps / env.max_episode_steps)
        out["floor"] += floor_hit
    out["rate"] = steps / (time.perf_counter() - start)
    return out


def part1() -> None:
    n = 10 if FAST else 50
    print(f"  {n} episodes of 100 random actions (5 s) per mode")
    print(f"  {'mode':<12}{'tool path (m)':>14}{'touched puck':>14}{'puck moved (mm)':>17}{'steps near a limit':>20}{'arm hit floor':>15}{'steps/s':>9}")
    for mode in ("torque", "joint_delta", "ee_delta"):
        r = random_rollouts(mode, n)
        print(f"  {mode:<12}{np.mean(r['path']):>14.2f}{r['reach']:>11d}/{n}{1000 * np.mean(r['moved']):>17.1f}"
              f"{np.mean(r['near_limit']):>20.1%}{r['floor']:>12d}/{n}{r['rate']:>9.0f}")


# ---------------------------------------------------------------- (2) rewards and the cross-entropy method

def plan_actions(params: np.ndarray) -> np.ndarray:
    """(KNOTS*2,) parameters -> (HORIZON, 2) piecewise-constant ee_delta actions."""
    return np.repeat(np.clip(params.reshape(KNOTS, 2), -1, 1), HORIZON // KNOTS, axis=0).astype(np.float32)


def evaluate(envs, population: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns, success flags and final puck-goal distances of each plan, run in parallel."""
    n = len(population)
    envs.reset(options=TASK)
    plans = np.stack([plan_actions(p) for p in population])
    returns, success, done = np.zeros(n), np.zeros(n, bool), np.zeros(n, bool)
    distance = np.zeros(n)
    for t in range(HORIZON):
        _, reward, terminated, truncated, info = envs.step(plans[:, t])
        live = ~done
        returns[live] += reward[live]
        success[live] |= info["is_success"][live]
        distance[live] = info["distance"][live]
        done |= terminated | truncated
        if done.all():
            break
    return returns, success, distance


def cem(reward: str, seed: int, population: int, iterations: int, envs) -> dict:
    rng = np.random.default_rng(seed)
    mean, std = np.zeros(KNOTS * 2), np.full(KNOTS * 2, 0.6)
    for _ in range(iterations):
        samples = np.clip(rng.normal(mean, std, (population, KNOTS * 2)), -1, 1)
        returns, _, _ = evaluate(envs, samples)
        elite = samples[np.argsort(returns)[-max(2, population // 5):]]
        mean, std = elite.mean(axis=0), elite.std(axis=0) + 0.02
    returns, success, distance = evaluate(envs, np.repeat(mean[None], population, axis=0)[:population])
    return {"return": returns[0], "success": bool(success[0]), "distance": distance[0]}


def part2() -> None:
    population, iterations, seeds = (8, 3, 2) if FAST else (32, 20, 5)
    print(f"  task: puck at {TASK['puck']}, goal at {TASK['goal']}; plans of {KNOTS} piecewise-constant ee_delta "
          f"actions over {HORIZON} steps; CEM population {population}, {iterations} iterations, {seeds} seeds per reward")
    print(f"  {'reward optimized':<18}{'return of the plan (per seed)':<40}{'task success':>13}{'final puck-goal distance (mm)':>36}")
    for reward in ("dense", "shaped", "sparse", "contact"):
        envs = gym.vector.AsyncVectorEnv([lambda r=reward: gym.make("mjcourse/Push-v0", action_mode="ee_delta", reward=r,
                                                                    max_episode_steps=HORIZON)] * population)
        results = [cem(reward, s, population, iterations, envs) for s in range(seeds)]
        envs.close()
        print(f"  {reward:<18}{', '.join(f'{r['return']:.2f}' for r in results):<40}"
              f"{sum(r['success'] for r in results):>10d}/{seeds}"
              f"{', '.join(f'{1000 * r['distance']:.0f}' for r in results):>36}")


# ---------------------------------------------------------------- (3) privileged information

class MislabelledLeak(PushEnv):
    """Appends the puck's true velocity but declares it as coming from the camera tracker."""

    def __init__(self, **kwargs):
        super().__init__(extra_observations=("puck_velocity",), **kwargs)
        self.observation_sources["puck_velocity"] = "camera tracker"


def part3() -> None:
    print(f"  declared sources allowed: {sorted(checks.REAL_SOURCES)}")
    print(f"  {'observation':<44}{'declared-source test':<42}{'perturbation test (changed by)':<30}")
    variants = [("standard: " + ", ".join(n for n, _, _ in OBSERVATION), PushEnv(action_mode="ee_delta")),
                ("+ puck velocity (simulator state)", PushEnv(action_mode="ee_delta", extra_observations=("puck_velocity",))),
                ("+ contact force (contact solver)", PushEnv(action_mode="ee_delta", extra_observations=("contact_force",))),
                ("+ puck friction (model parameter)", PushEnv(action_mode="ee_delta", extra_observations=("puck_friction",))),
                ("+ puck velocity labelled 'camera tracker'", MislabelledLeak(action_mode="ee_delta"))]
    for label, env in variants:
        bad, leaks = checks.undeclared_sources(env), checks.perturbation_leaks(env)
        print(f"  {label[:43]:<44}{'pass' if not bad else 'FAIL: ' + ', '.join(bad):<42}{'pass' if not leaks else 'FAIL: ' + ', '.join(leaks):<30}")
        env.close()


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}, gymnasium {gym.__version__}")
    print("(1) action spaces under random actions")
    part1()
    print("(2) rewards optimized by the cross-entropy method")
    part2()
    print("(3) privileged information in observations")
    part3()
