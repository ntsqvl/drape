"""AI Clothes (cloth-v3): selfie + garment reference image -> try-on render.

Source photo requirements per docs: single person, chest-up, face fully
visible, front-facing, person >= 80% of frame. Reference: front-facing
product shot of a single garment.
"""

from __future__ import annotations

from pathlib import Path

import requests

from drape import config
from drape.api.youcam_client import CLOTH, FileHandle, YouCamClient

UPPER_BODY = "upper_body"


def try_on(
    client: YouCamClient,
    selfie: FileHandle | str | Path,
    garment: str | Path,
    *,
    garment_category: str = UPPER_BODY,
) -> Path:
    """Render `garment` on `selfie`; returns a local path to the result image.

    `selfie` may be a pre-uploaded cloth-v3 FileHandle so a draping session
    uploads the user photo once and reuses it across every drape render.
    """
    if not isinstance(selfie, FileHandle):
        selfie = client.upload(CLOTH, selfie)
    garment_handle = client.upload(CLOTH, garment)
    result = client.run_task(
        CLOTH,
        {"ref_file_id": garment_handle.file_id, "garment_category": garment_category},
        src=selfie,
        cache_extra=str(garment),
    )
    url = result.results["url"]
    return _materialize(url)


def _materialize(url: str) -> Path:
    """Result URLs are short-lived S3 links; download immediately."""
    if url.startswith("file://"):
        return Path(url.removeprefix("file://"))
    config.RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    name = url.split("?")[0].rsplit("/", 1)[-1] or "render.jpg"
    dst = config.RENDERS_DIR / name
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dst.write_bytes(resp.content)
    return dst
