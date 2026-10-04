"""Lesson 21.4: planning with MuJoCo, then with a learned world model (Level 21).

INPUT   cartpole.xml; the predictive-sampling planner of the showcase (64 samples, 4-knot spline over 1 s,
        noise scales 0.5, 2 and 8 N, replanning every 40 ms); swing up from hanging and balance, 10 s, success when
        the pole stays within 0.2 rad of upright for the last 2 s with the cart inside its rails
PROCESS (1) the planner with MuJoCo as its model (a 10 ms copy of the simulator, pole 0.2 kg), 10 starts, on
            the real cart-pole with a 0.2, 0.4 and 0.8 kg pole;
        (2) a learned world model: an MLP predicting the 10 ms state change from the state (pole angle as its sine
            and cosine) and the force; trained on 100 to 10,000 transitions drawn uniformly over the task's state
            range, or on 100,000 transitions from random exploration (random forces held for 0.1 s, 1 s episodes
            from hanging); for each: the share of states within 0.5 rad of upright, the one-step error on uniform
            held-out transitions, the open-loop pole-angle error of 1 s predictions under random forces, and the
            closed-loop success of the same planner using the learned model
OUTPUT  printed tables

Run:  python examples/l21_4_world_models.py          (about 10 minutes)
"""
# requires: torch

import os

import mujoco
import mujoco.rollout as rollout
import numpy as np
import torch
from torch import nn

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"
FULL = mujoco.mjtState.mjSTATE_FULLPHYSICS
SCALES = np.array([0.5, 2.0, 8.0])
KNOTS, REPLAN, PLAN_DT, HORIZON, SAMPLES, LIMIT = 4, 0.04, 0.01, 1.0, 64, 20.0
LOW = np.array([-1.4, -np.pi, -3.0, -12.0])                    # state ranges for the data: x, theta, xdot, thetadot
HIGH = -LOW
STEPS = round(HORIZON / PLAN_DT)


