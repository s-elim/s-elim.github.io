"""Projects are tested against the reference solution by default. To test your own
work, set MJC_IMPL=starter:  MJC_IMPL=starter pytest projects/p01_pendulum"""

import importlib
import os
import sys
from pathlib import Path

import pytest


def _has_gl() -> bool:
    try:
        import mujoco

        model = mujoco.MjModel.from_xml_string("<mujoco><worldbody><geom size='.1'/></worldbody></mujoco>")
        mujoco.Renderer(model, 32, 32).close()
        return True
    except Exception:  # noqa: BLE001 - any GL failure means "no rendering here"
        return False


def pytest_collection_modifyitems(config, items):
    """Tests marked `render` need an OpenGL context (MUJOCO_GL=egl or osmesa on a headless machine)."""
    if any("render" in item.keywords for item in items) and not _has_gl():
        skip = pytest.mark.skip(reason="no OpenGL context; set MUJOCO_GL=egl or osmesa")
        for item in items:
            if "render" in item.keywords:
                item.add_marker(skip)


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
