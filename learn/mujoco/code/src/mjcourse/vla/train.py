from __future__ import annotations

import time

import numpy as np
import torch
from torch.nn import functional as F

from mjcourse import tabletop as tt
from mjcourse.vla.model import MiniVLA, VLAConfig

STATE_SCALE = np.array([1 / 0.3, 1 / 0.3, 1 / 0.2, 1 / 0.2], np.float32)   # pusher x, y (m), vx, vy (m/s) to about +-1


def _batch(arrays, idx, shift: int, state_dim: int = 4):
    img = torch.as_tensor(arrays["images"][idx]).permute(0, 3, 1, 2).float() / 255.0
    if shift:
        img = F.pad(img, (shift,) * 4, mode="replicate")
        dx, dy = np.random.randint(0, 2 * shift + 1, 2)
        img = img[:, :, dy:dy + 64, dx:dx + 64]
    states = (arrays["states"][idx] * STATE_SCALE)[:, :state_dim]
    return (img, torch.as_tensor(arrays["words"][idx]), torch.as_tensor(states),
            torch.as_tensor(arrays["targets"][idx]), torch.as_tensor(arrays["masks"][idx]),
            torch.as_tensor(arrays["pucks"][idx]))


def fit(arrays: dict, vocab: int, steps: int = 6000, batch: int = 64, lr: float = 3e-4, seed: int = 0,
        shift: int = 4, cfg: VLAConfig | None = None, log=None) -> tuple[MiniVLA, list[float]]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = MiniVLA(cfg or VLAConfig(vocab=vocab))
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, steps)
    n, losses, start = len(arrays["images"]), [], time.perf_counter()
    for step in range(steps):
        idx = np.random.randint(0, n, batch)
        img, words, state, target, mask, pucks = _batch(arrays, idx, shift, model.cfg.state_dim)
        pred = model(img, words, state, pucks)
        loss = (((pred - target) ** 2).sum(-1) * mask).sum() / mask.sum()
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        losses.append(float(loss.detach()))
        if log and (step + 1) % 1000 == 0:
            log(f"step {step + 1}: loss {np.mean(losses[-1000:]):.4f} ({time.perf_counter() - start:.0f} s)")
    return model, losses


class VLAPolicy:
    def __init__(self, model: MiniVLA, tokenizer, ensemble: bool = False, decay: float = 0.5):
        self.model, self.tokenizer, self.ensemble, self.decay = model.eval(), tokenizer, ensemble, decay
        self.history: list[tuple[int, np.ndarray]] = []

    def reset(self) -> None:
        self.history = []

    @torch.no_grad()
    def chunk(self, image: np.ndarray, text: str, state: np.ndarray) -> np.ndarray:
        img = torch.as_tensor(image).permute(2, 0, 1).float().unsqueeze(0) / 255.0
        words = torch.as_tensor(self.tokenizer(text)).unsqueeze(0)
        s = torch.as_tensor((state[:4] * STATE_SCALE)[:self.model.cfg.state_dim].astype(np.float32)).unsqueeze(0)
        pucks = None
        if self.model.cfg.vision == "oracle":                               # privileged: diagnosis only
            pucks = torch.as_tensor(state[[4, 5, 8, 9, 12, 13]].astype(np.float32)).unsqueeze(0)
        return self.model(img, words, s, pucks)[0].numpy()

    def act(self, t: int, image: np.ndarray, text: str, state: np.ndarray) -> np.ndarray:
        chunk = self.chunk(image, text, state)
        if not self.ensemble:
            return chunk[0]
        self.history = [(t0, c) for t0, c in self.history if t - t0 < len(c)] + [(t, chunk)]
        preds = np.array([c[t - t0] for t0, c in self.history])
        weights = np.exp(-self.decay * np.arange(len(preds))[::-1])        # older chunks weigh more in ACT; see 22.3
        return (weights[:, None] * preds).sum(0) / weights.sum()


def run_episode(policy: VLAPolicy, text: str, task, layout: tt.Layout, variation: tt.Variation | None = None,
                camera: str = "top", record: bool = False) -> dict:
    scene = tt.Tabletop(variation)
    scene.reset(layout)
    policy.reset()
    log = {"states": [], "actions": [], "images": []}
    for t in range(tt.EPISODE_STEPS):
        s = scene.state()
        image = scene.render(camera, 64)
        a = policy.act(t, image, text, s)
        if record:
            log["states"].append(s)
            log["actions"].append(a)
            log["images"].append(image)
        scene.step(a)
        if scene.success(task) and np.linalg.norm(scene.state()[4 + 4 * tt.OBJECTS.index(task[0]) + 2:][:2]) < 0.02:
            break
    out = {"success": scene.success(task), "steps": t + 1, "final": scene.state(), **({"log": log} if record else {})}
    scene.close()
    return out
