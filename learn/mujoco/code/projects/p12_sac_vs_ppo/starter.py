"""Project 12 starter: SAC on Project 11's task, compared with PPO under one protocol.

comparison.py fixes the budget, the seeds, the checkpoints, the evaluation and the report; read it, do not
edit it. Use mjcourse.rl.ppo and mjcourse.rl.offpolicy or your own implementations.

    MJC_IMPL=starter pytest projects/p12_sac_vs_ppo        (about 3 minutes on 48 cores)
"""

# Every configuration you tried, per method, on comparison.TUNING_SEED with success on TUNING_STATES:
# {"ppo": [{"config": {...}, "tuning_success": 0.0}, ...], "sac": [...]}. Give both methods the same number.
TUNING: dict[str, list[dict]] = {}


def train(method: str, seed: int, budget: int, checkpoint):
    """Train `method` ("ppo" or "sac") with `seed` for exactly `budget` environment steps.

    Call checkpoint(steps, act) at every point of comparison.EVAL_POINTS, with the environment steps used so far
    and the current deterministic policy act(obs) -> action. Return (act, steps) for the final policy.
    """
    raise NotImplementedError
