"""Lesson 13.1: an MDP in MuJoCo terms, a policy search you can watch, values and advantages.

INPUT   arm2.xml (planar two-link arm, torque motors, a mocap target)
PROCESS the task: bring the arm's ee site to a random target in its plane within 2 s.
        Policy: torques u = clip(W_e e + W_v qdot + b), e = target - ee (x, z), held for
        20 ms (10 physics steps); 10 parameters. With "gravity features" the policy also
        sees (cos q1, cos(q1 + q2)) through W_g: 14 parameters. Reward per control step:
        minus the distance (m); return = sum over 100 control steps.
        (1) the MDP spelled out: state, observation, action, reward, discount, horizon;
        (2) the cross-entropy method on the parameters (population 32, best 6 refitted,
            4 shared random targets per iteration, 60 iterations), 5 seeds per policy class run in
            parallel: learning curves, the final mean policy on 100 held-out targets, and a
            Mann-Whitney test across seeds;
        (3) values: with Gaussian noise on the torques, Monte Carlo estimates of V(s0) and
            of Q(s0, a) for actions around the policy's mean, and the advantages Q - V
OUTPUT  printed tables (the browser lab runs the same search)

Run:  python examples/l13_1_policy_search.py
"""

import math
import os
from multiprocessing import Pool

import mujoco
import numpy as np
from scipy.stats import mannwhitneyu

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"
SKIP, STEPS = 10, 100                       # physics steps per control step; control steps per episode (2 s)
GAMMA = 0.99
SCALE = np.r_[np.full(4, 100.0), np.full(4, 10.0), np.full(2, 10.0), np.full(4, 10.0)]   # N m/m, N m s/rad, N m, N m


def make():
    model = mujoco.MjModel.from_xml_path(str(model_path("arm2")))
    return model, mujoco.MjData(model)


def sample_targets(rng: np.random.Generator, n: int) -> np.ndarray:
    """Targets in the arm's plane: radius 0.35-0.85 m from the shoulder, angle -0.5 to 1.5 rad."""
    r, a = rng.uniform(0.35, 0.85, n), rng.uniform(-0.5, 1.5, n)
    return np.c_[r * np.cos(a), 1.0 + r * np.sin(a)]                  # x, z (shoulder at z = 1)


def policy(theta: np.ndarray, e: np.ndarray, qdot: np.ndarray, q: np.ndarray) -> np.ndarray:
    """10 parameters: W_e, W_v, b. 14 parameters: also W_g on (cos q1, cos(q1 + q2))."""
    p = theta * SCALE[:len(theta)]
    u = p[0:4].reshape(2, 2) @ e + p[4:8].reshape(2, 2) @ qdot + p[8:10]
    if len(theta) == 14:
        u = u + p[10:14].reshape(2, 2) @ np.array([math.cos(q[0]), math.cos(q[0] + q[1])])
    return u


def rollout(model, data, theta, target, noise: float = 0.0, rng=None, first_action=None) -> tuple[float, float, list[float]]:
    """Returns (return, final distance, rewards). `first_action` overrides the first control."""
    mujoco.mj_resetDataKeyframe(model, data, model.key("bent").id)
    data.mocap_pos[0] = [target[0], 0.0, target[1]]
    mujoco.mj_forward(model, data)
    rewards = []
    lo, hi = model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1]
    for k in range(STEPS):
        ee = data.site_xpos[0][[0, 2]]
        u = policy(theta, target - ee, data.qvel, data.qpos) if first_action is None or k > 0 else first_action
        if noise > 0 and (first_action is None or k > 0):
            u = u + rng.normal(0.0, noise, 2)
        data.ctrl[:] = np.clip(u, lo, hi)
        for _ in range(SKIP):
            mujoco.mj_step(model, data)
        mujoco.mj_forward(model, data)
        rewards.append(-float(np.linalg.norm(target - data.site_xpos[0][[0, 2]])))
    return float(sum(rewards)), -rewards[-1], rewards


def cem(seed: int, iterations: int, size: int = 10, population: int = 32, elite: int = 6, targets_per: int = 4):
    rng = np.random.default_rng(seed)
    model, data = make()
    mean, std = np.zeros(size), np.full(size, 0.5)
    curve = []
    for _ in range(iterations):
        targets = sample_targets(rng, targets_per)                     # shared by the whole population
        thetas = rng.normal(mean, std, (population, size))
        returns = np.array([np.mean([rollout(model, data, th, t)[0] for t in targets]) for th in thetas])
        best = thetas[np.argsort(returns)[-elite:]]
        mean, std = best.mean(axis=0), best.std(axis=0) + 0.01
        curve.append((returns.mean(), np.sort(returns)[-elite:].mean(), returns.max()))
    return mean, curve


def evaluate(theta, targets) -> tuple[float, float, float]:
    """Success rate (final distance < 2 cm), median and 90th percentile of the final distance (m)."""
    model, data = make()
    finals = np.array([rollout(model, data, theta, t)[1] for t in targets])
    return float(np.mean(finals < 0.02)), float(np.median(finals)), float(np.percentile(finals, 90))


