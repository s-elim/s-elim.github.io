import argparse
import json
import multiprocessing
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import torch

from mjcourse.vla import diagnosis
from mjcourse.vla import evaluation as ev

RUNS = Path(__file__).resolve().parents[1] / "runs" / "vla"
_MODELS: dict = {}


def _load(path: str):
    if path not in _MODELS:
        _MODELS[path] = torch.load(path, weights_only=False)
    return _MODELS[path]


def job(args) -> dict:
    vision, record = args
    torch.set_num_threads(1)
    seed = record["model_seed"]
    model = _load(str(RUNS / f"minivla_{vision}_s{seed}_pos.pt"))
    oracle = _load(str(RUNS / f"minivla_oracle_s{seed}_pos.pt"))
    return {**diagnosis.diagnose(record, model, oracle), "condition": record["condition"], "seed": seed, "text": record["text"]}


FAST = os.environ.get("MJC_FAST") == "1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vision", default="patch", choices=["patch", "keypoint"])
    args = parser.parse_args()
    records = json.loads((RUNS / f"eval_{args.vision}.json").read_text())
    failures = [r for r in records if not r["success"]]
    if FAST:
        failures = failures[:4]
    workers = int(os.environ.get("SLURM_CPUS_PER_TASK", min(32, os.cpu_count() or 1)))
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        verdicts = list(pool.map(job, [(args.vision, r) for r in failures], chunksize=2))
    (RUNS / f"diagnosis_{args.vision}.json").write_text(json.dumps(verdicts))
    print(f"{len(failures)} failures of {len(records)} episodes (MiniVLA, {args.vision}), attributed to the first repaired stage")
    print(f"  {'condition':<16}{'failures':>9}" + "".join(f"{s:>20}" for s in diagnosis.STAGES))
    for c in ev.CONDITIONS:
        counts = Counter(v["stage"] for v in verdicts if v["condition"] == c)
        n = sum(counts.values())
        print(f"  {c:<16}{n:>9}" + "".join(f"{counts[s]:>20}" for s in diagnosis.STAGES))
    total = Counter(v["stage"] for v in verdicts)
    print(f"  {'all':<16}{len(verdicts):>9}" + "".join(f"{total[s]:>20}" for s in diagnosis.STAGES))
    print(f"wrote {RUNS / f'diagnosis_{args.vision}.json'}")


if __name__ == "__main__":
    main()
