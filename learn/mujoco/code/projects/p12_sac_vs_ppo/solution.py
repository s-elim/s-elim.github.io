"""Project 12 reference solution: SAC and PPO under one protocol, with the tuning that chose their settings."""

import math

import comparison

from mjcourse.rl import offpolicy, ppo

# Tuning: two configurations per method on TUNING_SEED, success on the 20 TUNING_STATES at the full budget,
# measured by tune.py. A tie keeps the course default (a rule fixed before tuning).
TUNING = {
    "ppo": [{"config": {"lr": 3e-4}, "tuning_success": 0.70}, {"config": {"lr": 1e-3}, "tuning_success": 0.10}],
    "sac": [{"config": {"init_alpha": 0.1}, "tuning_success": 1.00}, {"config": {"init_alpha": 0.03}, "tuning_success": 1.00}],
}
CHOSEN = {"ppo": {"lr": 3e-4}, "sac": {"init_alpha": 0.1}}
SAC_HIDDEN = (128, 128)          # half the course default's width: 33 s instead of 69 s per 10 000 steps


def train(method: str, seed: int, budget: int, checkpoint, config: dict | None = None):
    config = CHOSEN[method] if config is None else config
    every = comparison.EVAL_POINTS[0]
    if method == "ppo":
        cfg = ppo.PPOConfig(total_steps=budget, seed=seed, **config)
        per_iteration = cfg.num_envs * cfg.steps_per_env
        calls = []

        def evaluate(agent):                          # called when the step count crosses a multiple of `every`
            calls.append(None)
            checkpoint(math.ceil(len(calls) * every / per_iteration) * per_iteration, agent.act)
            return {}

        agent, history = ppo.train(comparison.make_env, cfg, log=None, evaluate_fn=evaluate, eval_every=every)
        return agent.act, history[-1]["steps"]
    cfg = offpolicy.OffPolicyConfig(total_steps=budget, seed=seed, hidden=SAC_HIDDEN, eval_every=every, **config)
    calls = []

    def evaluate(learner):                            # called at every multiple of `every`
        calls.append(None)
        checkpoint(len(calls) * every, lambda obs: learner.act(obs, explore=False))
        return {}

    learner, _ = offpolicy.train(comparison.make_env, cfg, evaluate_fn=evaluate, log=None)
    return (lambda obs: learner.act(obs, explore=False)), budget
