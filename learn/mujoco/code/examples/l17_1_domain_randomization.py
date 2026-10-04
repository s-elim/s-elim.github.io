"""Lesson 17.1: domain randomization for the push task, measured against held-out parameters (Level 17 checkpoint).

INPUT   mjcourse.envs.PushEnv (end-effector actions whose target leads the tool by at most 2 cm,
        episodes of 5 s, success judged where the puck ends)
PROCESS (0) a pitfall: the puck's mass changed in the model with and without mj_setConst, and
            with one derived field at a time recomputed;
        a parametric pushing controller (push speed, slowdown gain near the goal, push depth,
        lateral tolerance) tuned by the cross-entropy method twice:
        (1) on nominal dynamics (puck 0.2 kg, friction 0.5);
        (2) with puck mass drawn from 0.1-0.4 kg and friction from 0.25-1.0 in every episode;
        (3) both evaluated on a grid of mass and friction values reaching beyond the
            randomized range, 24 tasks per cell, the same tasks for both controllers;
        (4) an open-loop strike: the puck is launched toward the goal at v = sqrt(2 mu_hat g D)
            for its distance D and an assumed friction mu_hat, then slides; mu_hat chosen on
            nominal friction and on the randomized range; success against the true friction;
            first, the simulator's sliding distance against v^2 / (2 mu g); then a strike that
            first identifies the friction from a probe launch, after checking the probe's estimates;
            last, a strike told the true friction, which separates estimation error from model error
OUTPUT  printed tables

Run:  python examples/l17_1_domain_randomization.py          (about 3 minutes on 24 CPU cores)
"""

import math
import os
from multiprocessing import Pool

import mujoco
import numpy as np

from mjcourse.envs import PushEnv

FAST = os.environ.get("MJC_FAST") == "1"
R_PUCK, HALF, DT = 0.035, 0.008, 0.05
NOMINAL = {"puck_mass": 0.2, "friction": 0.5}
TRAIN_RANGE = {"puck_mass": (0.1, 0.4), "friction": (0.25, 1.0)}
GRID = {"puck_mass": (0.05, 0.1, 0.2, 0.4, 0.8), "friction": (0.1, 0.25, 0.5, 1.0, 1.5)}


def decode(theta: np.ndarray) -> dict:
    s = 1 / (1 + np.exp(-np.asarray(theta)))
    return {"speed": 0.05 + 0.25 * s[0], "slow_gain": 0.5 + 4.5 * s[1], "depth": 0.002 + 0.02 * s[2], "lateral": 0.005 + 0.03 * s[3]}


def pusher(p: dict, obs: np.ndarray) -> np.ndarray:
    """Get behind the puck on its line to the goal, then push along that line, slowing near the goal."""
    tcp, puck, goal = obs[14:16], obs[17:19], obs[19:21]
    to_goal = goal - puck
    d = np.linalg.norm(to_goal)
    if d < 0.01:
        return np.zeros(2, np.float32)
    u = to_goal / d
    n = np.array([-u[1], u[0]])
    rel = tcp - puck
    along, lateral = rel @ u, rel @ n
    contact = -(R_PUCK + HALF)
    if along > contact + 0.015 or abs(lateral) > p["lateral"]:          # not behind the puck: reposition
        side = n * math.copysign(R_PUCK + HALF + 0.03, lateral if lateral != 0 else 1.0)
        target = puck + side if along > contact else puck - (R_PUCK + HALF + 0.03) * u
        speed = 0.3
    else:                                                                # push
        target = puck - (R_PUCK + HALF - p["depth"]) * u
        speed = min(p["speed"], p["slow_gain"] * d)
    step = target - tcp
    dist = np.linalg.norm(step)
    move = min(speed * DT, dist)
    return np.clip(step / max(dist, 1e-9) * move / 0.02, -1, 1).astype(np.float32)


_ENV = {}


