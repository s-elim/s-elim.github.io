from __future__ import annotations

import numpy as np
import torch

from mjcourse import tabletop as tt
from mjcourse.vla import language, train

CONDITIONS = ("in distribution", "paraphrase", "synonym", "composition", "larger pucks", "recoloured", "near the rim",
              "crowded", "camera shifted", "larger pusher", "slower pusher")
AXES = {"in distribution": "none", "paraphrase": "language", "synonym": "language", "composition": "language",
        "larger pucks": "object", "recoloured": "object", "near the rim": "spatial", "crowded": "initial state",
        "camera shifted": "camera", "larger pusher": "embodiment", "slower pusher": "embodiment"}
RECOLOURED = {"red": (0.85, 0.4, 0.1), "green": (0.1, 0.6, 0.55), "blue": (0.35, 0.25, 0.85)}


def setup(condition: str, rng: np.random.Generator):
    split = condition if condition in ("paraphrase", "synonym", "composition") else "train"
    instructions = language.instructions(split)
    text, task = instructions[rng.integers(len(instructions))]
    variation = {"larger pucks": tt.Variation(puck_radius=0.036), "recoloured": tt.Variation(colours=RECOLOURED),
                 "larger pusher": tt.Variation(pusher_radius=0.025), "slower pusher": tt.Variation(max_speed=0.15)}.get(condition)
    if condition == "near the rim":
        while True:
            layout = tt.sample_layout(rng, task, low=-0.26, high=0.26, min_gap=0.09)
            if all(max(abs(x), abs(y)) > 0.2 for x, y in layout.pucks):
                break
    elif condition == "crowded":
        while True:
            layout = tt.sample_layout(rng, task, low=-0.15, high=0.15, min_gap=0.065)
            gaps = [np.linalg.norm(np.subtract(a, b)) for i, a in enumerate(layout.pucks) for b in layout.pucks[i + 1:]]
            if max(gaps) < 0.16 and min(gaps) < 0.1:
                break
    else:
        layout = tt.sample_layout(rng, task)
    camera = "top_shifted" if condition == "camera shifted" else "top"
    return text, task, layout, variation, camera


def run(model, condition: str, rng: np.random.Generator, tokenizer=None) -> dict:
    text, task, layout, variation, camera = setup(condition, rng)
    policy = train.VLAPolicy(model, tokenizer or language.default_tokenizer())
    result = train.run_episode(policy, text, task, layout, variation, camera, record=True)
    states, actions = np.array(result["log"]["states"]), np.array(result["log"]["actions"])
    target = tt.OBJECTS.index(task[0])
    pucks = [states[:, 4 + 4 * k:6 + 4 * k] for k in range(3)]
    moved = [float(np.linalg.norm(p[-1] - p[0])) for p in pucks]
    closest = [float(np.min(np.linalg.norm(states[:, :2] - p, axis=1))) for p in pucks]
    final = result["final"][4 + 4 * target:6 + 4 * target]
    zone = tt.ZONES[task[1]]
    start = pucks[target][0]
    displacement = final - start
    # Cosine between the target puck's displacement and the direction to its zone; undefined if it moved under 1 cm.
    toward = (float(displacement @ (zone - start) / (np.linalg.norm(zone - start) * np.linalg.norm(displacement)))
              if np.linalg.norm(displacement) > 0.01 else float("nan"))
    speed = (variation or tt.Variation()).max_speed
    commanded = actions[:-1] * speed
    achieved = states[1:, 2:4]
    return {"condition": condition, "axis": AXES[condition], "text": text, "task": list(task), "success": bool(result["success"]),
            "steps": result["steps"], "moved": moved, "closest": closest, "target": target,
            "final_distance": float(np.linalg.norm(final - zone)), "toward_zone": toward,
            "velocity_error": float(np.mean(np.linalg.norm(commanded - achieved, axis=1))) if len(achieved) else 0.0,
            "layout": {"pusher": list(layout.pusher), "pucks": [list(p) for p in layout.pucks]}}


def evaluate_one(args) -> dict:
    model_path, condition, seed, index = args
    torch.set_num_threads(1)
    model = torch.load(model_path, weights_only=False)
    rng = np.random.default_rng([seed, CONDITIONS.index(condition), index])
    return run(model, condition, rng)
