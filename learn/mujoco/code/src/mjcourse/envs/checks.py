"""Checks gymnasium's env_checker does not make (Lessons 12.1 and 12.2).

Each returns a value a test can assert on:
    observations_are_copies(env)       stored observations do not change after later steps
    truncation_is_reported(env)        the time limit gives truncated=True, terminated=False
    reproducible(env, seed)            the same seed and actions give the same episode
    undeclared_sources(env, allowed)   observation components whose declared source is not a real sensor
    perturbation_leaks(env, ...)       quantities no sensor reports that nevertheless change the observation
"""

from __future__ import annotations

import mujoco
import numpy as np

REAL_SOURCES = frozenset({"joint encoders", "joint encoders, differentiated", "forward kinematics of the joint encoders",
                          "camera tracker", "task specification"})


def observations_are_copies(env, steps: int = 3, seed: int = 0) -> bool:
    stored = [env.reset(seed=seed)[0]]
    snapshot = [stored[0].copy()]
    for _ in range(steps):
        obs = env.step(env.action_space.sample())[0]
        stored.append(obs)
        snapshot.append(obs.copy())
    return all(np.array_equal(a, b) for a, b in zip(stored, snapshot))


def truncation_is_reported(env, seed: int = 0) -> bool:
    """Runs a zero action to the time limit; true if the last step is truncated and not terminated
    (and the episode did not end earlier)."""
    env.reset(seed=seed)
    zero = np.zeros(env.action_space.shape, env.action_space.dtype)
    for t in range(env.max_episode_steps):
        _, _, terminated, truncated, _ = env.step(zero)
        last = t == env.max_episode_steps - 1
        if terminated or truncated:
            return last and truncated and not terminated
    return False


def reproducible(make_env, seed: int = 0, steps: int = 20) -> bool:
    actions = np.random.default_rng(seed).uniform(-1, 1, (steps,) + make_env().action_space.shape).astype(np.float32)
    runs = []
    for _ in range(2):
        env = make_env()
        obs = [env.reset(seed=seed)[0]]
        obs += [env.step(a)[0] for a in actions]
        runs.append(np.array(obs))
        env.close()
    return np.array_equal(runs[0], runs[1])


def undeclared_sources(env, allowed=REAL_SOURCES) -> list[str]:
    return [f"{name} ({source})" for name, source in env.observation_sources.items() if source not in allowed]


def perturbation_leaks(env, body: str = "puck", geom: str = "puck", seed: int = 0, warmup: int = 20) -> list[str]:
    """At one instant, change quantities no real sensor reports (the object's velocity, mass,
    friction and contact stiffness) and recompute the observation; it must not change."""
    env.reset(seed=seed)
    push = np.zeros(env.action_space.shape, env.action_space.dtype)
    push[0] = 1.0
    for _ in range(warmup):                                     # move, and touch the object
        env.step(push)
    m, d = env.model, env.data
    b, g = m.body(body).id, m.geom(geom).id
    dof = m.body_dofadr[b]
    spec = mujoco.mjtState.mjSTATE_FULLPHYSICS
    mujoco.mj_forward(m, d)                                     # baseline from a fresh state, so a merely stale
    base = env._get_obs().copy()                                # observation is not reported as a leak

    def bump_velocity():
        d.qvel[dof:dof + m.body_dofnum[b]] += 0.3

    perturbations = {"object velocity": bump_velocity,
                     "object mass": lambda: m.body_mass.__setitem__(b, 2 * m.body_mass[b]),
                     "object friction": lambda: m.geom_friction.__setitem__(g, 2 * m.geom_friction[g]),
                     "contact stiffness": lambda: m.geom_solref.__setitem__(g, [0.005, 1.0])}
    leaks = []
    for name, apply in perturbations.items():
        state = np.zeros(mujoco.mj_stateSize(m, spec))
        mujoco.mj_getState(m, d, state, spec)
        saved = m.body_mass.copy(), m.geom_friction.copy(), m.geom_solref.copy()
        apply()
        mujoco.mj_forward(m, d)
        if not np.array_equal(env._get_obs(), base):
            leaks.append(name)
        m.body_mass[:], m.geom_friction[:], m.geom_solref[:] = saved
        mujoco.mj_setState(m, d, state, spec)
        mujoco.mj_forward(m, d)
    return leaks
