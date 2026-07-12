from drape.api.skin_analysis import SkinState
from drape.api.skin_tone import FacialColors
from drape.colorlab.lab import hex_to_lab
from drape.colorlab.scoring import FaceProfile, garment_warmth, score_drape

WARM_DEEP = FacialColors(
    skin="#8d5a3b", hair="#2e1d10", eye="#5e3e28", eyebrow="#2e1d10", lip="#a2543f",
    hair_name="Brown", eye_name="Brown",
)
COOL_LIGHT = FacialColors(
    skin="#ecc3bd", hair="#9c8e7d", eye="#5a698c", eyebrow="#7d7264", lip="#c06a7a",
    hair_name="Blonde", eye_name="Blue",
)

CALM_SKIN = SkinState(redness_score=90, radiance_score=80)
RED_SKIN = SkinState(redness_score=35, radiance_score=80)


def test_temperature_axes_separate_personas():
    warm = FaceProfile.from_colors(WARM_DEEP)
    cool = FaceProfile.from_colors(COOL_LIGHT)
    assert warm.temperature > 0.2
    assert cool.temperature < warm.temperature
    assert warm.depth > cool.depth


def test_warm_profile_prefers_warm_drape():
    profile = FaceProfile.from_colors(WARM_DEEP)
    gold = score_drape(profile, hex_to_lab("#d8a13b"), CALM_SKIN)
    orchid = score_drape(profile, hex_to_lab("#b45fb2"), CALM_SKIN)
    assert gold.score > orchid.score


def test_cool_profile_prefers_cool_drape():
    profile = FaceProfile.from_colors(COOL_LIGHT)
    powder = score_drape(profile, hex_to_lab("#9fc2e0"), CALM_SKIN)
    rust = score_drape(profile, hex_to_lab("#9c4722"), CALM_SKIN)
    assert powder.score > rust.score


def test_redness_demotes_saturated_reds_only():
    profile = FaceProfile.from_colors(COOL_LIGHT)
    red = hex_to_lab("#e8503a")  # saturated red-orange, inside the red band
    blue = hex_to_lab("#6c8ebf")
    calm_red = score_drape(profile, red, CALM_SKIN)
    flared_red = score_drape(profile, red, RED_SKIN)
    calm_blue = score_drape(profile, blue, CALM_SKIN)
    flared_blue = score_drape(profile, blue, RED_SKIN)
    assert flared_red.score < calm_red.score  # redness penalizes red garments
    assert abs(flared_blue.score - calm_blue.score) < 1  # but not blue ones
    assert any("redness" in r for r in flared_red.reasons)


def test_garment_warmth_neutral_damping():
    assert garment_warmth(hex_to_lab("#d8a13b")) > 0.5  # gold is warm
    assert garment_warmth(hex_to_lab("#0057b8")) < -0.5  # royal blue is cool
    assert abs(garment_warmth(hex_to_lab("#808085"))) < 0.25  # gray is neutral


def test_reasons_are_always_present():
    profile = FaceProfile.from_colors(WARM_DEEP)
    result = score_drape(profile, hex_to_lab("#b5651d"), CALM_SKIN)
    assert result.reasons
    assert 0 <= result.score <= 100