def episode(job) -> float:
    """One episode: (theta, task seed, mass, friction) -> 1 success, 0 failure, nan if the simulation diverged.
    MuJoCo resets a diverging simulation to its initial state (time 0), so a clock that runs backwards, or a
    controller that fails at the reset pose, marks the episode."""
    theta, seed, mass, friction = job
    if "pusher" not in _ENV:
        _ENV["pusher"] = PushEnv(action_mode="ee_delta", terminate_on_success=False, max_lead=0.02)   # force at most about 40 N
    env, p = _ENV["pusher"], decode(theta)
    obs, _ = env.reset(seed=int(seed), options={"puck_mass": mass, "friction": friction})
    done, last_time = False, 0.0
    try:
        while not done:
            obs, _, terminated, truncated, info = env.step(pusher(p, obs))
            if env.data.time < last_time:
                return float("nan")
            last_time, done = env.data.time, terminated or truncated
    except np.linalg.LinAlgError:
        return float("nan")
    return float(info["distance"] < env.success_radius)


STALE = ("body_invweight0", "dof_invweight0", "dof_M0", "body_subtreemass")    # what mj_setConst changes after a mass edit


def stale_constants(mass: float, episodes: int, repair=None) -> int:
    """Diverged episodes when the puck's mass and inertia are edited directly. repair=None takes the
    environment's path (edit, mj_setConst, reset); otherwise only the listed derived fields are recomputed."""
    env = PushEnv(action_mode="ee_delta", terminate_on_success=False, max_lead=0.02)
    m, puck, diverged = env.model, env.puck, 0
    nominal_mass, nominal_inertia = m.body_mass[puck], m.body_inertia[puck].copy()
    m.body_mass[puck], m.body_inertia[puck] = mass, nominal_inertia * mass / nominal_mass
    mujoco.mj_setConst(m, env.data)
    correct = {k: getattr(m, k).copy() for k in STALE}                # the constants for the edited mass
    m.body_mass[puck], m.body_inertia[puck] = nominal_mass, nominal_inertia
    mujoco.mj_setConst(m, env.data)
    for seed in range(episodes):
        if repair is None:
            obs, _ = env.reset(seed=seed, options={"puck_mass": mass})
        else:                                                      # the same edit made directly
            obs, _ = env.reset(seed=seed)
            m.body_mass[puck], m.body_inertia[puck] = mass, nominal_inertia * mass / nominal_mass
            for k in repair:
                getattr(m, k)[:] = correct[k]
        try:
            last, done = 0.0, False
            while not done:
                obs, _, terminated, truncated, _ = env.step(pusher(decode(np.zeros(4)), obs))
                if env.data.time < last:
                    diverged += 1
                    break
                last, done = env.data.time, terminated or truncated
        except np.linalg.LinAlgError:
            diverged += 1
        m.body_mass[puck], m.body_inertia[puck] = nominal_mass, nominal_inertia
        mujoco.mj_setConst(m, env.data)                            # leave the model as it was
    env.close()
    return diverged


