import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from drape import config
from drape.api.youcam_client import YouCamClient


@pytest.fixture(scope="session", autouse=True)
def assets():
    """Generate drapes and personas once if missing."""
    from scripts import make_drapes, make_personas

    if not any(config.DRAPES_DIR.glob("*.jpg")):
        config.DRAPES_DIR.mkdir(parents=True, exist_ok=True)
        from drape.colorlab import seasons
        from drape.colorlab.lab import hex_to_rgb

        for drape_id, (hex_, _name) in seasons.all_drape_colors().items():
            make_drapes.draw_tee(hex_to_rgb(hex_)).save(config.DRAPES_DIR / f"{drape_id}.jpg", quality=92)
    persona_dir = config.ASSETS_DIR / "personas"
    if not persona_dir.exists() or not any(persona_dir.glob("*.jpg")):
        for name, c in make_personas.PERSONAS.items():
            make_personas.make(name, c["skin"], c["hair"], c["eye"])


@pytest.fixture()
def mock_client(tmp_path):
    return YouCamClient(mock=True, cache_dir=tmp_path / "cache")


@pytest.fixture()
def persona_dir():
    return config.ASSETS_DIR / "personas"
