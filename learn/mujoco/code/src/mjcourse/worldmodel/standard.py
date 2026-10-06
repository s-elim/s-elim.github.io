from __future__ import annotations

import pickle
from pathlib import Path

import torch

from mjcourse.worldmodel import data, dynamics

ROOT = Path(__file__).resolve().parents[3] / "runs" / "worldmodel"
DATASETS = {
    "guided": {"seed": 0, "episodes": 1000},
    "guided_test": {"seed": 1, "episodes": 100},
    "random": {"seed": 2, "episodes": 1000, "random_share": 1.0},
    "random_test": {"seed": 3, "episodes": 100, "random_share": 1.0},
}
MODELS = {
    "one_step": {"data": "guided", "objective": "one_step"},
    "random_data": {"data": "random", "objective": "one_step"},
    "small_data": {"data": "guided", "objective": "one_step", "episodes": 50},
    "multi_step": {"data": "guided", "objective": "multi_step", "k": 5},
}


def dataset(name: str) -> list[dict]:
    path = ROOT / f"{name}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    cfg = dict(DATASETS[name])
    seed, episodes = cfg.pop("seed"), cfg.pop("episodes")
    out = data.collect(seed, episodes, **cfg)
    ROOT.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(out))
    return out


def model(name: str, steps: int = 20_000, log=None) -> dynamics.DynamicsModel:
    path = ROOT / f"{name}.pt"
    if path.exists():
        return torch.load(path, weights_only=False)
    cfg = MODELS[name]
    episodes = dataset(cfg["data"])[:cfg.get("episodes")]
    m, _ = dynamics.fit(episodes, steps=steps, objective=cfg["objective"], k=cfg.get("k", 5), log=log)
    ROOT.mkdir(parents=True, exist_ok=True)
    torch.save(m, path)
    return m
