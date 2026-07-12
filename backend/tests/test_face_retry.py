from pathlib import Path

import pytest
from PIL import Image

from drape.agent.session import DrapingSession
from drape.api.skin_tone import FacialColors
from drape.api.youcam_client import YouCamClient, YouCamError
from drape.colorlab.scoring import FaceProfile


@pytest.fixture()
def session(tmp_path):
    selfie = tmp_path / "selfie.jpg"
    Image.new("RGB", (2000, 2000), (200, 170, 150)).save(selfie)
    return DrapingSession(client=YouCamClient(mock=True, cache_dir=tmp_path), selfie=selfie)


def test_face_variants_are_progressively_tighter(session):
    variants = session._face_variants()
    assert len(variants) == 3
    widths = [Image.open(v).size[0] for v in variants]
    assert widths == sorted(widths, reverse=True)
    assert all(Path(v).exists() for v in variants)


def test_retry_advances_on_face_small_error(session):
    variants = session._face_variants()
    calls = []

    def analyze(path):
        calls.append(path)
        if len(calls) < 3:
            raise YouCamError("too small", error_code="error_face_position_too_small")
        return "ok"

    result, idx = session._analyze_with_face_retry(analyze, variants, 0)
    assert result == "ok"
    assert idx == 2
    assert any("tighter crop" in e["message"] for e in session.trace)


def test_retry_reraises_unrelated_errors(session):
    variants = session._face_variants()

    def analyze(path):
        raise YouCamError("dark", error_code="error_lighting_dark")

    with pytest.raises(YouCamError, match="dark"):
        session._analyze_with_face_retry(analyze, variants, 0)


def test_hair_misread_falls_back_to_eyebrow():
    # observed live: black hair returned as pale blonde on a cropped photo
    colors = FacialColors(
        skin="#af8b72", hair="#FAF0BE", eye="#271b1e", eyebrow="#3e3834",
        lip="#dc7e81", hair_name="Blonde", eye_name="Brown",
    )
    assert FaceProfile.hair_reading_suspect(colors)
    profile = FaceProfile.from_colors(colors)
    assert profile.hair.L < 40  # eyebrow depth, not the bogus blonde
    assert profile.depth > 0.5  # dark-haired profile reads deep, as it should
