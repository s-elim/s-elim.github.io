"""Lesson 12.1: the Gymnasium API written on MuJoCo, checked, broken on purpose, and timed.

INPUT   mjcourse.envs: ReachEnv and PushEnv, each with three action modes
PROCESS (1) gymnasium's check_env on the six variants;
        (2) four broken variants: what check_env catches and what it does not;
        (3) the observation-is-a-view bug in a replay buffer;
        (4) stale kinematics: positions read after mj_step without mj_forward;
        (5) seeding: the same seed and actions reproduce an episode, reset() continues the stream;
        (6) terminated against truncated for a random and a scripted policy on Reach;
        (7) throughput: environment steps per second per action mode, and with vector environments
OUTPUT  printed tables

Run:  python examples/l12_1_gym_env.py
"""

import os
import time
import warnings

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium.utils.env_checker import check_env

import mjcourse.envs  # noqa: F401  (registers mjcourse/Reach-v0 and mjcourse/Push-v0)
from mjcourse.envs.reach import TARGET_HIGH, TARGET_LOW, ReachEnv

FAST = os.environ.get("MJC_FAST") == "1"
MODES = ("torque", "joint_delta", "ee_delta")


def checked(env) -> str:
    """Run check_env; return 'passes' or the error, plus warnings other than infinite bounds."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            check_env(env, skip_render_check=True)
            result = "passes"
        except Exception as error:  # noqa: BLE001 - we report whatever the checker raises
            result = f"{type(error).__name__}: {error}"
    extra = [str(w.message).replace("\x1b[33m", "").replace("\x1b[0m", "") for w in caught if "infinity" not in str(w.message)]
    return result + (f" (warnings: {extra})" if extra else "")


class Float64Obs(ReachEnv):
    def _get_obs(self):
        return super()._get_obs().astype(np.float64)        # the space says float32


class GlobalRng(ReachEnv):
    def _reset_task(self, options):
        self.data.mocap_pos[0] = np.random.uniform(TARGET_LOW, TARGET_HIGH)   # not self.np_random
        mujoco.mj_forward(self.model, self.data)
        self.arm.reset()


class ViewObs(ReachEnv):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(7,), dtype=np.float64)

    def _get_obs(self):
        return self.data.qpos[:7]                           # a view into MjData, not a copy


class NoTruncation(ReachEnv):
    def step(self, action):
        obs, reward, terminated, truncated, info = super().step(action)
        return obs, reward, terminated or truncated, False, info   # time limit reported as termination


def part1_2() -> None:
    for env_id in ("mjcourse/Reach-v0", "mjcourse/Push-v0"):
        for mode in MODES:
            env = gym.make(env_id, action_mode=mode).unwrapped
            print(f"  {env_id:<18} {mode:<12} {checked(env)}")
            env.close()
    print("  broken on purpose:")
    for cls, what in ((Float64Obs, "float64 observation in a float32 space"), (GlobalRng, "reset draws from np.random"),
                      (ViewObs, "observation is a view of data.qpos"), (NoTruncation, "time limit reported as terminated")):
        print(f"  {what:<40} {checked(cls())}")


def part3() -> None:
    env = ViewObs(action_mode="torque")
    buffer = [env.reset(seed=0)[0]]
    for _ in range(3):
        buffer.append(env.step(env.action_space.sample())[0])
    same = all(np.array_equal(buffer[0], b) for b in buffer)
    print(f"  4 observations stored from a view: all equal {same}; they share memory with data.qpos: "
          f"{np.shares_memory(buffer[0], env.data.qpos)}")
    env = ReachEnv(action_mode="torque")
    buffer = [env.reset(seed=0)[0]]
    for _ in range(3):
        buffer.append(env.step(env.action_space.sample())[0])
    print(f"  4 observations stored from copies: all equal {all(np.array_equal(buffer[0], b) for b in buffer)}")


def part4() -> None:
    env = ReachEnv(action_mode="torque")
    m, d = env.model, env.data
    env.reset(seed=0)
    rng = np.random.default_rng(0)
    lag, speed = [], []
    for _ in range(200):
        d.ctrl[:7] = rng.uniform(-1, 1, 7) * m.actuator_ctrlrange[:7, 1] * 0.3
        for _ in range(env.frame_skip):
            mujoco.mj_step(m, d)
        stale = d.site("ee").xpos.copy()                    # computed at the start of the last step
        mujoco.mj_forward(m, d)
        lag.append(np.linalg.norm(d.site("ee").xpos - stale))
        jac = np.zeros((3, m.nv))
        mujoco.mj_jacSite(m, d, jac, None, m.site("ee").id)
        speed.append(np.linalg.norm(jac @ d.qvel))
    lag, speed = np.array(lag), np.array(speed)
    print(f"  ee position read after mj_step vs after mj_forward, 200 samples under random torques:")
    print(f"  difference mean {1000 * lag.mean():.2f} mm, max {1000 * lag.max():.2f} mm; "
          f"ee speed times the timestep: mean {1000 * (speed * m.opt.timestep).mean():.2f} mm")


def rollout(env, seed: int, actions: np.ndarray) -> np.ndarray:
    obs = [env.reset(seed=seed)[0]]
    for a in actions:
        obs.append(env.step(a)[0])
    return np.array(obs)


def part5() -> None:
    actions = np.random.default_rng(1).uniform(-1, 1, (50, 7)).astype(np.float32)
    a, b = ReachEnv(), ReachEnv()
    same = np.array_equal(rollout(a, 3, actions), rollout(b, 3, actions))
    other = np.array_equal(rollout(a, 3, actions), rollout(b, 4, actions))
    print(f"  seed 3 twice, same actions: identical {same}; seeds 3 and 4: identical {other}")
    targets = []
    for env in (ReachEnv(), ReachEnv()):
        env.reset(seed=7)
        targets.append([env.data.mocap_pos[0].copy()] + [env.reset()[0][17:20] for _ in range(3)])
    print(f"  reset(seed=7) then reset() three times, in two fresh environments: targets identical "
          f"{all(np.allclose(x, y) for x, y in zip(*targets))}; the four targets differ from each other "
          f"{len({tuple(np.round(t, 6)) for t in targets[0]}) == 4}")


def episodes(env, policy, n: int, seed: int) -> dict:
    stats = {"terminated": 0, "truncated": 0, "length": [], "return": []}
    for i in range(n):
        obs, _ = env.reset(seed=seed + i)
        total, steps = 0.0, 0
        while True:
            obs, reward, terminated, truncated, _ = env.step(policy(obs))
            total, steps = total + reward, steps + 1
            if terminated or truncated:
                stats["terminated" if terminated else "truncated"] += 1
                stats["length"].append(steps)
                stats["return"].append(total)
                break
    return stats


def part6() -> None:
    env = ReachEnv(action_mode="ee_delta")
    n = 20 if FAST else 100
    random_policy = lambda obs: env.action_space.sample()                      # noqa: E731
    toward = lambda obs: np.clip(obs[20:23] / 0.02, -1, 1).astype(np.float32)  # noqa: E731  target minus ee, scaled
    print(f"  {'policy':<22}{'terminated':>11}{'truncated':>10}{'mean length':>13}{'mean return':>13}")
    for name, policy in (("random", random_policy), ("move toward target", toward)):
        s = episodes(env, policy, n, seed=100)
        print(f"  {name:<22}{s['terminated']:>11d}{s['truncated']:>10d}{np.mean(s['length']):>13.1f}{np.mean(s['return']):>13.2f}")


def part7() -> None:
    n = 100 if FAST else 500
    print(f"  {'environment':<20}{'mode':<13}{'steps/s':>9}{'physics steps/s':>17}")
    for env_id in ("mjcourse/Reach-v0", "mjcourse/Push-v0"):
        for mode in MODES:
            env = gym.make(env_id, action_mode=mode)
            env.reset(seed=0)
            start = time.perf_counter()
            for _ in range(n):
                _, _, terminated, truncated, _ = env.step(env.action_space.sample())
                if terminated or truncated:
                    env.reset()
            rate = n / (time.perf_counter() - start)
            print(f"  {env_id:<20}{mode:<13}{rate:>9.0f}{rate * env.unwrapped.frame_skip:>17.0f}")
            env.close()
    print(f"  vector environments, Reach joint_delta ({os.cpu_count()} CPU cores):")
    for count in ((1, 4) if FAST else (1, 4, 16, 32)):
        envs = gym.vector.AsyncVectorEnv([lambda: gym.make("mjcourse/Reach-v0", action_mode="joint_delta")] * count)
        envs.reset(seed=0)
        start = time.perf_counter()
        for _ in range(n // 5):
            envs.step(envs.action_space.sample())
        rate = count * (n // 5) / (time.perf_counter() - start)
        print(f"    {count:>3d} processes: {rate:>8.0f} environment steps/s")
        envs.close()


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}, gymnasium {gym.__version__}")
    print("(1, 2) gymnasium.utils.env_checker.check_env (render check skipped)")
    part1_2()
    print("(3) a replay buffer filled from an observation that is a view")
    part3()
    print("(4) stale kinematics after mj_step")
    part4()
    print("(5) seeding")
    part5()
    print("(6) terminated or truncated: Reach with ee_delta actions, 100 steps of 0.05 s")
    part6()
    print("(7) throughput, single process")
    part7()
