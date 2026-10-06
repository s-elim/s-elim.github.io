import argparse
import json
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mjcourse import stats
from mjcourse.vla import evaluation as ev

FAST = os.environ.get("MJC_FAST") == "1"
RUNS = Path(__file__).resolve().parents[1] / "runs" / "vla"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vision", default="keypoint", choices=["patch", "keypoint", "oracle"])
    parser.add_argument("--seeds", type=int, nargs="+", default=[0] if FAST else [0, 1, 2])
    parser.add_argument("--episodes", type=int, default=2 if FAST else int(os.environ.get("MJC_EPISODES", "100")))
    args = parser.parse_args()
    models = {s: RUNS / f"minivla_{args.vision}_s{s}_pos.pt" for s in args.seeds}
    missing = [str(p) for p in models.values() if not p.exists()]
    if missing:
        raise SystemExit(f"train these first (examples/l22_4_train_minivla.py --state 2): {missing}")
    jobs = [(str(path), c, 3000 + seed, i) for seed, path in models.items() for c in ev.CONDITIONS for i in range(args.episodes)]
    workers = int(os.environ.get("SLURM_CPUS_PER_TASK", min(32, os.cpu_count() or 1)))
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        records = list(pool.map(ev.evaluate_one, jobs, chunksize=4))
    for job, rec in zip(jobs, records):
        rec["model_seed"] = int(Path(job[0]).stem.split("_s")[1].split("_")[0])
    (RUNS / f"eval_{args.vision}.json").write_text(json.dumps(records))
    print(f"MiniVLA ({args.vision}), {len(args.seeds)} seeds, {args.episodes} episodes per condition and seed")
    print(f"  {'condition':<16}{'axis':<15}{'success per seed [95% Wilson]':<62}{'mean':>6}{'gap to in distribution':>26}")
    base = {s: np.mean([r["success"] for r in records if r["condition"] == "in distribution" and r["model_seed"] == s])
            for s in args.seeds}
    for c in ev.CONDITIONS:
        cells, rates = [], []
        for s in args.seeds:
            ok = [r["success"] for r in records if r["condition"] == c and r["model_seed"] == s]
            lo, hi = stats.wilson_interval(int(sum(ok)), len(ok))
            cells.append(f"{np.mean(ok):.2f} [{lo:.2f}, {hi:.2f}]")
            rates.append(np.mean(ok))
        gaps = [rates[j] - base[s] for j, s in enumerate(args.seeds)]
        gap = "" if c == "in distribution" else f"{np.mean(gaps):+.2f} ({', '.join(f'{g:+.2f}' for g in gaps)})"
        print(f"  {c:<16}{ev.AXES[c]:<15}{'  '.join(cells):<62}{np.mean(rates):>6.2f}{gap:>26}")
    print(f"wrote {RUNS / f'eval_{args.vision}.json'}")


if __name__ == "__main__":
    main()
