"""Filesystem locations used across the package."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
MODELS_DIR = PACKAGE_DIR / "models"


def model_path(name: str) -> Path:
    """Resolve a model name ("pendulum" or "pendulum.xml") to its file path."""
    filename = name if name.endswith(".xml") else f"{name}.xml"
    path = MODELS_DIR / filename
    if not path.exists():
        available = sorted(p.stem for p in MODELS_DIR.glob("*.xml"))
        raise FileNotFoundError(f"no model {filename!r} in {MODELS_DIR}; available: {available}")
    return path
