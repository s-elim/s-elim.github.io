import os
import time
from pathlib import Path

import numpy as np
import torch

from mjcourse import tabletop as tt
from mjcourse.vla import data, language, train
from mjcourse.vla.model import MiniVLA, VLAConfig

RUNS = Path(__file__).resolve().parents[1] / "runs"
OUT = RUNS / "l22_2"
TEXT = "push the {obj} puck to the {zone} zone"


def inputs(image: np.ndarray, text: str, state: np.ndarray, tokenizer) -> tuple:
    img = torch.as_tensor(image).permute(2, 0, 1).float().unsqueeze(0) / 255.0
    words = torch.as_tensor(tokenizer(text)).unsqueeze(0)
    s = torch.as_tensor((state[:4] * train.STATE_SCALE)[:2].astype(np.float32)).unsqueeze(0)
    return img, words, s


def part1(model: MiniVLA, frame: tuple) -> None:
    img, words, s = frame
    print("(1) one observation through the patch MiniVLA (B = 1)")
    with torch.no_grad():
        x, pad = model.tokens(img, words, s)
        vision = model.vision(img)
        fused = model.fusion(x, src_key_padding_mask=pad)
        action = model(img, words, s)
    rows = [("image, RGB in [0, 1]", img.shape), ("  + 2 coordinate channels (CoordConv)", (1, 5, 64, 64)),
            ("  conv stack -> 8 x 8 grid, D = 64 channels", (1, 64, 8, 8)), ("  vision tokens (one per cell)", vision.shape),
            ("instruction, token ids (padded to 12)", words.shape), ("  language tokens", (1, 12, 64)),
            ("pusher position, scaled", s.shape), ("  state token", (1, 1, 64)), ("action query (learned)", (1, 1, 64)),
            ("sequence: query, state, words, vision", x.shape), ("  padding mask (True = ignored)", pad.shape),
            ("after 2 transformer layers", fused.shape), ("action: the query's output -> linear -> tanh", action.shape)]
    for label, shape in rows:
        print(f"  {label:<46}{str(tuple(shape)):>18}")
    print(f"  {int(pad.sum())} of {pad.shape[1]} positions are padding for this {int((words != 0).sum())}-word instruction")


def part2(vocab: int) -> None:
    print("(2) parameters per component")
    print(f"  {'component':<34}" + "".join(f"{v:>10}" for v in ("patch", "keypoint", "oracle")))
    groups = {"vision encoder": ("vision.",), "word embeddings and positions": ("words.", "word_position"),
              "state, queries, modality embeddings": ("state.", "queries", "modality"), "transformer (2 layers)": ("fusion.",),
              "action head": ("head.",)}
    counts = {}
    for v in ("patch", "keypoint", "oracle"):
        model = MiniVLA(VLAConfig(vocab=vocab, chunk=1, vision=v, state_dim=2))
        counts[v] = {g: sum(p.numel() for n, p in model.named_parameters() if n.startswith(prefixes))
                     for g, prefixes in groups.items()}
        counts[v]["total"] = sum(p.numel() for p in model.parameters())
    for g in (*groups, "total"):
        print(f"  {g:<34}" + "".join(f"{counts[v][g]:>10,}" for v in counts))


def part3(vocab: int, frame: tuple) -> None:
    torch.set_num_threads(1)
    img, words, s = frame
    pucks = torch.zeros(1, 6)
    print("(3) one decision on one CPU thread (batch 1, median of 300 forward passes)")
    for v in ("patch", "keypoint", "oracle"):
        model = MiniVLA(VLAConfig(vocab=vocab, chunk=1, vision=v, state_dim=2)).eval()
        times = []
        with torch.no_grad():
            for _ in range(320):
                t = time.perf_counter()
                model(img, words, s, pucks)
                times.append(time.perf_counter() - t)
        print(f"  {v:<10}{1000 * np.median(times[20:]):6.2f} ms")
    torch.set_num_threads(min(8, os.cpu_count() or 1))


def attention(model: MiniVLA, frame: tuple) -> list[np.ndarray]:
    img, words, s = frame
    out = []
    with torch.no_grad():
        x, pad = model.tokens(img, words, s)
        for layer in model.fusion.layers:
            _, w = layer.self_attn(x, x, x, key_padding_mask=pad, need_weights=True, average_attn_weights=True)
            out.append(w[0, 0].numpy())
            x = layer(x, src_key_padding_mask=pad)
    return out


def pick_frame(episodes: list[dict]) -> tuple[dict, int, list[str]]:
    for e in episodes:
        zone = e["task"][1]
        objects = [o for o in tt.OBJECTS if (o, zone) in language.TRAIN_PAIRS][:2]
        pucks = e["pucks"][0].reshape(3, 2)
        d = [pucks[tt.OBJECTS.index(o)] - e["states"][0][:2] for o in objects]
        if d[0] @ d[1] < 0:
            return e, 0, objects
    raise RuntimeError("no frame with pucks on opposite sides of the pusher")


