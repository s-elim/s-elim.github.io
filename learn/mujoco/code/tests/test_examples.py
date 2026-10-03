"""Every lesson example script runs to completion. The lessons embed these
files verbatim (tools/check_content.py enforces that), so a passing test means
the code a learner copies from a lesson runs against MuJoCo 3.14.0.

Scripts may declare one requirement on a line of its own:
    # requires: render    needs an OpenGL backend (skipped without one)
    # requires: display   needs a window; only byte-compiled here
    # requires: torch     needs PyTorch (skipped without it)
"""

import os
import py_compile
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import HAS_GL

EXAMPLES = sorted((Path(__file__).resolve().parents[1] / "examples").glob("*.py"))


def _requirements(script: Path) -> set[str]:
    return {line.split(":", 1)[1].strip() for line in script.read_text().splitlines()
            if line.startswith("# requires:")}


def _has_torch() -> bool:
    return subprocess.run([sys.executable, "-c", "import torch"], capture_output=True).returncode == 0


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.name)
def test_example_runs(script, tmp_path):
    needs = _requirements(script)
    if "display" in needs:
        py_compile.compile(str(script), cfile=str(tmp_path / "x.pyc"), doraise=True)
        pytest.skip("needs a display: byte-compiled only")
    if "render" in needs and not HAS_GL:
        pytest.skip("needs an OpenGL backend (MUJOCO_GL=egl or osmesa)")
    if "torch" in needs and not _has_torch():
        pytest.skip("needs PyTorch")
    env = {**os.environ, "MJC_FAST": "1", "MPLBACKEND": "Agg"}
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=900, env=env,
                          cwd=tmp_path)
    assert proc.returncode == 0, f"{script.name} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-4000:]}"
