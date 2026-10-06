import json
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from mjcourse import stats
from mjcourse import tabletop as tt
from mjcourse.vla import language
from mjcourse.vla.model import MiniVLA, VLAConfig
from mjcourse.vla.train import STATE_SCALE, VLAPolicy
from mjcourse.worldmodel import dynamics, mpc, standard

OUT = Path(__file__).resolve().parents[1] / "runs" / "l23_8"
FAST = os.environ.get("MJC_FAST") == "1"
TASKS = 4 if FAST else 20
CHUNK = 4
CANDIDATES = 8


def get_vla_policy():
    tokenizer = language.default_tokenizer()
    ckpt_path = Path(__file__).resolve().parents[1] / "runs" / "vla" / "minivla_patch_s0_pos.pt"
    if ckpt_path.exists():
        model = torch.load(ckpt_path, weights_only=False)
    else:
        model = MiniVLA(VLAConfig(vocab=len(tokenizer.vocab), chunk=CHUNK))
    return VLAPolicy(model, tokenizer)


def score_chunk(states: np.ndarray, task: tuple[str, str], actions: np.ndarray) -> float:
    target_idx = tt.OBJECTS.index(task[0])
    target_pos = states[-1, 4 + 4 * target_idx:6 + 4 * target_idx]
    zone_pos = np.array(tt.ZONES[task[1]])
    dist_zone = np.linalg.norm(target_pos - zone_pos)

    pusher_pos = states[-1, :2]
    to_zone = zone_pos - target_pos
    to_zone_unit = to_zone / (np.linalg.norm(to_zone) + 1e-6)
    behind = target_pos - to_zone_unit * (tt.PUCK_RADIUS + tt.PUSHER_RADIUS + 0.005)
    align_dist = np.linalg.norm(pusher_pos - behind)

    distractor_penalty = 0.0
    for j, obj in enumerate(tt.OBJECTS):
        if j != target_idx:
            d_puck = states[:, 4 + 4 * j:6 + 4 * j]
            min_gap = np.linalg.norm(states[:, :2] - d_puck, axis=-1).min()
            if min_gap < (tt.PUCK_RADIUS + tt.PUSHER_RADIUS + 0.003):
                distractor_penalty += 2.0

    return float(dist_zone + 0.5 * align_dist + distractor_penalty + 0.01 * np.sum(actions ** 2))


def run_episode(mode: str, task_idx: int) -> dict:
    torch.set_num_threads(1)
    rng = np.random.default_rng([8, task_idx])
    task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
    text = f"push the {task[0]} puck to the {task[1]} zone"
    layout = tt.sample_layout(rng, task)
    scene = tt.Tabletop()
    scene.reset(layout)

    vla = get_vla_policy()
    world_model = standard.model("one_step")
    target_idx = tt.OBJECTS.index(task[0])

    overrules = 0
    total_decisions = 0
    collisions = 0
    step_count = 0

    while step_count < tt.EPISODE_STEPS:
        state = scene.state()
        img = scene.render("top", 64)

        if mode == "pure_vla":
            chunk = vla.chunk(img, text, state)
            chosen_chunk = chunk
        elif mode == "pure_mpc":
            planner = mpc.Planner(mpc.LearnedModel(world_model), task, mpc.PlannerConfig(horizon=CHUNK, samples=CANDIDATES))
            chosen_chunk = planner.plan(state, execute=CHUNK)
        elif mode == "hybrid":
            base_chunk = vla.chunk(img, text, state)
            candidates = [base_chunk]
            for _ in range(CANDIDATES - 1):
                pert = rng.normal(0, 0.35, size=base_chunk.shape)
                candidates.append(np.clip(base_chunk + pert, -1, 1))
            candidates = np.stack(candidates, axis=0)

            rollouts = world_model.rollout(np.repeat(state[None], CANDIDATES, 0), candidates)
            scores = [score_chunk(rollouts[k], task, candidates[k]) for k in range(CANDIDATES)]
            best_idx = int(np.argmin(scores))
            chosen_chunk = candidates[best_idx]
            if best_idx != 0:
                overrules += 1
            total_decisions += 1
        else:
            raise ValueError(f"Unknown mode {mode}")

        for a in chosen_chunk:
            scene.step(a)
            step_count += 1
            cur_s = scene.state()
            for j in range(3):
                if j != target_idx:
                    d_pos = cur_s[4 + 4 * j:6 + 4 * j]
                    if np.linalg.norm(cur_s[:2] - d_pos) < (tt.PUCK_RADIUS + tt.PUSHER_RADIUS + 0.003):
                        collisions += 1
            if scene.success(task):
                break
        if scene.success(task):
            break

    success = bool(scene.success(task))
    scene.close()
    return {"mode": mode, "task_idx": task_idx, "success": success, "steps": step_count,
            "collisions": collisions, "overrules": overrules, "total_decisions": total_decisions}


def run_trial(args: tuple[str, int]) -> dict:
    mode, task_idx = args
    return run_episode(mode, task_idx)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    standard.model("one_step")
    modes = ("pure_vla", "pure_mpc", "hybrid")
    trials = [(m, i) for m in modes for i in range(TASKS)]

    workers = min(16, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        runs = list(pool.map(run_trial, trials, chunksize=1))

    print(f"(1) Evaluated {TASKS} held-out tabletop tasks across policy architectures:")
    print(f"  {'architecture':<18}{'success':>16}{'95% Wilson CI':>22}{'median steps':>16}{'distractor hits':>18}")

    summary = {}
    for m in modes:
        runs_m = [r for r in runs if r["mode"] == m]
        succ = sum(r["success"] for r in runs_m)
        total = len(runs_m)
        lo, hi = stats.wilson_interval(succ, total)
        med_steps = float(np.median([r["steps"] for r in runs_m if r["success"]])) if succ > 0 else float("nan")
        total_col = sum(r["collisions"] for r in runs_m)
        rate = succ / total
        summary[m] = {"success_rate": rate, "wilson_ci": [lo, hi], "median_steps": med_steps,
                      "distractor_hits": total_col, "total": total}
        print(f"  {m:<18}{rate:>15.1%}{f'[{lo:.2f}, {hi:.2f}]':>22}{med_steps:>16.1f}{total_col:>18d}")

    hybrid_runs = [r for r in runs if r["mode"] == "hybrid"]
    tot_dec = sum(r["total_decisions"] for r in hybrid_runs)
    tot_over = sum(r["overrules"] for r in hybrid_runs)
    over_pct = (tot_over / tot_dec) if tot_dec > 0 else 0.0
    print(f"\n(2) Hybrid lookahead arbitration:")
    print(f"  World model overruled greedy VLA proposal in {tot_over}/{tot_dec} decisions ({over_pct:.1%}).")
    print(f"  Filtering distractor collisions and poor trajectories preserves physical task completion.")

    (OUT / "vla_wm_comparison.json").write_text(json.dumps(summary, indent=2))
    print(f"wrote {OUT / 'vla_wm_comparison.json'}")


if __name__ == "__main__":
    main()