def part1() -> None:
    model, _ = make()
    dt = model.opt.timestep * SKIP
    print(f"  state      q (2), qdot (2), target (2): what the simulator needs to continue")
    print(f"  observed   e = target - ee (2), qdot (2): the policy does not see q, so gravity compensation can only be")
    print(f"             approximate (the observation is not a Markov state for this policy class)")
    print(f"  action     shoulder and elbow torques, limits {model.actuator_ctrlrange[:, 1]} N m, held {1000 * dt:.0f} ms")
    print(f"  reward     -|e| (m) per control step; episode {STEPS} control steps = {STEPS * dt:.1f} s")
    print(f"  discount   gamma {GAMMA}: effective horizon 1/(1 - gamma) = {1 / (1 - GAMMA):.0f} steps = {dt / (1 - GAMMA):.1f} s")


HELD_OUT = sample_targets(np.random.default_rng(1234), 100)            # never used during the search


def search_and_evaluate(job: tuple[int, int, int]) -> tuple[int, int, np.ndarray, list, tuple]:
    size, seed, iterations = job
    theta, curve = cem(seed, iterations, size)
    return size, seed, theta, curve, evaluate(theta, HELD_OUT)


def part2() -> np.ndarray:
    iterations, seeds = (6, 1) if FAST else (60, 5)
    jobs = [(size, seed, iterations) for size in (10, 14) for seed in range(seeds)]
    if FAST:
        results = [search_and_evaluate(j) for j in jobs]
    else:
        with Pool(len(jobs)) as pool:
            results = pool.map(search_and_evaluate, jobs)
    marks = sorted({0, 9, 19, 39, iterations - 1} & set(range(iterations)))
    summary = {}
    for size, label in ((10, "observes e, qdot (10 parameters)"), (14, "also observes cos q1, cos(q1 + q2) (14 parameters)")):
        print(f"  policy {label}")
        for _, seed, _, curve, (success, median, p90) in [r for r in results if r[0] == size]:
            print(f"    seed {seed}: elite mean return at iterations " + ", ".join(f"{i + 1}: {curve[i][1]:.1f}" for i in marks)
                  + f"; held-out: success {success:.0%}, final distance median {1000 * median:.1f} mm, 90th percentile {1000 * p90:.1f} mm")
        summary[size] = np.array([r[4] for r in results if r[0] == size])
    if seeds > 1:
        for k, name in ((0, "success rate"), (1, "median final distance")):
            test = mannwhitneyu(summary[14][:, k], summary[10][:, k], alternative="two-sided")
            print(f"  {name} per seed, 14 against 10 parameters: medians {np.median(summary[14][:, k]):.3f} against "
                  f"{np.median(summary[10][:, k]):.3f}; Mann-Whitney U {test.statistic:.0f}, two-sided p = {test.pvalue:.3f}")
    theta = next(r[2] for r in results if r[0] == 10 and r[1] == 0)
    print(f"  parameters, first policy, seed 0 (W_e N m/m, W_v N m s/rad, b N m): {np.round(theta * SCALE[:10], 1)}")
    return theta


def part3(theta: np.ndarray) -> None:
    model, data = make()
    target, noise, n = np.array([0.70, 1.13]), 1.0, (40 if FAST else 300)
    rng = np.random.default_rng(7)
    discounted = lambda rewards: sum(GAMMA**k * r for k, r in enumerate(rewards))   # noqa: E731
    mujoco.mj_resetDataKeyframe(model, data, model.key("bent").id)
    data.mocap_pos[0] = [target[0], 0.0, target[1]]
    mujoco.mj_forward(model, data)
    mean_action = np.clip(policy(theta, target - data.site_xpos[0][[0, 2]], data.qvel, data.qpos),
                          model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
    start_distance = np.linalg.norm(target - data.site_xpos[0][[0, 2]])
    v = [discounted(rollout(model, data, theta, target, noise, rng)[2]) for _ in range(n)]
    print(f"  s0: the bent keyframe, target {target} ({100 * start_distance:.1f} cm away); "
          f"torque noise sigma {noise} N m; {n} rollouts per estimate")
    print(f"  V(s0) = {np.mean(v):.3f} +- {np.std(v) / math.sqrt(n):.3f} (standard error)")
    print(f"  {'first action a (N m)':<26}{'Q(s0, a)':>10}{'A = Q - V':>11}")
    for label, delta in (("policy mean", (0, 0)), ("mean + (5, 0)", (5, 0)), ("mean - (5, 0)", (-5, 0)),
                         ("mean + (0, 5)", (0, 5)), ("mean - (0, 5)", (0, -5)), ("zero torque", None)):
        a = np.zeros(2) if delta is None else mean_action + np.array(delta)
        q = [discounted(rollout(model, data, theta, target, noise, rng, first_action=a)[2]) for _ in range(n)]
        print(f"  {label + ' ' + str(np.round(a, 1)):<26}{np.mean(q):>10.3f}{np.mean(q) - np.mean(v):>11.3f}")


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}")
    print("(1) the reach task as an MDP")
    part1()
    print("(2) cross-entropy method on a linear feedback policy")
    theta = part2()
    print("(3) value and action values of the learned policy, by Monte Carlo")
    part3(theta)
