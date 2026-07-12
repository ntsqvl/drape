from drape.agent import decide
from drape.api.skin_tone import FacialColors
from drape.colorlab.scoring import DrapeScore, FaceProfile

WARM_DEEP = FaceProfile.from_colors(FacialColors(
    skin="#8d5a3b", hair="#2e1d10", eye="#5e3e28", eyebrow="#2e1d10", lip="#c9765a",
    hair_name="", eye_name="",
))
NEUTRAL_FACE = FaceProfile.from_colors(FacialColors(
    # skin hue right at the warm/cool midpoint, neutral lip (temp = +0.03)
    skin="#dbb19e", hair="#6f6154", eye="#7f8f87", eyebrow="#6f6154", lip="#b87370",
    hair_name="", eye_name="",
))


def _score(**components) -> DrapeScore:
    base = {"temperature": 0.5, "depth": 0.5, "chroma": 0.5}
    base.update(components)
    return DrapeScore(score=50.0, components=base, reasons=[])


def test_temperature_decides_on_component_not_total():
    # warm probe wins on the temperature axis even though its (irrelevant
    # here) total would lose -- totals are never consulted
    warm = _score(temperature=0.8, depth=0.1)
    cool = _score(temperature=0.4, depth=0.9)
    d = decide.decide_temperature(warm, cool, WARM_DEEP)
    assert d.choice == "warm"
    assert d.tiebreak is None
    assert d.margin == 40.0


def test_temperature_tie_falls_back_to_profile():
    warm = _score(temperature=0.52)
    cool = _score(temperature=0.48)
    d = decide.decide_temperature(warm, cool, WARM_DEEP)
    assert d.choice == "warm"
    assert d.tiebreak == "profile"


def test_double_ambiguity_goes_neutral():
    warm = _score(temperature=0.51)
    cool = _score(temperature=0.49)
    d = decide.decide_temperature(warm, cool, NEUTRAL_FACE)
    assert d.choice == "neutral"
    assert d.tiebreak == "neutral"


def test_depth_decides_on_depth_component():
    light = _score(depth=0.9, temperature=0.1)
    deep = _score(depth=0.3, temperature=0.9)
    d = decide.decide_depth(light, deep, WARM_DEEP)
    assert d.choice == "light"
    assert d.tiebreak is None


def test_muted_warm_light_routes_to_autumn():
    # soft-muted warm coloring is soft autumn, not a dusty spring
    assert decide.family_for("warm", "light", NEUTRAL_FACE) == "autumn"
    assert NEUTRAL_FACE.clarity < decide.CLARITY_MUTED_WARM
    assert decide.family_for("warm", "light", WARM_DEEP) in ("spring", "autumn")


def test_rank_subseasons_prefers_axis_fit():
    scores = {k: _score() for k in ("soft_autumn", "true_autumn", "deep_autumn")}
    ranked = decide.rank_subseasons(scores, WARM_DEEP)  # deep profile (0.72)
    assert ranked[0][0] == "deep_autumn"