def cost(x: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Summed running cost; x is (N, T, 4) states (x, theta, xdot, thetadot), u is (N, T) forces."""
    return ((1 - np.cos(x[..., 1])) + 0.1 * x[..., 0] ** 2 + 0.01 * x[..., 2] ** 2 + 0.001 * x[..., 3] ** 2
            + 1e-4 * u ** 2).sum(axis=1)


class MujocoModel:
    """The simulator at a 10 ms timestep, as a model: predict(states (N, 4), forces (N, T)) -> (N, T, 4)."""

    def __init__(self):
        self.model = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
        self.model.opt.timestep = PLAN_DT
        self.datas = [mujoco.MjData(self.model) for _ in range(8)]
        self.template = np.zeros(mujoco.mj_stateSize(self.model, FULL))

    def predict(self, states: np.ndarray, forces: np.ndarray) -> np.ndarray:
        x0 = np.tile(self.template, (len(states), 1))
        x0[:, 1:3], x0[:, 3:5] = states[:, :2], states[:, 2:]            # full state: time, qpos, qvel
        out, _ = rollout.rollout(self.model, self.datas, x0, forces[..., None])
        return out[..., 1:5]


def features(states: np.ndarray, forces: np.ndarray) -> np.ndarray:
    """The network's input: x, sin and cos of the pole angle (the dynamics are periodic in it), velocities, force."""
    return np.c_[states[:, 0], np.sin(states[:, 1]), np.cos(states[:, 1]), states[:, 2:], forces]


class LearnedModel:
    """An MLP predicting the 10 ms state change, rolled out step by step."""

    def __init__(self, net: nn.Module, mean: np.ndarray, std: np.ndarray, dmean: np.ndarray, dstd: np.ndarray):
        self.net, self.mean, self.std, self.dmean, self.dstd = net, mean, std, dmean, dstd

    def step(self, states: np.ndarray, forces: np.ndarray) -> np.ndarray:
        z = features(states, forces)
        with torch.no_grad():
            delta = self.net(torch.as_tensor((z - self.mean) / self.std, dtype=torch.float32)).numpy()
        return states + delta * self.dstd + self.dmean

    def predict(self, states: np.ndarray, forces: np.ndarray) -> np.ndarray:
        out, x = np.empty((len(states), forces.shape[1], 4)), states.copy()
        for t in range(forces.shape[1]):
            x = self.step(x, forces[:, t])
            out[:, t] = x
        return out


def transitions(n: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    states, forces = rng.uniform(LOW, HIGH, (n, 4)), rng.uniform(-LIMIT, LIMIT, n)
    sim = MujocoModel()
    nxt = sim.predict(states, forces[:, None])[:, 0]
    return states, forces, nxt


def train(n: int, seed: int = 0, data: str = "uniform") -> LearnedModel:
    s, u, s1 = transitions(n, seed) if data == "uniform" else explore(n, seed)
    z, d = features(s, u), s1 - s
    mean, std, dmean, dstd = z.mean(0), z.std(0) + 1e-8, d.mean(0), d.std(0) + 1e-8
    torch.manual_seed(seed)
    net = nn.Sequential(nn.Linear(6, 128), nn.SiLU(), nn.Linear(128, 128), nn.SiLU(), nn.Linear(128, 4))
    opt = torch.optim.Adam(net.parameters(), lr=2e-3)
    x = torch.as_tensor((z - mean) / std, dtype=torch.float32)
    y = torch.as_tensor((d - dmean) / dstd, dtype=torch.float32)
    updates = 300 if FAST else 6000
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, updates)
    gen = torch.Generator().manual_seed(seed)
    for _ in range(updates):
        idx = torch.randint(0, n, (min(512, n),), generator=gen)
        loss = ((net(x[idx]) - y[idx]) ** 2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
    return LearnedModel(net, mean, std, dmean, dstd)


def explore(n: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Transitions from random exploration: 1 s episodes from hanging, a new random force every 0.1 s."""
    rng, sim, chunks = np.random.default_rng(seed), MujocoModel(), []
    while sum(len(c[0]) for c in chunks) < n:
        start = np.array([0.0, np.pi + rng.normal(0, 0.1), 0.0, 0.0])
        forces = np.repeat(rng.uniform(-LIMIT, LIMIT, 10), 10)[None]
        traj = sim.predict(start[None], forces)[0]
        chunks.append((np.vstack([start, traj[:-1]]), forces[0], traj))
    s, u, s1 = (np.concatenate([c[k] for c in chunks])[:n] for k in range(3))
    return s, u, s1


def episode(world, seed: int, seconds: float = 10.0, pole_mass: float = 0.2) -> bool:
    rng = np.random.default_rng(seed)
    spec = mujoco.MjSpec.from_file(str(model_path("cartpole")))
    spec.geom("pole").mass = pole_mass
    model = spec.compile()
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("hanging").id)
    data.qpos[1] += rng.normal(0.0, 0.05)
    knot_t, step_t = np.linspace(0.0, HORIZON, KNOTS), np.arange(STEPS) * PLAN_DT
    nominal, t_nominal, angles = np.zeros(KNOTS), 0.0, []
    for _ in range(round(seconds / REPLAN)):
        nominal = np.interp(knot_t + (data.time - t_nominal), knot_t, nominal)
        t_nominal = data.time
        noise = SCALES[np.arange(SAMPLES - 1) % 3][:, None] * rng.standard_normal((SAMPLES - 1, KNOTS))
        candidates = np.vstack([nominal, np.clip(nominal + noise, -LIMIT, LIMIT)])
        forces = np.stack([np.interp(step_t, knot_t, c) for c in candidates])
        state = np.r_[data.qpos, data.qvel]
        predicted = world.predict(np.tile(state, (SAMPLES, 1)), forces)
        nominal = candidates[int(np.argmin(cost(predicted, forces)))]
        for _ in range(round(REPLAN / model.opt.timestep)):
            data.ctrl[0] = np.interp(data.time - t_nominal, knot_t, nominal)
            mujoco.mj_step(model, data)
        angles.append(abs((data.qpos[1] + np.pi) % (2 * np.pi) - np.pi))
    return bool((np.array(angles[-round(2.0 / REPLAN):]) < 0.2).all() and abs(data.qpos[0]) < 1.45)


if __name__ == "__main__":
    starts = range(3) if FAST else range(10)
    print(f"MuJoCo {mujoco.__version__}, torch {torch.__version__}; planner: {SAMPLES} samples, {HORIZON} s horizon, "
          f"replanning every {1000 * REPLAN:.0f} ms; {len(starts)} starts per row")
    sim = MujocoModel()
    print("(1) MuJoCo as the model (it assumes a 0.2 kg pole)")
    for mass in (0.2, 0.4, 0.8):
        print(f"    real pole {mass} kg: success {sum(episode(sim, s, pole_mass=mass) for s in starts)}/{len(starts)}")
    print("(2) a learned model (MLP, 2 x 128 units)")
    test_s, test_u, test_s1 = transitions(5000, seed=99)
    rng = np.random.default_rng(7)
    starts_ol = rng.uniform(LOW * [0.5, 1, 0.3, 0.3], HIGH * [0.5, 1, 0.3, 0.3], (200, 4))
    forces_ol = rng.uniform(-LIMIT, LIMIT, (200, STEPS))
    truth = sim.predict(starts_ol, forces_ol)
    print(f"    {'data':<28}{'near upright':>13}{'one-step RMS error (x, th, xd, thd)':>40}{'pole angle error at 1 s':>25}{'success':>9}")
    sets = [("uniform", n) for n in ((300, 1000) if FAST else (100, 300, 1000, 10000))] + [("exploration", 10000 if FAST else 100000)]
    for data, n in sets:
        s_train = (transitions if data == "uniform" else explore)(n, 0)[0]
        near = np.mean(np.abs((s_train[:, 1] + np.pi) % (2 * np.pi) - np.pi) < 0.5)
        world = train(n, data=data)
        rms = np.sqrt(np.mean((world.step(test_s, test_u) - test_s1) ** 2, axis=0))
        pred = world.predict(starts_ol, forces_ol)
        err = np.median(np.abs(np.angle(np.exp(1j * (pred[:, -1, 1] - truth[:, -1, 1])))))
        wins = sum(episode(world, s) for s in starts)
        print(f"    {data + ', ' + format(n, ',') + ' transitions':<28}{near:>13.4f}   "
              f"{rms[0]:.1e} {rms[1]:.1e} {rms[2]:.1e} {rms[3]:.1e}{err:>22.3f} rad{wins:>6}/{len(starts)}")
