"""Acceptance checks for capstone environments (Lesson 22.1).

    python -m mjcourse.capstone mjcourse.envs.push:PushEnv --kwargs '{"action_mode": "ee_delta"}' --object puck

The environment must follow the course's MujocoEnv conventions (Level 12): `model`, `data`,
`max_episode_steps`, `observation_sources` and `_get_obs()`. The checks are Gymnasium's own checker and
the five checks of mjcourse.envs.checks; the compiled model's fingerprint is printed for the run record.
A capstone passes when every check passes; the checks do not judge the research, only the instrument.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import warnings

from gymnasium.utils.env_checker import check_env

from mjcourse.envs import checks
from mjcourse.experiment import model_fingerprint


def check(make_env, object_body: str | None = None, object_geom: str | None = None) -> dict:
    """Run every check; returns {name: (passed, detail)}."""
    results = {}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            check_env(make_env(), skip_render_check=True)
        results["gymnasium check_env"] = (True, "")
    except Exception as err:                                     # the checker raises on any violation
        results["gymnasium check_env"] = (False, str(err).splitlines()[0])
    results["observations are copies"] = (checks.observations_are_copies(make_env()), "")
    results["time limit reported as truncation"] = (checks.truncation_is_reported(make_env()), "")
    results["reproducible with a seed"] = (checks.reproducible(make_env), "")
    undeclared = checks.undeclared_sources(make_env())
    results["observation sources are sensors"] = (not undeclared, ", ".join(undeclared))
    if object_body:
        leaks = checks.perturbation_leaks(make_env(), body=object_body, geom=object_geom or object_body)
        results["no privileged quantity leaks"] = (not leaks, ", ".join(leaks))
    results["model fingerprint"] = (True, model_fingerprint(make_env().model))
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", help="module:Class of the environment")
    parser.add_argument("--kwargs", default="{}", help="constructor arguments as JSON")
    parser.add_argument("--object", default=None, help="body (and geom) of the manipulated object, for the leak check")
    args = parser.parse_args(argv)
    module, name = args.target.split(":")
    cls = getattr(importlib.import_module(module), name)
    kwargs = json.loads(args.kwargs)
    results = check(lambda: cls(**kwargs), args.object)
    for label, (ok, detail) in results.items():
        print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f": {detail}" if detail else ""))
    return 0 if all(ok for ok, _ in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
