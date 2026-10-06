from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass(frozen=True)
class VLAConfig:
    vocab: int
    width: int = 64
    heads: int = 4
    layers: int = 2
    chunk: int = 4
    max_tokens: int = 12
    state_dim: int = 4
    vision: str = "patch"
    keypoints: int = 16


class VisionEncoder(nn.Module):
    def __init__(self, width: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(5, 32, 5, stride=2, padding=2), nn.ReLU(),       # 32 x 32
            nn.Conv2d(32, 32, 3, stride=2, padding=1), nn.ReLU(),      # 16 x 16
            nn.Conv2d(32, width, 3, stride=2, padding=1), nn.ReLU(),   # 8 x 8
            nn.Conv2d(width, width, 1))
        self.position = nn.Parameter(torch.zeros(1, 64, width))

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        b, _, h, w = image.shape
        ys = torch.linspace(-1, 1, h).view(1, 1, h, 1).expand(b, 1, h, w)
        xs = torch.linspace(-1, 1, w).view(1, 1, 1, w).expand(b, 1, h, w)
        features = self.net(torch.cat([image, xs, ys], dim=1))          # (B, D, 8, 8)
        return features.flatten(2).transpose(1, 2) + self.position     # (B, 64, D)


class FiLMKeypointEncoder(nn.Module):
    def __init__(self, width: int, keypoints: int):
        super().__init__()
        self.c1 = nn.Conv2d(5, 32, 5, stride=2, padding=2)                # 32 x 32
        self.c2 = nn.Conv2d(32, 32, 3, padding=1)
        self.c3 = nn.Conv2d(32, keypoints, 3, padding=1)
        self.film = nn.Linear(width, 2 * (32 + 32))                        # scale and shift for c1 and c2
        self.token = nn.Linear(3, width)
        self.identity = nn.Parameter(torch.randn(1, keypoints, width) * 0.02)

    def forward(self, image: torch.Tensor, language: torch.Tensor) -> torch.Tensor:
        b, _, h, w = image.shape
        ys = torch.linspace(-1, 1, h).view(1, 1, h, 1).expand(b, 1, h, w)
        xs = torch.linspace(-1, 1, w).view(1, 1, 1, w).expand(b, 1, h, w)
        g1, b1, g2, b2 = self.film(language).split(32, dim=-1)
        x = torch.relu(self.c1(torch.cat([image, xs, ys], 1)) * (1 + g1[..., None, None]) + b1[..., None, None])
        x = torch.relu(self.c2(x) * (1 + g2[..., None, None]) + b2[..., None, None])
        logits = self.c3(x).flatten(2)                                     # (B, K, 32 * 32)
        attention = torch.softmax(logits, dim=-1)
        grid = torch.linspace(-1, 1, 32)
        gy, gx = torch.meshgrid(grid, grid, indexing="ij")
        ex = (attention * gx.flatten()).sum(-1)                            # expected x of each keypoint
        ey = (attention * gy.flatten()).sum(-1)
        presence = logits.max(-1).values.tanh()
        return self.token(torch.stack([ex, ey, presence], -1)) + self.identity


class OracleObjects(nn.Module):
    def __init__(self, width: int):
        super().__init__()
        self.token = nn.Linear(2, width)
        self.identity = nn.Parameter(torch.randn(1, 3, width) * 0.02)

    def forward(self, pucks: torch.Tensor) -> torch.Tensor:
        return self.token(pucks.view(-1, 3, 2) / 0.3) + self.identity


class MiniVLA(nn.Module):
    def __init__(self, cfg: VLAConfig):
        super().__init__()
        self.cfg = cfg
        d = cfg.width
        if cfg.vision == "patch":
            self.vision = VisionEncoder(d)
        elif cfg.vision == "keypoint":
            self.vision = FiLMKeypointEncoder(d, cfg.keypoints)
        elif cfg.vision == "oracle":
            self.vision = OracleObjects(d)
        else:
            raise ValueError(cfg.vision)
        self.words = nn.Embedding(cfg.vocab, d, padding_idx=0)
        self.word_position = nn.Parameter(torch.zeros(1, cfg.max_tokens, d))
        self.state = nn.Linear(cfg.state_dim, d)
        self.queries = nn.Parameter(torch.randn(1, cfg.chunk, d) * 0.02)
        self.modality = nn.Parameter(torch.zeros(4, d))                  # query, state, language, vision
        layer = nn.TransformerEncoderLayer(d, cfg.heads, dim_feedforward=2 * d, dropout=0.0, batch_first=True)
        self.fusion = nn.TransformerEncoder(layer, cfg.layers, enable_nested_tensor=False)
        self.head = nn.Linear(d, 2)

    def tokens(self, image, words, state, pucks=None) -> tuple[torch.Tensor, torch.Tensor]:
        b = image.shape[0]
        q = self.queries.expand(b, -1, -1) + self.modality[0]
        s = self.state(state).unsqueeze(1) + self.modality[1]
        embedded = self.words(words)
        w = embedded + self.word_position + self.modality[2]
        if self.cfg.vision == "keypoint":
            known = (words != 0).float().unsqueeze(-1)
            summary = (embedded * known).sum(1) / known.sum(1).clamp(min=1)     # mean word embedding
            v = self.vision(image, summary) + self.modality[3]
        elif self.cfg.vision == "oracle":
            v = self.vision(pucks) + self.modality[3]
        else:
            v = self.vision(image) + self.modality[3]
        pad = torch.cat([torch.zeros(b, q.shape[1] + 1, dtype=torch.bool), words == 0,
                         torch.zeros(b, v.shape[1], dtype=torch.bool)], dim=1)
        return torch.cat([q, s, w, v], dim=1), pad

    def forward(self, image, words, state, pucks=None) -> torch.Tensor:
        x, pad = self.tokens(image, words, state, pucks)
        fused = self.fusion(x, src_key_padding_mask=pad)
        return torch.tanh(self.head(fused[:, :self.cfg.chunk]))         # (B, CHUNK, 2)