def part4(model: MiniVLA, episode: dict, t: int, objects: list[str], tokenizer) -> dict:
    zone = episode["task"][1]
    print(f"(4) attention of the action query, same image, two instructions naming different pucks")
    shown = {}
    for obj in objects:
        text = TEXT.format(obj=obj, zone=zone)
        frame = inputs(episode["images"][t], text, episode["states"][t], tokenizer)
        maps = attention(model, frame)
        n_words = int((frame[1] != 0).sum())
        with torch.no_grad():
            action = model(*frame)[0, 0].numpy()
        for k, m in enumerate(maps, 1):
            vision, words = m[14:], m[2:2 + n_words]
            cell = np.unravel_index(int(vision.argmax()), (8, 8))
            print(f"  '{text}', layer {k}: attention on image {vision.sum():.2f}, words {words.sum():.2f}, "
                  f"state {m[1]:.2f}, itself {m[0]:.2f}; most-attended image cell (row, col) ({cell[0]}, {cell[1]})")
        print(f"    predicted action {np.round(action, 2)}")
        shown[text] = {"maps": maps, "n_words": n_words, "action": action}
    return shown


def part5(model: MiniVLA, episodes: list[dict], tokenizer) -> None:
    rng = np.random.default_rng(0)
    frames = [(e, t) for e in episodes for t in rng.choice(len(e["actions"]), min(10, len(e["actions"])), replace=False)]
    changes = {k: [] for k in ("another puck named", "another zone named", "another scene's image", "another pusher position")}
    base_norm = []
    with torch.no_grad():
        for e, t in frames:
            obj, zone = e["task"]
            text = TEXT.format(obj=obj, zone=zone)
            a0 = model(*inputs(e["images"][t], text, e["states"][t], tokenizer))[0, 0].numpy()
            base_norm.append(np.linalg.norm(a0))
            other_obj = [o for o in tt.OBJECTS if o != obj and (o, zone) in language.TRAIN_PAIRS]
            other_zone = [z for z in tt.ZONES if z != zone and (obj, z) in language.TRAIN_PAIRS]
            o_e, o_t = frames[rng.integers(len(frames))]
            variants = {"another puck named": (e["images"][t], TEXT.format(obj=rng.choice(other_obj), zone=zone), e["states"][t]),
                        "another zone named": (e["images"][t], TEXT.format(obj=obj, zone=rng.choice(other_zone)), e["states"][t]),
                        "another scene's image": (o_e["images"][o_t], text, e["states"][t]),
                        "another pusher position": (e["images"][t], text, o_e["states"][o_t])}
            for k, (img, txt, st) in variants.items():
                a = model(*inputs(img, txt, st, tokenizer))[0, 0].numpy()
                changes[k].append(np.linalg.norm(a - a0))
    print(f"(5) sensitivity on {len(frames)} frames of 40 held-out demonstrations: mean change of the action when one input "
          f"is replaced (mean action norm {np.mean(base_norm):.2f}; actions are in [-1, 1] per axis)")
    for k, v in changes.items():
        v = np.array(v)
        print(f"  {k:<26} mean change {v.mean():.2f}   changed by more than 0.2 in {np.mean(v > 0.2):.2f} of frames")


def to_pixel(xy: np.ndarray, size: int = 64, fovy: float = 38.0, height: float = 0.88) -> tuple[float, float]:
    f = 0.5 * size / np.tan(np.radians(fovy) / 2)
    return -xy[1] * f / height + size / 2, -xy[0] * f / height + size / 2


def figure(episode: dict, t: int, shown: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(shown), 3, figsize=(10, 3.3 * len(shown)), constrained_layout=True,
                             gridspec_kw={"width_ratios": [1, 1, 1.4]})
    for r, (text, d) in enumerate(shown.items()):
        for k in range(2):
            ax = axes[r, k]
            ax.imshow(episode["images"][t], extent=(0, 64, 64, 0))
            grid = d["maps"][k][14:].reshape(8, 8)
            ax.imshow(grid / grid.max(), extent=(0, 64, 64, 0), cmap="magma", alpha=0.55, interpolation="nearest")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"layer {k + 1}: image attention ({d['maps'][k][14:].sum():.2f} of total)", fontsize=9)
            if k == 1:                                                # the predicted action, from the pusher
                u, v = to_pixel(episode["states"][t][:2])
                a = d["action"]
                ax.annotate("", xy=(u - 14 * a[1], v - 14 * a[0]), xytext=(u, v),
                            arrowprops={"arrowstyle": "-|>", "color": "#56B4E9", "lw": 2})
        words = text.split()
        ax = axes[r, 2]
        width = 0.38
        for k, colour in ((0, "#56B4E9"), (1, "#0072B2")):
            ax.bar(np.arange(len(words)) + (k - 0.5) * width, d["maps"][k][2:2 + len(words)], width, color=colour,
                   label=f"layer {k + 1}")
        ax.set_xticks(range(len(words)))
        ax.set_xticklabels(words, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("attention weight")
        ax.set_title(f'"{text}"', fontsize=9)
        ax.legend(frameon=False, fontsize=8)
    fig.savefig(OUT / "attention.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    tokenizer = language.default_tokenizer()
    model = torch.load(RUNS / "vla" / "minivla_patch_s0_pos.pt", weights_only=False).eval()
    episodes = [e for e in data.generate(7, 40) if e["success"]]
    first = episodes[0]
    frame = inputs(first["images"][0], TEXT.format(obj=first["task"][0], zone=first["task"][1]), first["states"][0], tokenizer)
    part1(model, frame)
    part2(len(tokenizer.vocab))
    part3(len(tokenizer.vocab), frame)
    episode, t, objects = pick_frame(episodes)
    shown = part4(model, episode, t, objects, tokenizer)
    part5(model, episodes, tokenizer)
    figure(episode, t, shown)
    print(f"wrote {OUT / 'attention.png'}")
