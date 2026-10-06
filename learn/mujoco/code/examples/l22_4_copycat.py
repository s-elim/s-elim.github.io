import json
import os
from pathlib import Path

import numpy as np
import torch

from mjcourse import tabletop as tt
from mjcourse.vla import data, language, train

RUNS = Path(__file__).resolve().parents[1] / "runs" / "vla"


def part1() -> None:
    print("(1) every trained MiniVLA: final training loss and closed-loop success (train split: 100 held-out layouts; "
          "others: 60)")
    print(f"  {'vision':<10}{'state':<22}{'seed':>5}{'loss':>9}{'train':>8}{'paraphrase':>12}{'synonym':>9}{'composition':>13}")
    for vision in ("patch", "keypoint", "oracle"):
        for suffix, state in (("", "position and velocity"), ("_pos", "position")):
            for seed in (0, 1, 2):
                path = RUNS / f"minivla_{vision}_s{seed}{suffix}.json"
                if not path.exists():
                    continue
                r = json.loads(path.read_text())
                s = r["summary"]
                print(f"  {vision:<10}{state:<22}{seed:>5}{r['final_loss']:>9.4f}{s['train']:>8.2f}{s['paraphrase']:>12.2f}"
                      f"{s['synonym']:>9.2f}{s['composition']:>13.2f}")


def predict(model, frames: list[tuple], tokenizer, zero_velocity: bool = False) -> np.ndarray:
    out = []
    with torch.no_grad():
        for image, text, state in frames:
            img = torch.as_tensor(image).permute(2, 0, 1).float().unsqueeze(0) / 255.0
            words = torch.as_tensor(tokenizer(text)).unsqueeze(0)
            s = (state[:4] * train.STATE_SCALE).astype(np.float32)
            if zero_velocity:
                s = s * np.array([1, 1, 0, 0], np.float32)
            out.append(model(img, words, torch.as_tensor(s[:model.cfg.state_dim]).unsqueeze(0))[0, 0].numpy())
    return np.array(out)


def part2_3(models: dict, episodes: list[dict], tokenizer) -> None:
    first = [(e["images"][0], e["text"], e["states"][0]) for e in episodes]
    first_target = np.array([e["actions"][0] for e in episodes])
    later = [(e, t) for e in episodes for t in range(1, len(e["actions"]))]
    later_frames = [(e["images"][t], e["text"], e["states"][t]) for e, t in later]
    later_target = np.array([e["actions"][t] for e, t in later])
    copy_error = np.linalg.norm(later_target - np.array([e["actions"][t - 1] for e, t in later]), axis=1).mean()
    print(f"(2) offline action error on {len(episodes)} held-out demonstrations (mean distance; demonstrator's actions "
          f"have mean norm {np.linalg.norm(later_target, axis=1).mean():.2f})")
    print(f"  {'model':<34}{'first frame (at rest)':>22}{'later frames':>14}")
    for name, model in models.items():
        e0 = np.linalg.norm(predict(model, first, tokenizer) - first_target, axis=1).mean()
        e1 = np.linalg.norm(predict(model, later_frames, tokenizer) - later_target, axis=1).mean()
        print(f"  {name:<34}{e0:>22.3f}{e1:>14.3f}")
    print(f"  {'copy the previous action':<34}{'(none)':>22}{copy_error:>14.3f}")
    model = models["patch, position and velocity"]
    with_v = predict(model, later_frames, tokenizer)
    without_v = predict(model, later_frames, tokenizer, zero_velocity=True)
    velocity = np.array([s[2:4] for _, _, s in later_frames]) / tt.MAX_SPEED          # the velocity, as an action
    print(f"(3) the velocity model on the {len(later_frames)} later frames")
    print(f"  action change when the velocity input is set to zero: mean {np.linalg.norm(with_v - without_v, axis=1).mean():.3f}")
    print(f"  distance between its action and the velocity it is given (in action units): "
          f"{np.linalg.norm(with_v - velocity, axis=1).mean():.3f}; between the demonstrator's action and that "
          f"velocity: {np.linalg.norm(later_target - velocity, axis=1).mean():.3f}")


