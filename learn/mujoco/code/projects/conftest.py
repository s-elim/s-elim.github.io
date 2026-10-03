"""Projects are tested against the reference solution by default. To test your own
work, set MJC_IMPL=starter:  MJC_IMPL=starter pytest projects/p01_pendulum"""

import importlib
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def impl(request):
    folder = Path(request.fspath).parent
    name = os.environ.get("MJC_IMPL", "solution")
    sys.path.insert(0, str(folder))
    try:
        module = importlib.import_module(name)
        importlib.reload(module)
        yield module
    finally:
        sys.path.remove(str(folder))
        sys.modules.pop(name, None)
