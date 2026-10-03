"""Behaviour cloning from images (Level 15).

A small convolutional network reads a 64 x 64 image (RGB, or RGB plus depth), and its
features are concatenated with proprioception (the mass's position and velocity) before a
two-layer head predicts the action. Trained by mean-squared error like the state policy of
mjcourse.il.bc, with the same data.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn


class ConvPolicy(nn.Module):
    def __init__(self, channels: int, proprio: int, actions: int = 2):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(channels, 16, 5, stride=2, padding=2), nn.ReLU(),     # 32 x 32
            nn.Conv2d(16, 32, 3, stride=2, padding=1), nn.ReLU(),           # 16 x 16
            nn.Conv2d(32, 32, 3, stride=2, padding=1), nn.ReLU(),           # 8 x 8
            nn.Flatten(), nn.Linear(32 * 8 * 8, 128), nn.ReLU())
        self.head = nn.Sequential(nn.Linear(128 + proprio, 128), nn.ReLU(), nn.Linear(128, actions))

    def forward(self, image: torch.Tensor, proprio: torch.Tensor) -> torch.Tensor:
        return self.head(torch.cat([self.conv(image), proprio], dim=-1))


class ImagePolicy:
    """Callable on (image, proprioception) for one step; images (H, W, C), uint8 or float."""

    def __init__(self, net, p_mean, p_std, a_mean, a_std, image_scale):
        self.net, self.p_mean, self.p_std, self.a_mean, self.a_std, self.image_scale = net, p_mean, p_std, a_mean, a_std, image_scale

    def prepare(self, images: np.ndarray) -> torch.Tensor:
        x = torch.as_tensor(np.asarray(images, np.float32) / self.image_scale)
        return x.permute(0, 3, 1, 2)

    @torch.no_grad()
    def __call__(self, image: np.ndarray, proprio: np.ndarray) -> np.ndarray:
        p = torch.as_tensor(((np.asarray(proprio) - self.p_mean) / self.p_std)[None], dtype=torch.float32)
        return self.net(self.prepare(image[None]), p)[0].numpy() * self.a_std + self.a_mean


def fit_images(images: np.ndarray, proprio: np.ndarray, actions: np.ndarray, steps: int = 3000, batch: int = 128,
               lr: float = 1e-3, seed: int = 0) -> ImagePolicy:
    """images (N, H, W, C): uint8 RGB, or float32 RGB in [0, 1] with depth (m) as a fourth channel."""
    torch.manual_seed(seed)
    image_scale = 255.0 if images.dtype == np.uint8 else np.r_[np.ones(3), np.full(images.shape[-1] - 3, 1.25)].astype(np.float32)
    p_mean, p_std = proprio.mean(axis=0), proprio.std(axis=0) + 1e-6
    a_mean, a_std = actions.mean(axis=0), actions.std(axis=0) + 1e-6
    net = ConvPolicy(images.shape[-1], proprio.shape[1], actions.shape[1])
    policy = ImagePolicy(net, p_mean, p_std, a_mean, a_std, image_scale)
    p_all = torch.as_tensor((proprio - p_mean) / p_std, dtype=torch.float32)
    a_all = torch.as_tensor((actions - a_mean) / a_std, dtype=torch.float32)
    optimizer = torch.optim.Adam(net.parameters(), lr=lr)
    gen = np.random.default_rng(seed)
    for _ in range(steps):
        idx = gen.integers(0, len(images), min(batch, len(images)))
        loss = (net(policy.prepare(images[idx]), p_all[idx]) - a_all[idx]).pow(2).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return policy
