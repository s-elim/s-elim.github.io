"""Every lesson example script runs to completion. The lessons embed these
files verbatim (tools/check_content.py enforces that), so a passing test means
the code a learner copies from a lesson runs against MuJoCo 3.14.0."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).resolve().parents[1] / "examples").glob("*.py"))


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.name)
def test_example_runs(script):
    if "torch" in script.read_text() and subprocess.run([sys.executable, "-c", "import torch"]).returncode:
        pytest.skip("needs PyTorch")
    env = {**os.environ, "MJC_FAST": "1", "MPLBACKEND": "Agg"}
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=600, env=env)
    assert proc.returncode == 0, f"{script.name} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-4000:]}"
