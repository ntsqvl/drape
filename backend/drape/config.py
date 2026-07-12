import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

API_BASE = os.environ.get("YOUCAM_API_BASE", "https://yce-api-01.makeupar.com")
API_KEY = os.environ.get("YOUCAM_API_KEY", "")
MOCK = os.environ.get("YOUCAM_MOCK", "0") == "1"
CACHE_DIR = Path(os.environ.get("DRAPE_CACHE_DIR", ".cache/youcam"))

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = BACKEND_ROOT / "assets"
DRAPES_DIR = ASSETS_DIR / "drapes"
RENDERS_DIR = ASSETS_DIR / "renders"
