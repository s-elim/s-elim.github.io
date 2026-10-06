import json
import os
from pathlib import Path

import numpy as np
import torch

from mjcourse import tabletop as tt
from mjcourse.worldmodel import data, dynamics, standard

OUT = Path(__file__).resolve().parents[1] / "runs" / "l23_2"
HORIZONS = (1, 5, 10, 20, 50)


class Persistence:
    @torch.no_grad()
    def rollout(self, s0, actions):
        return np.repeat(np.atleast_2d(s0)[:, None], actions.shape[1] + 1, axis=1)


class Linear:
    def __init__(self, episodes):
        s, a, s2 = data.transitions(episodes)
        x = np.c_[s, a, np.ones(len(s))]
        self.w, *_ = np.linalg.lstsq(x, s2 - s, rcond=None)

    def rollout(self, s0, actions):
        s = np.atleast_2d(s0).astype(float)
        out = [s]
        for t in range(actions.shape[1]):
            s = s + np.c_[s, actions[:, t], np.ones(len(s))] @ self.w
            out.append(s)
        return np.stack(out, 1)


def part1(train, test) -> None:
    s, _, _ = data.transitions(train)
    print(f"(1) {len(train)} training episodes ({len(s)} transitions), {len(test)} held out; "
          f"pusher touching a puck in {data.contact_share(train):.1%} of steps")


def part2_3(train, test, mlp) -> dict:
    models = {"nothing moves": Persistence(), "linear": Linear(train), "MLP, one-step objective": mlp}
    print("(2, 3) open-loop prediction error on held-out states (mean distance, mm)")
    print(f"  {'model':<26}{'quantity':<14}" + "".join(f"{h:>9d}" for h in HORIZONS) + "   (steps of 0.1 s)")
    table = {}
    for name, model in models.items():
        err = dynamics.horizon_errors(model, test, HORIZONS)
        table[name] = err
        for q, label in (("pusher", "pusher"), ("target", "pushed puck"), ("worst_puck", "worst puck")):
            print(f"  {name:<26}{label:<14}" + "".join(f"{1000 * err[h][q]:9.2f}" for h in HORIZONS))
    return table


def part4(test, mlp) -> dict:
    episode = test[3]
    target = tt.OBJECTS.index(episode["task"][0])
    pred = mlp.rollout(episode["states"][0][None], episode["actions"][None, :60])[0]
    true = episode["states"][:61]
    i = 4 + 4 * target
    print(f"(4) held-out episode 3 ({episode['task'][0]} puck toward the {episode['task'][1]} zone), predicted open loop "
          "from its first state under its logged actions")
    for t in (0, 10, 20, 30, 40, 50, 60):
        print(f"  t = {t / 10:3.1f} s  pusher true {np.round(true[t, :2], 3)} predicted {np.round(pred[t, :2], 3)}   "
              f"puck true {np.round(true[t, i:i + 2], 3)} predicted {np.round(pred[t, i:i + 2], 3)}")
    return {"true": true.tolist(), "pred": pred.tolist(), "target": target}


def figure(table: dict, trajectory: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
    colours = {"nothing moves": "#7a7a7a", "linear": "#E69F00", "MLP, one-step objective": "#0072B2"}
    for name, err in table.items():
        ax1.plot(HORIZONS, [1000 * err[h]["target"] for h in HORIZONS], marker="o", color=colours[name], label=name)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("prediction horizon (steps of 0.1 s)")
    ax1.set_ylabel("error of the pushed puck (mm)")
    ax1.grid(alpha=0.3, which="both")
    ax1.legend(frameon=False)
    true, pred, i = np.array(trajectory["true"]), np.array(trajectory["pred"]), 4 + 4 * trajectory["target"]
    ax2.plot(true[:, 1], true[:, 0], color="#0072B2", label="pusher, MuJoCo")
    ax2.plot(pred[:, 1], pred[:, 0], "--", color="#0072B2", label="pusher, learned model")
    ax2.plot(true[:, i + 1], true[:, i], color="#D55E00", label="puck, MuJoCo")
    ax2.plot(pred[:, i + 1], pred[:, i], "--", color="#D55E00", label="puck, learned model")
    ax2.invert_xaxis()
    ax2.set_aspect("equal")
    ax2.set_xlabel("y (m)")
    ax2.set_ylabel("x (m)")
    ax2.legend(frameon=False, fontsize=8)
    ax2.set_title("one held-out episode, 6 s open loop", fontsize=10)
    fig.savefig(OUT / "horizon.png", dpi=150)
    plt.close(fig)


def export(mlp) -> None:
    import base64

    def b64(t) -> str:
        return base64.b64encode(np.ascontiguousarray(t.detach().numpy(), dtype="<f4").tobytes()).decode()

    layers = [m for m in mlp.net if isinstance(m, torch.nn.Linear)]
    blob = {"layers": [{"out": layer.out_features, "in": layer.in_features, "w": b64(layer.weight), "b": b64(layer.bias)}
                       for layer in layers],
            "activation": "silu", **{k: getattr(mlp, k).numpy().round(8).tolist() for k in ("s_mean", "s_std", "d_mean", "d_std")},
            "state": list(tt.STATE_NAMES), "dt": tt.CONTROL_DT, "max_speed": tt.MAX_SPEED,
            "source": "examples/l23_2_learned_dynamics.py; mjcourse.worldmodel.standard model 'one_step' (1000 guided episodes, "
                      "seed 0, 20 000 steps)"}
    (OUT / "dynamics.json").write_text(json.dumps(blob))


if __name__ == "__main__":
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    OUT.mkdir(parents=True, exist_ok=True)
    train, test = standard.dataset("guided"), standard.dataset("guided_test")
    mlp = standard.model("one_step")
    part1(train, test)
    table = part2_3(train, test, mlp)
    trajectory = part4(test, mlp)
    figure(table, trajectory)
    export(mlp)
    print(f"wrote {OUT / 'horizon.png'} and {OUT / 'dynamics.json'}")
