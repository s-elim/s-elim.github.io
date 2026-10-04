"""Experiment records for MuJoCo studies (Level 21): what a reviewer will ask for, written by code.

A study states its protocol before it runs (`Protocol`), and every run writes a record with the protocol,
the software versions, a hash of each model file and a fingerprint of each compiled model, the
configuration and the results (`run_record`). The fingerprint covers the compiled model's numbers, so it
also changes when code edits a model after loading it, which a hash of the XML file cannot see.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import platform
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path

import mujoco
import numpy as np


@dataclasses.dataclass(frozen=True)
class Protocol:
    """Everything decided before the first run. Fields are free text where a number would hide a choice."""

    name: str
    hypothesis: str
    task: str
    initial_states: str
    success: str
    metric: str
    train_seeds: tuple[int, ...] = ()
    eval_seeds: tuple[int, ...] = ()
    falsified_if: str = ""


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model_fingerprint(model: mujoco.MjModel) -> str:
    """SHA-256 over every numeric array of the compiled model and its options."""
    digest = hashlib.sha256()
    for name in sorted(dir(model)):
        if name.startswith("_"):
            continue
        try:
            value = getattr(model, name)
        except Exception:
            continue
        if isinstance(value, np.ndarray):
            digest.update(name.encode())
            digest.update(np.ascontiguousarray(value).tobytes())
    for name in sorted(n for n in dir(model.opt) if not n.startswith("_")):
        value = getattr(model.opt, name)
        if isinstance(value, (int, float, np.ndarray)):
            digest.update(name.encode())
            digest.update(np.asarray(value).tobytes())
    return digest.hexdigest()


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def software() -> dict:
    """Versions a result depends on, and the code's git commit when run inside a repository."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        commit = None
    return {"python": sys.version.split()[0], "platform": platform.platform(), "mujoco": mujoco.__version__,
            "numpy": np.__version__, **{p: _version(p) for p in ("gymnasium", "torch", "scipy")}, "git_commit": commit}


def run_record(protocol: Protocol, models: dict[str, tuple[mujoco.MjModel, str | Path | None]], config: dict,
               results: dict) -> dict:
    """models maps a name to (compiled model, its XML file or None)."""
    return {"protocol": dataclasses.asdict(protocol),
            "software": software(),
            "models": {name: {"file_sha256": file_sha256(path) if path else None, "fingerprint": model_fingerprint(m),
                              "timestep": m.opt.timestep, "integrator": mujoco.mjtIntegrator(m.opt.integrator).name}
                       for name, (m, path) in models.items()},
            "config": config,
            "results": results,
            "written": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


def save(record: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, default=float))
    return path
