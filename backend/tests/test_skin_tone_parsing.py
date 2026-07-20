"""The live tone analyzer omits fields it can't detect (observed: no
hair_color when hair isn't visible). Parsing must degrade, not crash."""

import pytest

from drape.api import skin_tone
from drape.api.youcam_client import FileHandle, TaskResult, YouCamError


class StubClient:
    def __init__(self, color):
        self._color = color

    def upload(self, feature, path):
        return FileHandle(feature, "id", "digest")

    def run_task(self, feature, params, *, src=None, cache_extra="", force=False):
        return TaskResult(feature, "t", {"results": {"color": self._color}})


def test_missing_hair_falls_back_to_eyebrow():
    colors = skin_tone.analyze(
        StubClient({"skin_color": "#af8b72", "eyebrow_color": "#3e3834", "eye_color": "#271b1e", "lip_color": "#dc7e81"}),
        "x.jpg",
    )
    assert colors.hair == "#3e3834"
    assert colors.eyebrow == "#3e3834"


def test_only_skin_present_still_returns_profileable_colors():
    colors = skin_tone.analyze(StubClient({"skin_color": "#af8b72"}), "x.jpg")
    assert colors.skin == "#af8b72"
    assert colors.hair.startswith("#") and colors.eye.startswith("#") and colors.lip.startswith("#")


def test_missing_skin_raises_friendly_error():
    with pytest.raises(YouCamError, match="couldn't read a skin tone"):
        skin_tone.analyze(StubClient({"hair_color": "#000000"}), "x.jpg")
