import argparse
import json
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from mjcourse import tabletop as tt
from mjcourse.vla import data, language, train
from mjcourse.vla.model import VLAConfig

FAST = os.environ.get("MJC_FAST") == "1"
OUT = Path(__file__).resolve().parents[1] / "runs" / "vla"
EPISODES = {"train": 2, "paraphrase": 1, "synonym": 1, "composition": 1} if FAST else {"train": 100, "paraphrase": 60, "synonym": 60, "composition": 60}


def evaluate_one(args) -> dict:
    model_path, split, index = args
    torch.set_num_threads(1)
    model = torch.load(model_path, weights_only=False)
    rng = np.random.default_rng([2026, index])                        # layouts the demonstrations never used
    instructions = language.instructions(split)
    text, task = instructions[rng.integers(len(instructions))]
    layout = tt.sample_layout(rng, task)
    result = train.run_episode(train.VLAPolicy(model, language.default_tokenizer()), text, task, layout)
    return {"split": split, "index": index, "text": text, "task": list(task), "success": bool(result["success"]),
            "steps": result["steps"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vision", default="keypoint", choices=["patch", "keypoint", "oracle"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--steps", type=int, default=100 if FAST else 30000)
    parser.add_argument("--demos", type=int, default=20 if FAST else 3000)
    parser.add_argument("--state", type=int, default=2, choices=[2, 4], help="2: pusher position (the course default); 4: position and velocity (Lesson 22.4, the copycat)")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", min(16, os.cpu_count() or 1)))
    torch.set_num_threads(cpus)
    name = (f"minivla_{args.vision}_s{args.seed}" + ("" if args.demos == 3000 else f"_d{args.demos}")
            + ("" if args.state == 4 else "_pos"))
    episodes = data.cached(0, 3000, "train")[:args.demos]
    tokenizer = language.default_tokenizer()
    arrays = data.to_arrays(episodes, tokenizer, 1)
    print(f"{name}: {sum(e['success'] for e in episodes)} successful demonstrations, {len(arrays['images'])} frames", flush=True)
    start = time.perf_counter()
    model, losses = train.fit(arrays, len(tokenizer.vocab), steps=args.steps, seed=args.seed,
                              cfg=VLAConfig(vocab=len(tokenizer.vocab), chunk=1, vision=args.vision, state_dim=args.state),
                              log=lambda m: print(m, flush=True))
    seconds = time.perf_counter() - start
    path = OUT / f"{name}.pt"
    torch.save(model, path)
    jobs = [(str(path), split, i) for split, n in EPISODES.items() for i in range(n)]
    with ProcessPoolExecutor(cpus, mp_context=multiprocessing.get_context("spawn")) as pool:
        episodes_out = list(pool.map(evaluate_one, jobs, chunksize=2))
    summary = {split: float(np.mean([e["success"] for e in episodes_out if e["split"] == split])) for split in EPISODES}
    record = {"vision": args.vision, "seed": args.seed, "steps": args.steps, "demos": args.demos, "state": args.state,
              "train_seconds": seconds,
              "final_loss": float(np.mean(losses[-1000:])), "summary": summary, "episodes": episodes_out}
    (OUT / f"{name}.json").write_text(json.dumps(record, indent=1))
    print(json.dumps({k: v for k, v in record.items() if k != "episodes"}), flush=True)


if __name__ == "__main__":
    main()
