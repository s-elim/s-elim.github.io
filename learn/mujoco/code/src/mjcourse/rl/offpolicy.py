"""DDPG, TD3 and SAC in one learner (Lesson 13.3), so that what each adds is a switch.

All three keep a replay buffer, learn a critic Q(s, a) by bootstrapped targets and an
actor that climbs it, and move slow-moving target networks toward the learned ones.
    DDPG  deterministic actor, Gaussian exploration noise, one critic.
    TD3   adds two critics with the minimum in the target (clipped double Q), noise on the
          target action (target policy smoothing) and an actor updated every second step.
    SAC   a stochastic tanh-Gaussian actor, two critics with the minimum, and an entropy
          term whose weight alpha is tuned to keep the policy's entropy near a target.
Truncation is not a terminal state: the target bootstraps unless `terminated` is true.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class OffPolicyConfig:
    algo: str = "sac"                         # "ddpg", "td3" or "sac"
    total_steps: int = 60_000
    start_steps: int = 2_000                  # uniform random actions before learning starts
    batch: int = 256
    buffer: int = 200_000
    gamma: float = 0.99
    tau: float = 0.005                        # target network update rate
    lr: float = 3e-4
    hidden: tuple[int, ...] = (256, 256)
    explore_noise: float = 0.1                # DDPG and TD3
    target_noise: float = 0.2                 # TD3 smoothing noise, clipped at 0.5
    policy_delay: int = 2                     # TD3
    init_alpha: float = 0.1                   # SAC's initial entropy weight; compare with the reward scale
    seed: int = 0
    eval_every: int = 10_000


def net(sizes) -> nn.Sequential:
    layers = []
    for a, b in zip(sizes[:-1], sizes[1:]):
        layers += [nn.Linear(a, b), nn.ReLU()]
    return nn.Sequential(*layers[:-1])


class Actor(nn.Module):
    def __init__(self, obs_dim, act_dim, hidden, stochastic: bool):
        super().__init__()
        self.body = net((obs_dim, *hidden, act_dim * (2 if stochastic else 1)))
        self.stochastic, self.act_dim = stochastic, act_dim

    def forward(self, obs, deterministic: bool = False):
        """Action in [-1, 1] and, for the stochastic actor, its log-probability."""
        out = self.body(obs)
        if not self.stochastic:
            return torch.tanh(out), None
        mean, log_std = out[..., :self.act_dim], out[..., self.act_dim:].clamp(-5, 2)
        if deterministic:
            return torch.tanh(mean), None
        normal = torch.distributions.Normal(mean, log_std.exp())
        raw = normal.rsample()
        action = torch.tanh(raw)
        log_prob = (normal.log_prob(raw) - torch.log(1 - action.pow(2) + 1e-6)).sum(-1)   # change of variables
        return action, log_prob


class Critic(nn.Module):
    def __init__(self, obs_dim, act_dim, hidden, twin: bool):
        super().__init__()
        self.q = nn.ModuleList([net((obs_dim + act_dim, *hidden, 1)) for _ in range(2 if twin else 1)])

    def forward(self, obs, act) -> list[torch.Tensor]:
        x = torch.cat([obs, act], -1)
        return [q(x).squeeze(-1) for q in self.q]


class Learner:
    def __init__(self, obs_dim: int, act_dim: int, cfg: OffPolicyConfig):
        torch.manual_seed(cfg.seed)
        self.cfg, self.act_dim = cfg, act_dim
        self.actor = Actor(obs_dim, act_dim, cfg.hidden, stochastic=cfg.algo == "sac")
        self.critic = Critic(obs_dim, act_dim, cfg.hidden, twin=cfg.algo != "ddpg")
        self.actor_target, self.critic_target = copy.deepcopy(self.actor), copy.deepcopy(self.critic)
        self.actor_opt = torch.optim.Adam(self.actor.parameters(), lr=cfg.lr)
        self.critic_opt = torch.optim.Adam(self.critic.parameters(), lr=cfg.lr)
        self.log_alpha = torch.full((1,), float(np.log(cfg.init_alpha)), requires_grad=True)
        self.alpha_opt = torch.optim.Adam([self.log_alpha], lr=cfg.lr)
        self.target_entropy = -float(act_dim)
        self.updates = 0

    @torch.no_grad()
    def act(self, obs: np.ndarray, explore: bool) -> np.ndarray:
        a, _ = self.actor(torch.as_tensor(obs, dtype=torch.float32), deterministic=not explore)
        a = a.numpy()
        if explore and self.cfg.algo != "sac":
            a = a + self.cfg.explore_noise * np.random.standard_normal(a.shape)
        return np.clip(a, -1, 1)

    def update(self, o, a, r, o2, term) -> None:
        cfg = self.cfg
        with torch.no_grad():
            if cfg.algo == "sac":
                a2, logp2 = self.actor(o2)
                q2 = torch.min(*self.critic_target(o2, a2)) - self.log_alpha.exp() * logp2
            else:
                a2, _ = self.actor_target(o2)
                if cfg.algo == "td3":
                    a2 = (a2 + (cfg.target_noise * torch.randn_like(a2)).clamp(-0.5, 0.5)).clamp(-1, 1)
                qs = self.critic_target(o2, a2)
                q2 = torch.min(*qs) if len(qs) == 2 else qs[0]
            target = r + cfg.gamma * (1 - term) * q2
        critic_loss = sum(F.mse_loss(q, target) for q in self.critic(o, a))
        self.critic_opt.zero_grad()
        critic_loss.backward()
        self.critic_opt.step()
        self.updates += 1
        if cfg.algo == "td3" and self.updates % cfg.policy_delay:
            return
        if cfg.algo == "sac":
            a_new, logp = self.actor(o)
            actor_loss = (self.log_alpha.exp().detach() * logp - torch.min(*self.critic(o, a_new))).mean()
        else:
            actor_loss = -self.critic(o, self.actor(o)[0])[0].mean()
        self.actor_opt.zero_grad()
        actor_loss.backward()
        self.actor_opt.step()
        if cfg.algo == "sac":
            alpha_loss = -(self.log_alpha * (logp.detach() + self.target_entropy)).mean()
            self.alpha_opt.zero_grad()
            alpha_loss.backward()
            self.alpha_opt.step()
        with torch.no_grad():
            for net_, target_ in ((self.actor, self.actor_target), (self.critic, self.critic_target)):
                for p, tp in zip(net_.parameters(), target_.parameters()):
                    tp.mul_(1 - cfg.tau).add_(cfg.tau * p)


def train(make_env, cfg: OffPolicyConfig, evaluate_fn=None, log=print) -> tuple[Learner, list[dict]]:
    """One environment, one gradient update per environment step after `start_steps`."""
    env = make_env()
    np.random.seed(cfg.seed)
    obs_dim, act_dim = env.observation_space.shape[0], env.action_space.shape[0]
    learner = Learner(obs_dim, act_dim, cfg)
    buf = {k: np.zeros((cfg.buffer, n), np.float32) for k, n in (("o", obs_dim), ("a", act_dim), ("o2", obs_dim))}
    buf |= {"r": np.zeros(cfg.buffer, np.float32), "term": np.zeros(cfg.buffer, np.float32)}
    size, history, start = 0, [], time.perf_counter()
    obs, _ = env.reset(seed=cfg.seed)
    for step in range(1, cfg.total_steps + 1):
        action = env.action_space.sample() if step <= cfg.start_steps else learner.act(obs, explore=True)
        obs2, reward, terminated, truncated, _ = env.step(action.astype(np.float32))
        i = size % cfg.buffer
        buf["o"][i], buf["a"][i], buf["r"][i], buf["o2"][i], buf["term"][i] = obs, action, reward, obs2, float(terminated)
        size += 1
        obs = obs2
        if terminated or truncated:
            obs, _ = env.reset()
        if step > cfg.start_steps:
            idx = np.random.randint(0, min(size, cfg.buffer), cfg.batch)
            learner.update(*(torch.as_tensor(buf[k][idx]) for k in ("o", "a", "r", "o2", "term")))
        if evaluate_fn is not None and step % cfg.eval_every == 0:
            row = {"steps": step, "seconds": time.perf_counter() - start, **evaluate_fn(learner)}
            history.append(row)
            if log:
                log(row)
    env.close()
    return learner, history
