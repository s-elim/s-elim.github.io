from __future__ import annotations

import time
from dataclasses import dataclass
from itertools import pairwise

import numpy as np
import torch
from torch import nn

STATE, ACTION = 16, 2


@dataclass
class Normalizer:
    s_mean: np.ndarray
    s_std: np.ndarray
    d_mean: np.ndarray
    d_std: np.ndarray


class DynamicsModel(nn.Module):
    def __init__(self, norm: Normalizer, hidden: int = 256, layers: int = 3):
        super().__init__()
        sizes = [STATE + ACTION] + [hidden] * layers
        mods = []
        for a, b in pairwise(sizes):
            mods += [nn.Linear(a, b), nn.SiLU()]
        self.net = nn.Sequential(*mods, nn.Linear(hidden, STATE))
        for name, value in (("s_mean", norm.s_mean), ("s_std", norm.s_std), ("d_mean", norm.d_mean), ("d_std", norm.d_std)):
            self.register_buffer(name, torch.as_tensor(value, dtype=torch.float32))

    def forward(self, s: torch.Tensor, a: torch.Tensor) -> torch.Tensor:
        x = torch.cat([(s - self.s_mean) / self.s_std, a], dim=-1)
        return s + self.net(x) * self.d_std + self.d_mean

    @torch.no_grad()
    def rollout(self, s0: np.ndarray, actions: np.ndarray) -> np.ndarray:
        s = torch.as_tensor(np.atleast_2d(s0), dtype=torch.float32)
        a = torch.as_tensor(actions, dtype=torch.float32)
        out = [s]
        for t in range(a.shape[1]):
            s = self(s, a[:, t])
            out.append(s)
        return torch.stack(out, 1).numpy()


def normalizer(s: np.ndarray, s2: np.ndarray) -> Normalizer:
    d = s2 - s
    return Normalizer(s.mean(0), s.std(0) + 1e-6, d.mean(0), d.std(0) + 1e-6)


def fit(episodes: list[dict], steps: int = 20_000, batch: int = 256, lr: float = 1e-3, seed: int = 0,
        objective: str = "one_step", k: int = 5, hidden: int = 256, log=None) -> tuple[DynamicsModel, list[float]]:
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    s = np.concatenate([e["states"][:-1] for e in episodes])
    s2 = np.concatenate([e["states"][1:] for e in episodes])
    model = DynamicsModel(normalizer(s, s2), hidden=hidden)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, steps)
    window = 1 if objective == "one_step" else k
    # Flat arrays: states of every episode back to back; a window may start at t if t + window stays in the episode.
    flat_s = torch.as_tensor(np.concatenate([e["states"] for e in episodes]))
    flat_a = torch.as_tensor(np.concatenate([np.concatenate([e["actions"], e["actions"][-1:]]) for e in episodes]))
    offsets = np.cumsum([0] + [len(e["states"]) for e in episodes])
    starts = torch.as_tensor(np.concatenate([o + np.arange(len(e["actions"]) - window + 1) for o, e in zip(offsets, episodes)]))
    losses, start = [], time.perf_counter()
    for step in range(steps):
        idx = starts[torch.as_tensor(rng.integers(0, len(starts), batch))]
        s_t = flat_s[idx]
        loss = 0.0
        for h in range(window):
            s_t = model(s_t, flat_a[idx + h])
            loss = loss + (((s_t - flat_s[idx + h + 1]) / model.s_std) ** 2).mean()
        loss = loss / window
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        losses.append(float(loss.detach()))
        if log and (step + 1) % 5000 == 0:
            log(f"step {step + 1}: loss {np.mean(losses[-5000:]):.5f} ({time.perf_counter() - start:.0f} s)")
    return model, losses


def horizon_errors(model: DynamicsModel, episodes: list[dict], horizons=(1, 5, 10, 20, 50), starts_per_episode: int = 4,
                   seed: int = 0) -> dict:
    from mjcourse.tabletop import OBJECTS

    rng = np.random.default_rng(seed)
    out = {h: {"pusher": [], "target": [], "worst_puck": []} for h in horizons}
    hmax = max(horizons)
    for e in episodes:
        target = OBJECTS.index(e["task"][0])
        for t0 in rng.integers(0, len(e["actions"]) - hmax + 1, starts_per_episode):
            pred = model.rollout(e["states"][t0][None], e["actions"][None, t0:t0 + hmax])[0]
            for h in horizons:
                true, p = e["states"][t0 + h], pred[h]
                puck = [np.linalg.norm(p[4 + 4 * i:6 + 4 * i] - true[4 + 4 * i:6 + 4 * i]) for i in range(3)]
                out[h]["pusher"].append(np.linalg.norm(p[:2] - true[:2]))
                out[h]["target"].append(puck[target])
                out[h]["worst_puck"].append(max(puck))
    return {h: {k: float(np.mean(v)) for k, v in d.items()} for h, d in out.items()}
