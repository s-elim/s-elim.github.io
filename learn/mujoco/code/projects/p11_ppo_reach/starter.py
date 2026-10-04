"""Project 11 starter: PPO on the reach task, five seeds, held-out evaluation, one ablation.

rl_protocol.py fixes the task, the budget, the seeds, the held-out states and the report; read it, do not
edit it. Use the course's PPO (mjcourse.rl.ppo) or your own.

    MJC_IMPL=starter pytest projects/p11_ppo_reach        (about 2 minutes on 48 cores)
"""

ABLATION = ""   # one sentence: what the ablation changes, and why you expect it to matter


def train(seed: int, variant: str, budget: int):
    """Train one run with `seed` ("main" or "ablation" variant) for at most `budget` environment steps.

    Return (act, steps): act(obs) -> action is the policy to evaluate, and steps the environment steps used.
    """
    raise NotImplementedError
