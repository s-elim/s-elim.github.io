"""Behaviour cloning by regression, and DAgger (Level 14).

`fit` trains an MLP that maps states to actions by mean-squared error, with inputs and
outputs standardized by the dataset's statistics. `dagger` alternates: run the current
policy, ask the expert what it would have done in every state visited, add those labels
to the dataset, and fit again (Ross, Gordon and Bagnell, arXiv:1011.0686, with beta = 0
after the first iteration).
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn


class Policy:
    """A trained regressor with its normalization; callable on one state."""

    def __init__(self, net: nn.Module, x_mean, x_std, y_mean, y_std):
        self.net, self.x_mean, self.x_std, self.y_mean, self.y_std = net, x_mean, x_std, y_mean, y_std

    @torch.no_grad()
    def __call__(self, state: np.ndarray) -> np.ndarray:
        x = torch.as_tensor((np.asarray(state) - self.x_mean) / self.x_std, dtype=torch.float32)
        return self.net(x).numpy() * self.y_std + self.y_mean


def fit(states: np.ndarray, actions: np.ndarray, steps: int = 3000, hidden: int = 64, lr: float = 1e-3,
        batch: int = 256, seed: int = 0, validation: tuple[np.ndarray, np.ndarray] | None = None) -> tuple[Policy, dict]:
    """Returns the policy and the training (and validation) mean-squared error in normalized units."""
    torch.manual_seed(seed)
    x_mean, x_std = states.mean(axis=0), states.std(axis=0) + 1e-6
    y_mean, y_std = actions.mean(axis=0), actions.std(axis=0) + 1e-6
    x = torch.as_tensor((states - x_mean) / x_std, dtype=torch.float32)
    y = torch.as_tensor((actions - y_mean) / y_std, dtype=torch.float32)
    net = nn.Sequential(nn.Linear(states.shape[1], hidden), nn.Tanh(), nn.Linear(hidden, hidden), nn.Tanh(),
                        nn.Linear(hidden, actions.shape[1]))
    optimizer = torch.optim.Adam(net.parameters(), lr=lr)
    gen = torch.Generator().manual_seed(seed)
    for _ in range(steps):
        idx = torch.randint(0, len(x), (min(batch, len(x)),), generator=gen)
        loss = (net(x[idx]) - y[idx]).pow(2).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    with torch.no_grad():
        info = {"train_mse": float((net(x) - y).pow(2).mean())}
        if validation is not None:
            vx = torch.as_tensor((validation[0] - x_mean) / x_std, dtype=torch.float32)
            vy = torch.as_tensor((validation[1] - y_mean) / y_std, dtype=torch.float32)
            info["val_mse"] = float((net(vx) - vy).pow(2).mean())
    return Policy(net, x_mean, x_std, y_mean, y_std), info


def dagger(sim, expert, states: np.ndarray, actions: np.ndarray, starts_per_iteration: np.ndarray,
           iterations: int, evaluate_fn, seed: int = 0, push_rate: float = 0.0) -> list[dict]:
    """DAgger from an initial dataset. Each iteration rolls out the current policy from the
    next block of starts, labels every visited state with the expert, aggregates and refits.
    Returns one row per policy (iteration 0 is plain behaviour cloning)."""
    rows = []
    for it in range(iterations + 1):
        policy, _ = fit(states, actions, seed=seed)
        rows.append({"iteration": it, "labels": len(states), **evaluate_fn(policy)})
        if it == iterations:
            break
        for j, start in enumerate(starts_per_iteration[it]):
            visited = sim.rollout(policy, start, push_rate=push_rate, rng=np.random.default_rng([seed, 1000 + it, j])).states
            states = np.vstack([states, visited])
            actions = np.vstack([actions, np.array([expert(s) for s in visited])])
    return rows
