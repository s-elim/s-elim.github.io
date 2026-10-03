"""Proximal Policy Optimization, written out (Lesson 13.2).

One iteration: run the current policy in N vector environments for T steps; estimate
advantages with GAE(lambda) from a learned value function; then take several epochs of
minibatch gradient steps on the clipped surrogate objective, a value loss and an entropy
bonus. Truncated episodes are bootstrapped from the value of their final observation
(gymnasium's SAME_STEP autoreset puts it in info["final_obs"]); terminated ones are not.
Observations are normalized by running statistics unless `normalize_obs` is False.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import gymnasium as gym
import numpy as np
import torch
from torch import nn


@dataclass
class PPOConfig:
    num_envs: int = 16
    steps_per_env: int = 128                 # T: rollout length per environment and iteration
    total_steps: int = 500_000
    gamma: float = 0.99
    gae_lambda: float = 0.95
    epochs: int = 10
    minibatch: int = 512
    lr: float = 3e-4
    clip: float = 0.2
    entropy_coef: float = 0.0
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    hidden: tuple[int, ...] = (64, 64)
    normalize_obs: bool = True
    bootstrap_truncation: bool = True        # False treats time limits as terminal states (a mistake, kept to measure it)
    seed: int = 0
    log_every: int = 10
    extra: dict = field(default_factory=dict)


class RunningMeanStd:
    """Running mean and variance (parallel algorithm of Chan et al.) for observation normalization."""

    def __init__(self, shape):
        self.mean, self.var, self.count = np.zeros(shape), np.ones(shape), 1e-4

    def update(self, x: np.ndarray) -> None:
        batch_mean, batch_var, n = x.mean(axis=0), x.var(axis=0), x.shape[0]
        delta, total = batch_mean - self.mean, self.count + n
        self.mean = self.mean + delta * n / total
        self.var = (self.var * self.count + batch_var * n + delta**2 * self.count * n / total) / total
        self.count = total

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return np.clip((x - self.mean) / np.sqrt(self.var + 1e-8), -10, 10)


def mlp(sizes, out_std: float) -> nn.Sequential:
    layers = []
    for a, b in zip(sizes[:-2], sizes[1:-1]):
        layers += [nn.Linear(a, b), nn.Tanh()]
    layers.append(nn.Linear(sizes[-2], sizes[-1]))
    for layer in layers:
        if isinstance(layer, nn.Linear):
            nn.init.orthogonal_(layer.weight, np.sqrt(2))
            nn.init.zeros_(layer.bias)
    nn.init.orthogonal_(layers[-1].weight, out_std)
    return nn.Sequential(*layers)


class ActorCritic(nn.Module):
    """Gaussian policy with a state-independent log standard deviation, and a separate value network."""

    def __init__(self, obs_dim: int, act_dim: int, hidden: tuple[int, ...]):
        super().__init__()
        self.actor = mlp((obs_dim, *hidden, act_dim), out_std=0.01)
        self.critic = mlp((obs_dim, *hidden, 1), out_std=1.0)
        self.log_std = nn.Parameter(torch.full((act_dim,), -0.5))

    def dist(self, obs: torch.Tensor) -> torch.distributions.Normal:
        return torch.distributions.Normal(self.actor(obs), self.log_std.exp())

    def value(self, obs: torch.Tensor) -> torch.Tensor:
        return self.critic(obs).squeeze(-1)


class Agent:
    """The trained policy with its observation normalizer; `act` returns the mean action."""

    def __init__(self, net: ActorCritic, obs_rms: RunningMeanStd | None, low, high):
        self.net, self.obs_rms, self.low, self.high = net, obs_rms, low, high

    def norm(self, obs: np.ndarray) -> np.ndarray:
        return self.obs_rms(obs) if self.obs_rms is not None else obs

    @torch.no_grad()
    def act(self, obs: np.ndarray) -> np.ndarray:
        x = torch.as_tensor(self.norm(np.asarray(obs, np.float64)), dtype=torch.float32)
        return np.clip(self.net.actor(x).numpy(), self.low, self.high)


def train(make_env, cfg: PPOConfig, log=print, evaluate_fn=None, eval_every: int = 0) -> tuple[Agent, list[dict]]:
    """Returns the agent and one history row per iteration; with `evaluate_fn`, rows at every
    `eval_every` environment steps also hold its result (deterministic held-out evaluation)."""
    torch.manual_seed(cfg.seed)
    envs = gym.vector.AsyncVectorEnv([make_env] * cfg.num_envs, autoreset_mode=gym.vector.AutoresetMode.SAME_STEP)
    obs_dim, act_dim = envs.single_observation_space.shape[0], envs.single_action_space.shape[0]
    low, high = envs.single_action_space.low, envs.single_action_space.high
    net = ActorCritic(obs_dim, act_dim, cfg.hidden)
    optimizer = torch.optim.Adam(net.parameters(), lr=cfg.lr, eps=1e-5)
    obs_rms = RunningMeanStd(obs_dim) if cfg.normalize_obs else None
    agent = Agent(net, obs_rms, low, high)
    n, t_len = cfg.num_envs, cfg.steps_per_env
    iterations = cfg.total_steps // (n * t_len)
    obs, _ = envs.reset(seed=cfg.seed)
    history, finished = [], {"return": [], "success": [], "length": []}
    ep_return, ep_length = np.zeros(n), np.zeros(n, int)
    start = time.perf_counter()
    for it in range(1, iterations + 1):
        b_obs, b_act, b_logp = np.zeros((t_len, n, obs_dim)), np.zeros((t_len, n, act_dim)), np.zeros((t_len, n))
        b_rew, b_done, b_val = np.zeros((t_len, n)), np.zeros((t_len, n)), np.zeros((t_len + 1, n))
        for t in range(t_len):
            if obs_rms is not None:
                obs_rms.update(obs)
            x = torch.as_tensor(agent.norm(obs), dtype=torch.float32)
            with torch.no_grad():
                dist, value = net.dist(x), net.value(x)
                action = dist.sample()
            b_obs[t], b_act[t], b_logp[t], b_val[t] = x.numpy(), action.numpy(), dist.log_prob(action).sum(-1).numpy(), value.numpy()
            obs, reward, terminated, truncated, info = envs.step(np.clip(action.numpy(), low, high))
            reward = reward.astype(np.float64)
            ep_return += reward
            ep_length += 1
            for i in np.flatnonzero(truncated & ~terminated & cfg.bootstrap_truncation):   # the episode did not end
                final = torch.as_tensor(agent.norm(info["final_obs"][i][None]), dtype=torch.float32)
                with torch.no_grad():
                    reward[i] += cfg.gamma * net.value(final).item()
            b_rew[t], b_done[t] = reward, terminated | truncated
            for i in np.flatnonzero(terminated | truncated):
                finished["return"].append(ep_return[i])
                finished["length"].append(ep_length[i])
                final_info = info.get("final_info", {})                  # the finished episode's info
                finished["success"].append(bool(final_info["is_success"][i]) if "is_success" in final_info else False)
                ep_return[i], ep_length[i] = 0.0, 0
        with torch.no_grad():
            b_val[t_len] = net.value(torch.as_tensor(agent.norm(obs), dtype=torch.float32)).numpy()
        advantages, last = np.zeros((t_len, n)), np.zeros(n)
        for t in reversed(range(t_len)):                              # GAE(lambda)
            alive = 1.0 - b_done[t]
            delta = b_rew[t] + cfg.gamma * b_val[t + 1] * alive - b_val[t]
            last = delta + cfg.gamma * cfg.gae_lambda * alive * last
            advantages[t] = last
        returns = advantages + b_val[:t_len]
        flat = lambda a: torch.as_tensor(a.reshape(t_len * n, *a.shape[2:]), dtype=torch.float32)   # noqa: E731
        obs_t, act_t, logp_t, adv_t, ret_t = flat(b_obs), flat(b_act), flat(b_logp), flat(advantages), flat(returns)
        stats = {"kl": [], "clipfrac": [], "value_loss": [], "entropy": []}
        for _ in range(cfg.epochs):
            for idx in torch.randperm(t_len * n).split(cfg.minibatch):
                dist = net.dist(obs_t[idx])
                logp = dist.log_prob(act_t[idx]).sum(-1)
                ratio = (logp - logp_t[idx]).exp()
                adv = (adv_t[idx] - adv_t[idx].mean()) / (adv_t[idx].std() + 1e-8)
                policy_loss = -torch.min(ratio * adv, ratio.clamp(1 - cfg.clip, 1 + cfg.clip) * adv).mean()
                value_loss = 0.5 * (net.value(obs_t[idx]) - ret_t[idx]).pow(2).mean()
                entropy = dist.entropy().sum(-1).mean()
                loss = policy_loss + cfg.value_coef * value_loss - cfg.entropy_coef * entropy
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), cfg.max_grad_norm)
                optimizer.step()
                with torch.no_grad():
                    stats["kl"].append(((ratio - 1) - (logp - logp_t[idx])).mean().item())   # low-variance KL estimate
                    stats["clipfrac"].append(((ratio - 1).abs() > cfg.clip).float().mean().item())
                    stats["value_loss"].append(value_loss.item())
                    stats["entropy"].append(entropy.item())
        variance = ret_t.var().item()
        with torch.no_grad():
            explained = 1 - (ret_t - net.value(obs_t)).var().item() / variance if variance > 0 else float("nan")
        recent = slice(-100, None)
        row = {"iteration": it, "steps": it * n * t_len, "seconds": time.perf_counter() - start,
               "return": float(np.mean(finished["return"][recent])) if finished["return"] else float("nan"),
               "success": float(np.mean(finished["success"][recent])) if finished["success"] else float("nan"),
               "length": float(np.mean(finished["length"][recent])) if finished["length"] else float("nan"),
               "explained_variance": explained, "std": float(net.log_std.exp().mean().item()),
               **{k: float(np.mean(v)) for k, v in stats.items()}}
        if evaluate_fn is not None and eval_every and (it * n * t_len) // eval_every > ((it - 1) * n * t_len) // eval_every:
            row["eval"] = evaluate_fn(agent)
        history.append(row)
        if log and (it % cfg.log_every == 0 or it == iterations):
            log(row)
    envs.close()
    return agent, history


def evaluate(agent: Agent, make_env, seeds) -> dict:
    """Deterministic (mean-action) episodes from the given reset seeds."""
    env = make_env()
    success, final_distance, returns = [], [], []
    for seed in seeds:
        obs, info = env.reset(seed=int(seed))
        total, done = 0.0, False
        while not done:
            obs, reward, terminated, truncated, info = env.step(agent.act(obs))
            total += reward
            done = terminated or truncated
        success.append(bool(info.get("is_success", False)))
        final_distance.append(info.get("distance", float("nan")))
        returns.append(total)
    env.close()
    return {"success": np.array(success), "final_distance": np.array(final_distance), "return": np.array(returns)}
