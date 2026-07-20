"""AI Facial Color Tones Analyzer: selfie -> skin/eye/eyebrow/lip/hair hex colors.

Note: the API returns hex colors and coarse names only -- there is NO
undertone field. Temperature (warm/cool/neutral) is derived downstream in
colorlab from the Lab values of these colors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from drape.api.youcam_client import SKIN_TONE, YouCamClient, YouCamError


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
    """jpg/jpeg only for this feature; callers convert PNGs before invoking.

    The live API omits fields it couldn't detect (observed: no hair_color
    when hair isn't visible), so every field except skin is optional --
    hair falls back to the eyebrow reading (eyebrows track natural hair
    depth), and eye/lip fall back to plausible neutral defaults.
    """
    handle = client.upload(SKIN_TONE, selfie)
    result = client.run_task(
        SKIN_TONE,
        {"face_angle_strictness_level": strictness},
        src=handle,
    )
    color = result.results.get("color") or {}
    skin = color.get("skin_color")
    if not skin:
        raise YouCamError(
            "The analyzer couldn't read a skin tone from this photo. Face the camera "
            "straight on in even light and try again.",
            error_code="error_face_position_invalid",
            payload=result.payload,
        )
    eyebrow = color.get("eyebrow_color") or color.get("hair_color") or "#5b4a3f"
    return FacialColors(
        skin=skin,
        hair=color.get("hair_color") or eyebrow,
        eye=color.get("eye_color") or "#4a3a30",
        eyebrow=eyebrow,
        lip=color.get("lip_color") or "#c06a6a",
        hair_name=color.get("hair_color_name", ""),
        eye_name=color.get("eye_color_name", ""),
    )
