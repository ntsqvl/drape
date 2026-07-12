"""AI Facial Color Tones Analyzer: selfie -> skin/eye/eyebrow/lip/hair hex colors.

Note: the API returns hex colors and coarse names only -- there is NO
undertone field. Temperature (warm/cool/neutral) is derived downstream in
colorlab from the Lab values of these colors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from drape.api.youcam_client import SKIN_TONE, YouCamClient


@dataclass
class FacialColors:
    skin: str
    hair: str
    eye: str
    eyebrow: str
    lip: str
    hair_name: str
    eye_name: str


def analyze(client: YouCamClient, selfie: str | Path, *, strictness: str = "medium") -> FacialColors:
    """jpg/jpeg only for this feature; callers convert PNGs before invoking."""
    handle = client.upload(SKIN_TONE, selfie)
    result = client.run_task(
        SKIN_TONE,
        {"face_angle_strictness_level": strictness},
        src=handle,
    )
    color = result.results["color"]
    return FacialColors(
        skin=color["skin_color"],
        hair=color["hair_color"],
        eye=color["eye_color"],
        eyebrow=color["eyebrow_color"],
        lip=color["lip_color"],
        hair_name=color.get("hair_color_name", ""),
        eye_name=color.get("eye_color_name", ""),
    )
