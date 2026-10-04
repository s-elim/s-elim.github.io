"""Check that a project's tests catch the common failures its README lists.

INPUT   code/projects/<slug>/mutants.json:
            {"name": {"edits": {"file": [[old, new], ...]}, "caught_by": ["test_name", ...]}, ...}
        A mutant with "expect_survival": true is a control that must pass every test.
PROCESS for each mutant: copy the project into a temporary folder, apply the edits to the
        reference files, run the project's tests against the mutated reference, and record
        which tests failed
OUTPUT  one line per mutant; exit status 1 if a mutant survives (no test fails), is not
        caught by every test named in "caught_by", or is a control that some test rejects

Usage:  python tools/mutate_project.py p05_ik [p04_joint_pd ...]
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "code" / "projects"


def run_mutant(slug: str, edits: dict[str, list[list[str]]]) -> set[str]:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / slug
        shutil.copytree(PROJECTS / slug, work, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(PROJECTS / "conftest.py", work / "conftest.py")   # pytest only loads conftests under its rootdir
        for name, pairs in edits.items():
            path = work / name
            text = path.read_text()
            for old, new in pairs:
                if old not in text:
                    raise SystemExit(f"{slug}: edit target not found in {name}: {old[:60]!r}")
                text = text.replace(old, new)
            path.write_text(text)
        env = {**os.environ, "MJC_IMPL": "solution",
               "PYTHONPATH": os.pathsep.join([str(ROOT / "code" / "src"), os.environ.get("PYTHONPATH", "")])}
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rfE", str(work)],
                                env=env, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):                  # 2+ means pytest itself failed: collection, fixtures, usage
        raise SystemExit(f"{slug}: pytest exited {result.returncode}\n{result.stdout[-2000:]}")
    return {line.split("::")[1].split(" ")[0].split("[")[0]            # a test that errors has not passed either
            for line in result.stdout.splitlines() if line.startswith(("FAILED", "ERROR"))}


def main(slugs: list[str]) -> int:
    status = 0
    for slug in slugs:
        mutants = json.loads((PROJECTS / slug / "mutants.json").read_text())
        for name, spec in mutants.items():
            failed = run_mutant(slug, spec["edits"])
            if spec.get("expect_survival"):              # a control: an edit that changes nothing physical
                ok, label = not failed, "harmless" if not failed else "CAUGHT?!"
            else:
                missing = set(spec["caught_by"]) - failed
                ok, label = bool(failed) and not missing, "caught  " if failed and not missing else "SURVIVED"
            status |= not ok
            print(f"{label} {slug}: {name}: failed {sorted(failed)}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