def cem(pool, randomize: bool, seed: int, iterations: int, population: int, episodes: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    mean, std = np.zeros(4), np.full(4, 1.5)
    for it in range(iterations):
        thetas = rng.normal(mean, std, (population, 4))
        tasks = rng.integers(0, 10**6, episodes)                          # shared tasks within an iteration
        if randomize:
            params = [(rng.uniform(*TRAIN_RANGE["puck_mass"]), rng.uniform(*TRAIN_RANGE["friction"])) for _ in range(episodes)]
        else:
            params = [(NOMINAL["puck_mass"], NOMINAL["friction"])] * episodes
        jobs = [(th, t, m, f) for th in thetas for t, (m, f) in zip(tasks, params)]
        scores = np.nan_to_num(np.array(pool.map(episode, jobs))).reshape(population, episodes).mean(axis=1)
        elite = thetas[np.argsort(scores)[-max(2, population // 5):]]
        mean, std = elite.mean(axis=0), elite.std(axis=0) + 0.05
        if it in (0, iterations - 1):
            print(f"    iteration {it + 1:>2}: mean success {scores.mean():.2f}, best {scores.max():.2f}")
    return mean


def strike(job) -> tuple[float, float, float]:
    """Launch the puck toward the goal at sqrt(2 mu_hat g D) and let it slide for 3 s with the arm holding
    its start pose: (final distance to the goal, distance the puck travelled, largest tilt of its axis
    from vertical in degrees, sampled every 50 ms)."""
    mu_hat, seed, friction = job
    if "strike" not in _ENV:
        _ENV["strike"] = PushEnv(action_mode="ee_delta", terminate_on_success=False, max_episode_steps=60)
    env = _ENV["strike"]
    env.reset(seed=int(seed), options={"friction": friction})
    start, goal = env.puck_xy(), env.goal_xy()
    distance = np.linalg.norm(goal - start)
    dof = env.model.jnt_dofadr[env.model.joint("puck").id]
    env.data.qvel[dof:dof + 2] = math.sqrt(2 * mu_hat * 9.81 * distance) * (goal - start) / distance
    tilt = 0.0
    for _ in range(env.max_episode_steps):
        env.step(np.zeros(2, np.float32))
        tilt = max(tilt, math.degrees(math.acos(np.clip(env.data.xmat[env.puck][8], -1.0, 1.0))))
    return float(np.linalg.norm(env.puck_xy() - goal)), float(np.linalg.norm(env.puck_xy() - start)), tilt


PROBE = 0.3                                          # probe launch speed (m/s)


def probe_estimate(speed: float, friction: float, seed: int = 3) -> tuple[float, float]:
    """Launch toward the goal at `speed`, wait 1 s: (distance slid, friction estimated as v^2 / (2 g d))."""
    if "strike" not in _ENV:
        _ENV["strike"] = PushEnv(action_mode="ee_delta", terminate_on_success=False, max_episode_steps=60)
    env = _ENV["strike"]
    env.reset(seed=seed, options={"friction": friction})
    dof = env.model.jnt_dofadr[env.model.joint("puck").id]
    start, goal = env.puck_xy(), env.goal_xy()
    env.data.qvel[dof:dof + 2] = speed * (goal - start) / np.linalg.norm(goal - start)
    for _ in range(20):
        env.step(np.zeros(2, np.float32))
    slid = float(np.linalg.norm(env.puck_xy() - start))
    return slid, speed**2 / (2 * 9.81 * max(slid, 1e-4))


def probe_then_strike(job) -> float:
    """Launch at PROBE m/s, wait 1 s, estimate mu from the slide (v0^2 / (2 g d)), then strike from where
    the puck stopped. Returns the final distance to the goal."""
    _, seed, friction = job
    if "strike" not in _ENV:
        _ENV["strike"] = PushEnv(action_mode="ee_delta", terminate_on_success=False, max_episode_steps=60)
    env = _ENV["strike"]
    env.reset(seed=int(seed), options={"friction": friction})
    dof = env.model.jnt_dofadr[env.model.joint("puck").id]

    def launch(speed: float, steps: int) -> float:
        start, goal = env.puck_xy(), env.goal_xy()
        env.data.qvel[dof:dof + 2] = speed * (goal - start) / np.linalg.norm(goal - start)
        for _ in range(steps):
            env.step(np.zeros(2, np.float32))
        return float(np.linalg.norm(env.puck_xy() - start))

    slid = launch(PROBE, 20)
    mu_hat = PROBE**2 / (2 * 9.81 * max(slid, 1e-4))
    launch(math.sqrt(2 * mu_hat * 9.81 * np.linalg.norm(env.goal_xy() - env.puck_xy())), 40)
    return float(np.linalg.norm(env.puck_xy() - env.goal_xy()))


MU_GRID = (0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5)


def strike_success(pool, mu_hat: float, frictions, tasks) -> float:
    jobs = [(mu_hat, t, f) for f, t in zip(frictions, tasks)]
    return float(np.mean([d < 0.03 for d, _, _ in pool.map(strike, jobs)]))


def part4(pool, per_cell: int) -> dict:
    """The strike: physics check, then mu_hat chosen by grid search on nominal and on randomized friction."""
    print("  sliding distance after a launch at 0.4 m/s: simulated against v^2 / (2 mu g)")
    for mu in (0.1, 0.25, 0.5, 1.0):
        # mu_hat chosen so that the launch speed is 0.4 m/s for this task's distance
        env = PushEnv(action_mode="ee_delta", max_episode_steps=60)
        env.reset(seed=3)
        d = np.linalg.norm(env.goal_xy() - env.puck_xy())
        env.close()
        _, travelled, _ = strike((0.16 / (2 * 9.81 * d), 3, mu))
        print(f"    mu {mu:<5} simulated {1000 * travelled:6.1f} mm, predicted {1000 * 0.16 / (2 * mu * 9.81):6.1f} mm")
    print("  friction estimated by a probe launch (one task), at two probe speeds:")
    for speed in (0.15, PROBE):
        cells = []
        for mu in (0.05, 0.25, 0.5, 1.0, 1.5):
            slid, mu_hat = probe_estimate(speed, mu)
            cells.append(f"{mu}: {1000 * slid:.1f} mm -> {mu_hat:.2f}")
        print(f"    {speed} m/s   " + ";  ".join(cells))
    rng = np.random.default_rng(17)
    train_tasks = rng.integers(0, 10**6, 64)
    candidates = np.round(np.arange(0.05, 1.51, 0.05), 2)
    chosen = {}
    for name, frictions in (("nominal", np.full(64, NOMINAL["friction"])), ("randomized", rng.uniform(*TRAIN_RANGE["friction"], 64))):
        scores = [strike_success(pool, c, frictions, train_tasks) for c in candidates]
        chosen[name] = float(candidates[int(np.argmax(scores))])
        print(f"  chosen on {name} friction: mu_hat {chosen[name]} (training success {max(scores):.2f})")
    tasks = np.random.default_rng(1718).integers(0, 10**6, per_cell)
    print(f"  success against the true friction, {per_cell} held-out tasks each:")
    print(f"    {'true friction':<34}" + "".join(f"{m:>7}" for m in MU_GRID))
    table = {}
    for name, mu_hat in chosen.items():
        table[name] = [strike_success(pool, mu_hat, np.full(per_cell, m), tasks) for m in MU_GRID]
        print(f"    {f'mu_hat {mu_hat} (chosen on {name})':<34}" + "".join(f"{v:>7.2f}" for v in table[name]))
    table["probe"] = [float(np.mean([d < 0.03 for d in pool.map(probe_then_strike, [(0, t, m) for t in tasks])])) for m in MU_GRID]
    print(f"    {f'probe at {PROBE} m/s, then strike':<34}" + "".join(f"{v:>7.2f}" for v in table["probe"]))
    oracle = [pool.map(strike, [(m, t, m) for t in tasks]) for m in MU_GRID]
    print(f"    {'oracle: mu_hat = true mu':<34}" + "".join(f"{np.mean([d < 0.03 for d, _, _ in o]):>7.2f}" for o in oracle))
    print(f"    {'  its largest tilt (deg, median)':<34}" + "".join(f"{np.median([a for _, _, a in o]):>7.1f}" for o in oracle))
    return table


def grid(pool, theta, tasks) -> tuple[np.ndarray, np.ndarray]:
    """Success per cell (diverged episodes count as failures) and the number of diverged episodes per cell."""
    jobs = [(theta, t, m, f) for m in GRID["puck_mass"] for f in GRID["friction"] for t in tasks]
    out = np.array(pool.map(episode, jobs)).reshape(len(GRID["puck_mass"]), len(GRID["friction"]), len(tasks))
    return np.nan_to_num(out).mean(axis=2), np.isnan(out).sum(axis=2)


def show(table: np.ndarray, fmt: str = "{:>7.2f}") -> None:
    print("      mass \\ friction " + "".join(f"{f:>7}" for f in GRID["friction"]))
    for m, row in zip(GRID["puck_mass"], table):
        print(f"      {m:>8.2f} kg     " + "".join(fmt.format(v) for v in row))


def inside(m: float, f: float) -> bool:
    return TRAIN_RANGE["puck_mass"][0] <= m <= TRAIN_RANGE["puck_mass"][1] and TRAIN_RANGE["friction"][0] <= f <= TRAIN_RANGE["friction"][1]


if __name__ == "__main__":
    iterations, population, episodes, per_cell = (2, 8, 2, 4) if FAST else (12, 24, 8, 24)
    print(f"CEM: {population} candidates x {episodes} episodes per iteration, {iterations} iterations; "
          f"randomized range: mass {TRAIN_RANGE['puck_mass']} kg, friction {TRAIN_RANGE['friction']}")
    n0 = 3 if FAST else 10
    print(f"(0) puck mass edited in the model, {n0} episodes each: diverged episodes")
    for mass in (0.2, 0.4, 0.8):
        print(f"    {mass} kg: without mj_setConst {stale_constants(mass, n0, ())}/{n0}, with it {stale_constants(mass, n0)}/{n0}")
    print("    0.4 kg, without mj_setConst but with one derived field recomputed: "
          + ", ".join(f"{k} {stale_constants(0.4, n0, (k,))}/{n0}" for k in STALE))
    with Pool(8 if FAST else 24) as pool:
        print("(1) tuned on nominal dynamics")
        theta_nominal = cem(pool, False, 0, iterations, population, episodes)
        print("(2) tuned with randomized mass and friction")
        theta_random = cem(pool, True, 0, iterations, population, episodes)
        for name, th in (("nominal", theta_nominal), ("randomized", theta_random)):
            print(f"  {name:<11} parameters: " + ", ".join(f"{k} {v:.3f}" for k, v in decode(th).items()))
        tasks = np.random.default_rng(1717).integers(0, 10**6, per_cell)
        print(f"(3) success on {per_cell} held-out tasks per cell")
        tables = {}
        for name, th in (("tuned on nominal", theta_nominal), ("tuned with randomization", theta_random)):
            tables[name], diverged = grid(pool, th, tasks)
            print(f"  {name}")
            show(tables[name])
            if diverged.any():
                print("    episodes in which the simulation diverged (counted as failures):")
                show(diverged, "{:>7.0f}")
        print("(4) an open-loop strike")
        strikes = part4(pool, per_cell)
    cells = [(i, j) for i, m in enumerate(GRID["puck_mass"]) for j, f in enumerate(GRID["friction"])]
    print("mean success inside the randomized range, outside it, and at the nominal values (pusher: grid cells; strike: frictions):")
    for name, table in tables.items():
        ins = np.mean([table[i, j] for i, j in cells if inside(GRID["puck_mass"][i], GRID["friction"][j])])
        out = np.mean([table[i, j] for i, j in cells if not inside(GRID["puck_mass"][i], GRID["friction"][j])])
        print(f"  {'pusher, ' + name:<36} inside {ins:.2f}, outside {out:.2f}, nominal {table[2, 2]:.2f}")
    inside_mu = [i for i, m in enumerate(MU_GRID) if TRAIN_RANGE["friction"][0] <= m <= TRAIN_RANGE["friction"][1]]
    for name, row in strikes.items():
        ins = np.mean([row[i] for i in inside_mu])
        out = np.mean([row[i] for i in range(len(MU_GRID)) if i not in inside_mu])
        label = "probe, then strike" if name == "probe" else f"strike, mu_hat from {name}"
        print(f"  {label:<36} inside {ins:.2f}, outside {out:.2f}, nominal {row[MU_GRID.index(0.5)]:.2f}")
