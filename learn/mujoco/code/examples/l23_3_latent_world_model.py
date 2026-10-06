import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from mjcourse import tabletop as tt
from mjcourse.worldmodel import data, latent, standard

OUT = Path(__file__).resolve().parents[1] / "runs" / "l23_3"
FAST = os.environ.get("MJC_FAST") == "1"
TRAIN, TEST, STEPS = (40, 8, 300) if FAST else (600, 50, 30000)
HORIZONS = (1, 5, 10, 20)


def collect(seed: int, n: int) -> list[dict]:
    with ProcessPoolExecutor(min(32, os.cpu_count() or 1), mp_context=multiprocessing.get_context("spawn")) as pool:
        return list(pool.map(data._collect, [(seed, i, {"render": True}) for i in range(n)], chunksize=2))


def train(objective: str) -> str:
    torch.set_num_threads(max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", 16)) // 2))
    episodes = collect_cached(10, TRAIN)
    model = latent.fit(episodes, objective, steps=STEPS, log=lambda m: print(f"  [{objective}] {m}", flush=True))
    path = OUT / f"latent_{objective}.pt"
    torch.save(model, path)
    return str(path)


def collect_cached(seed: int, n: int) -> list[dict]:
    import pickle

    path = OUT / f"images_{seed}_{n}.pkl"
    if not path.exists():
        path.write_bytes(pickle.dumps(collect(seed, n)))
    return pickle.loads(path.read_bytes())


def score(episodes: list[dict], predict, starts_per_episode: int = 4) -> dict:
    rng = np.random.default_rng(0)
    rows = {h: {"pixel": [], "puck": [], "missing": []} for h in HORIZONS}
    for e in episodes:
        target = tt.OBJECTS.index(e["task"][0])
        for t0 in rng.integers(0, len(e["actions"]) - max(HORIZONS), starts_per_episode):
            pred = predict(e, t0, max(HORIZONS))
            for h in HORIZONS:
                true_img, img = e["images"][t0 + h], pred[h]
                rows[h]["pixel"].append(np.mean((img.astype(float) - true_img.astype(float)) ** 2) / 255.0 ** 2)
                found = latent.puck_positions(img)[tt.OBJECTS[target]]
                rows[h]["missing"].append(found is None)
                if found is not None:
                    rows[h]["puck"].append(np.linalg.norm(found - e["states"][t0 + h][4 + 4 * target:6 + 4 * target]))
    return {h: {"pixel": float(np.mean(r["pixel"])), "puck": float(np.mean(r["puck"])) if r["puck"] else float("nan"),
                "missing": float(np.mean(r["missing"]))} for h, r in rows.items()}


def state_model_errors(episodes: list[dict]) -> dict:
    mlp = standard.model("one_step")
    rng = np.random.default_rng(0)
    rows = {h: [] for h in HORIZONS}
    for e in episodes:
        target = tt.OBJECTS.index(e["task"][0])
        for t0 in rng.integers(0, len(e["actions"]) - max(HORIZONS), 4):
            pred = mlp.rollout(e["states"][t0][None], e["actions"][None, t0:t0 + max(HORIZONS)])[0]
            for h in HORIZONS:
                i = 4 + 4 * target
                rows[h].append(np.linalg.norm(pred[h, i:i + 2] - e["states"][t0 + h][i:i + 2]))
    return {h: float(np.mean(v)) for h, v in rows.items()}


def figure(episode: dict, models: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    shown = (0, 5, 10, 20)
    rows = {"MuJoCo (true)": [episode["images"][20 + h] for h in shown]}
    for name, model in models.items():
        pred = model.predict(episode["images"][20], episode["actions"][20:40])
        rows[f"latent model, {name}"] = [pred[h] for h in shown]
    fig, axes = plt.subplots(len(rows), len(shown), figsize=(2.0 * len(shown), 2.1 * len(rows)), constrained_layout=True)
    for r, (label, images) in enumerate(rows.items()):
        for c, img in enumerate(images):
            axes[r, c].imshow(img)
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])
            if r == 0:
                axes[r, c].set_title(f"{shown[c] / 10:.1f} s ahead", fontsize=9)
            if c == 0:
                axes[r, c].set_ylabel(label, fontsize=8)
    fig.savefig(OUT / "frames.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    train_eps, test_eps = collect_cached(10, TRAIN), collect_cached(11, TEST)
    print(f"(1) {TRAIN} training and {TEST} held-out episodes with images; detector error on true images "
          f"{1000 * latent.detector_error(test_eps):.2f} mm")
    with ProcessPoolExecutor(2, mp_context=multiprocessing.get_context("spawn")) as pool:
        paths = dict(zip(("pixels", "positions"), pool.map(train, ("pixels", "positions"))))
    models = {k: torch.load(p, weights_only=False) for k, p in paths.items()}
    print(f"(2) trained two latent models, {STEPS} steps each")
    print("(3) open-loop prediction on held-out states")
    results = {"first image copied forward": score(test_eps, lambda e, t0, h: e["images"][t0:t0 + h + 1].repeat(h + 1, 0))}
    for name, model in models.items():
        results[f"latent, {name}"] = score(test_eps, lambda e, t0, h, m=model: m.predict(e["images"][t0], e["actions"][t0:t0 + h]))
    print(f"  {'model':<28}{'quantity':<26}" + "".join(f"{h:>9d}" for h in HORIZONS) + "   (steps of 0.1 s)")
    for name, res in results.items():
        print(f"  {name:<28}{'pixel MSE (x 1000)':<26}" + "".join(f"{1000 * res[h]['pixel']:9.2f}" for h in HORIZONS))
        print(f"  {'':<28}{'pushed puck error (mm)':<26}" + "".join(f"{1000 * res[h]['puck']:9.1f}" for h in HORIZONS))
        print(f"  {'':<28}{'pushed puck missing':<26}" + "".join(f"{res[h]['missing']:9.2f}" for h in HORIZONS))
    sm = state_model_errors(test_eps)
    print(f"  {'state model (23.2)':<28}{'pushed puck error (mm)':<26}" + "".join(f"{1000 * sm[h]:9.1f}" for h in HORIZONS))
    figure(test_eps[2], models)
    print(f"wrote {OUT / 'frames.png'}")
