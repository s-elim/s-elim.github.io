"""Project 11 reference solution: the course's PPO on the reach task, and an ablation of its clipping."""

import rl_protocol

from mjcourse.rl import ppo

ABLATION = "no clipping: the surrogate's clip range raised from 0.2 to 10, so nothing limits the policy update"


def train(seed: int, variant: str, budget: int):
    cfg = ppo.PPOConfig(total_steps=budget, seed=seed, clip=0.2 if variant == "main" else 10.0)
    agent, history = ppo.train(rl_protocol.make_env, cfg, log=None)
    return agent.act, history[-1]["steps"]
