"""Project 12 tuning: every configuration in solution.TUNING, on the tuning seed and tuning states only.

    python tune.py        (about 2 minutes on 4 cores; prints the numbers recorded in solution.TUNING)
"""

import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import comparison

SOLUTION = str(Path(__file__).with_name("solution.py"))


def tune_one(method: str, config: dict) -> tuple[str, dict, float]:
    import torch

    torch.set_num_threads(1)
    module = comparison._load(SOLUTION)
    act, _ = module.train(method, comparison.TUNING_SEED, comparison.BUDGET, lambda n, a: None, config=config)
    return method, config, comparison.success(act, comparison.TUNING_STATES)


if __name__ == "__main__":
    module = comparison._load(SOLUTION)
    jobs = [(m, entry["config"]) for m in comparison.METHODS for entry in module.TUNING[m]]
    with ProcessPoolExecutor(len(jobs), mp_context=multiprocessing.get_context("spawn")) as pool:
        for method, config, value in pool.map(tune_one, *zip(*jobs)):
            print(f"{method} {config}: success {value:.2f} on {len(comparison.TUNING_STATES)} tuning states")
