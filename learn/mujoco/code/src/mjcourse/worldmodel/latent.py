from __future__ import annotations

import math
import time

import numpy as np
import torch
from torch import nn

from mjcourse import tabletop as tt

LATENT = 32
# The pucks' colours as the top camera renders them (lit), measured from their segmentation masks.
COLOURS = {"red": (0.955, 0.24, 0.207), "green": (0.316, 0.907, 0.374), "blue": (0.313, 0.495, 0.973)}


class LatentModel(nn.Module):
    def __init__(self, positions: bool):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, 4, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, 4, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(64, 64, 4, stride=2, padding=1), nn.ReLU(),
            nn.Flatten(), nn.Linear(64 * 8 * 8, LATENT))
        self.decoder_in = nn.Linear(LATENT, 64 * 8 * 8)
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(64, 64, 4, stride=2, padding=1), nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 4, stride=2, padding=1), nn.ReLU(),
            nn.ConvTranspose2d(32, 3, 4, stride=2, padding=1), nn.Sigmoid())
        self.transition = nn.Sequential(nn.Linear(LATENT + 2, 256), nn.SiLU(), nn.Linear(256, 256), nn.SiLU(),
                                        nn.Linear(256, LATENT))
        self.probe = nn.Linear(LATENT, 8) if positions else None

    def encode(self, img: torch.Tensor) -> torch.Tensor:
        return self.encoder(img)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.decoder_in(z).view(-1, 64, 8, 8))

    def step(self, z: torch.Tensor, a: torch.Tensor) -> torch.Tensor:
        return z + self.transition(torch.cat([z, a], dim=-1))

    @torch.no_grad()
    def predict(self, image: np.ndarray, actions: np.ndarray) -> np.ndarray:
        z = self.encode(_tensor(image[None]))
        frames = [self.decode(z)]
        for a in torch.as_tensor(actions, dtype=torch.float32):
            z = self.step(z, a[None])
            frames.append(self.decode(z))
        return (torch.cat(frames).permute(0, 2, 3, 1).numpy() * 255).round().astype(np.uint8)


def _tensor(images: np.ndarray) -> torch.Tensor:
    return torch.as_tensor(images).permute(0, 3, 1, 2).float() / 255.0


def positions_of(states: np.ndarray) -> np.ndarray:
    return np.concatenate([states[..., 0:2]] + [states[..., 4 + 4 * i:6 + 4 * i] for i in range(3)], axis=-1)


def fit(episodes: list[dict], objective: str, steps: int = 8000, batch: int = 32, k: int = 5, lr: float = 1e-3,
        seed: int = 0, log=None) -> LatentModel:
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = LatentModel(positions=objective == "positions")
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    starts = [(i, t) for i, e in enumerate(episodes) for t in range(len(e["actions"]) - k + 1)]
    start = time.perf_counter()
    for step in range(steps):
        pick = [starts[j] for j in rng.integers(0, len(starts), batch)]
        imgs = _tensor(np.stack([episodes[i]["images"][t:t + k + 1] for i, t in pick]).reshape(-1, 64, 64, 3)).view(batch, k + 1, 3, 64, 64)
        acts = torch.as_tensor(np.stack([episodes[i]["actions"][t:t + k] for i, t in pick]), dtype=torch.float32)
        pos = torch.as_tensor(np.stack([positions_of(episodes[i]["states"][t:t + k + 1]) for i, t in pick]), dtype=torch.float32)
        z = model.encode(imgs[:, 0])
        loss = ((model.decode(z) - imgs[:, 0]) ** 2).mean()
        if model.probe is not None:
            loss = loss + ((model.probe(z) - pos[:, 0]) ** 2).mean() / 0.01
        for h in range(k):
            z = model.step(z, acts[:, h])
            loss = loss + ((model.decode(z) - imgs[:, h + 1]) ** 2).mean()
            if model.probe is not None:
                loss = loss + ((model.probe(z) - pos[:, h + 1]) ** 2).mean() / 0.01
        opt.zero_grad()
        loss.backward()
        opt.step()
        if log and (step + 1) % 1000 == 0:
            log(f"step {step + 1}: loss {float(loss):.5f} ({time.perf_counter() - start:.0f} s)")
    return model


def pixel_to_table(u: float, v: float, size: int = 64, fovy: float = 38.0, height: float = 0.9 - 0.02) -> tuple[float, float]:
    f = 0.5 * size / math.tan(math.radians(fovy) / 2)
    return -(v + 0.5 - size / 2) / f * height, -(u + 0.5 - size / 2) / f * height


def puck_positions(image: np.ndarray, min_pixels: int = 4) -> dict[str, np.ndarray | None]:
    rgb = image.astype(float) / 255.0
    out = {}
    for name, colour in COLOURS.items():
        mask = np.linalg.norm(rgb - np.array(colour), axis=-1) < 0.2
        if mask.sum() < min_pixels:
            out[name] = None
            continue
        v, u = np.nonzero(mask)
        out[name] = np.array(pixel_to_table(u.mean(), v.mean()))
    return out


def detector_error(episodes: list[dict], frames: int = 200, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    errs = []
    for _ in range(frames):
        e = episodes[rng.integers(len(episodes))]
        t = rng.integers(len(e["images"]))
        found = puck_positions(e["images"][t])
        for i, name in enumerate(tt.OBJECTS):
            if found[name] is not None:
                errs.append(np.linalg.norm(found[name] - e["states"][t][4 + 4 * i:6 + 4 * i]))
    return float(np.mean(errs))
