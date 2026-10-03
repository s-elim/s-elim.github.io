"""Shared pytest fixtures."""

import os

import pytest


def _has_gl() -> bool:
    try:
        import mujoco

        m = mujoco.MjModel.from_xml_string("<mujoco><worldbody><geom size='.1'/></worldbody></mujoco>")
        r = mujoco.Renderer(m, 32, 32)
        r.close()
        return True
    except Exception:  # noqa: BLE001 - any GL failure means "no rendering here"
        return False


HAS_GL = _has_gl()


def pytest_collection_modifyitems(config, items):
    skip_render = pytest.mark.skip(reason="no OpenGL context; set MUJOCO_GL=egl or osmesa")
    for item in items:
        if "render" in item.keywords and not HAS_GL:
            item.add_marker(skip_render)


@pytest.fixture(scope="session")
def has_gl() -> bool:
    return HAS_GL


@pytest.fixture(autouse=True)
def _quiet_numpy():
    import numpy as np

    with np.errstate(all="raise"):
        yield


os.environ.setdefault("PYTHONHASHSEED", "0")