def part4(paths: dict, tokenizer, tasks: int = 20, seconds: int = 3) -> None:
    print(f"(4) closed loop from rest, {tasks} held-out tasks: distance between the policy's action and the demonstrator's "
          f"action at the states the policy itself visits, mean per second")
    print(f"  {'model':<34}" + "".join(f"{f'{k}-{k + 1} s':>10}" for k in range(seconds)))
    for name, path in paths.items():
        model = torch.load(path, weights_only=False)
        errors = np.zeros((tasks, 10 * seconds))
        for i in range(tasks):
            rng = np.random.default_rng([2027, i])
            text, task = language.instructions("train")[rng.integers(len(language.instructions("train")))]
            scene = tt.Tabletop()
            scene.reset(tt.sample_layout(rng, task))
            policy = train.VLAPolicy(model, tokenizer)
            for t in range(10 * seconds):
                s = scene.state()
                a = policy.act(t, scene.render("top", 64), text, s)
                errors[i, t] = np.linalg.norm(a - tt.expert(s, task))
                scene.step(a)
            scene.close()
        per_second = errors.reshape(tasks, seconds, 10).mean((0, 2))
        print(f"  {name:<34}" + "".join(f"{e:>10.3f}" for e in per_second))


def figure(paths: dict, tokenizer, index: int = 0) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng([2027, index])
    text, task = language.instructions("train")[rng.integers(len(language.instructions("train")))]
    layout = tt.sample_layout(rng, task)
    runs = {"demonstrator": None, **paths}
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.7), constrained_layout=True, sharex=True, sharey=True)
    colours = {"red": "#D55E00", "green": "#009E73", "blue": "#0072B2"}
    for ax, (name, path) in zip(axes, runs.items()):
        model = torch.load(path, weights_only=False) if path else None
        policy = train.VLAPolicy(model, tokenizer) if model else None
        scene = tt.Tabletop()
        scene.reset(layout)
        states = [scene.state()]
        for t in range(60):
            s = scene.state()
            scene.step(policy.act(t, scene.render("top", 64), text, s) if policy else tt.expert(s, task))
            states.append(scene.state())
        scene.close()
        states = np.array(states)
        for zone, (zx, zy) in tt.ZONES.items():
            ax.add_patch(plt.Circle((zy, zx), tt.SUCCESS_RADIUS, color="#bbbbbb", alpha=0.5 if zone == task[1] else 0.2))
        for k, obj in enumerate(tt.OBJECTS):
            i = 4 + 4 * k
            ax.plot(states[:, i + 1], states[:, i], color=colours[obj], lw=2 if obj == task[0] else 1)
            ax.add_patch(plt.Circle((states[0, i + 1], states[0, i]), tt.PUCK_RADIUS, fill=False, color=colours[obj], ls=":"))
        ax.plot(states[:, 1], states[:, 0], color="black", lw=1)
        ax.plot(states[0, 1], states[0, 0], "ko", ms=4)
        ax.set_title(name, fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlim(0.3, -0.3)                                            # as the top camera shows it: +y to the left
        ax.set_ylim(-0.3, 0.3)
        ax.set_xlabel("y (m)")
    axes[0].set_ylabel("x (m)")
    fig.suptitle(f'"{text}", 6 s from the same start (black: pusher; dotted: pucks at the start)', fontsize=10)
    fig.savefig(RUNS / "copycat.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    tokenizer = language.default_tokenizer()
    part1()
    paths = {"patch, position and velocity": RUNS / "minivla_patch_s0.pt", "patch, position only": RUNS / "minivla_patch_s0_pos.pt"}
    models = {k: torch.load(p, weights_only=False).eval() for k, p in paths.items()}
    episodes = [e for e in data.generate(7, 40) if e["success"]]
    part2_3(models, episodes, tokenizer)
    part4(paths, tokenizer)
    figure(paths, tokenizer)
