"""Round decision logic, shared by the live draping agent and the renderless
golden-set classifier.

Each round decides on its OWN axis component of the two probe scores, not the
total: a probe's total mixes temperature, depth and chroma, so comparing
totals lets (say) a warm bonus contaminate a depth decision. Component gaps
are scaled x100 so the shared MARGIN threshold reads in familiar 0-100 terms.
"""

from __future__ import annotations

from dataclasses import dataclass

from drape.colorlab.scoring import DrapeScore, FaceProfile

MARGIN = 10.0  # minimum component gap (x100) for a conclusive round
PROFILE_TEMP_TIEBREAK = 0.15  # |profile temperature| below this can't break a tie
PROFILE_DEPTH_SPLIT = 0.5
CLARITY_MUTED_WARM = 0.38  # warm + light + clarity below this = soft autumn zone

# Expected (depth, clarity) center per sub-season, from the 12-season model.
# Round 3's signature drapes barely separate neighboring seasons (their
# palettes overlap by design), so the profile's own axes carry half the vote.
SUBSEASON_AXES = {
    "light_spring": (0.18, 0.45), "true_spring": (0.38, 0.55), "bright_spring": (0.42, 0.62),
    "light_summer": (0.18, 0.35), "true_summer": (0.38, 0.38), "soft_summer": (0.40, 0.24),
    "soft_autumn": (0.42, 0.28), "true_autumn": (0.55, 0.42), "deep_autumn": (0.70, 0.35),
    "bright_winter": (0.50, 0.70), "true_winter": (0.62, 0.55), "deep_winter": (0.76, 0.45),
}
# Round-3 blend weights. Temperature is EXCLUDED on purpose: within a family
# every candidate shares the person's temperature, so a drape's temperature
# component only measures how extreme its hue is -- cobalt would beat
# shocking pink on any cool profile without saying anything about sub-season.
# Weights tuned on the golden archetype set (92% exact at these values; the
# drape components' ideal-value formulas compress toward mid-tones, which is
# why axis fit carries most of the sub-season vote). Caveat: the golden set
# shares axis definitions with the targets, so re-examine this split against
# real measured renders once live-API data exists.
SUB_W_DEPTH = 0.15
SUB_W_CHROMA = 0.05
SUB_W_AXES = 0.80


@dataclass(frozen=True)
class RoundDecision:
    choice: str
    margin: float  # component gap x100, always >= 0
    tiebreak: str | None  # None (probes decided) | "profile" | "neutral"


def decide_temperature(warm: DrapeScore, cool: DrapeScore, profile: FaceProfile) -> RoundDecision:
    gap = (warm.components["temperature"] - cool.components["temperature"]) * 100.0
    if abs(gap) >= MARGIN:
        return RoundDecision("warm" if gap > 0 else "cool", abs(gap), None)
    if abs(profile.temperature) >= PROFILE_TEMP_TIEBREAK:
        return RoundDecision("warm" if profile.temperature > 0 else "cool", abs(gap), "profile")
    return RoundDecision("neutral", abs(gap), "neutral")


def decide_depth(light: DrapeScore, deep: DrapeScore, profile: FaceProfile) -> RoundDecision:
    gap = (light.components["depth"] - deep.components["depth"]) * 100.0
    if abs(gap) >= MARGIN:
        return RoundDecision("light" if gap > 0 else "deep", abs(gap), None)
    return RoundDecision("light" if profile.depth < PROFILE_DEPTH_SPLIT else "deep", abs(gap), "profile")


def family_for(temperature: str, depth: str, profile: FaceProfile) -> str:
    family = {
        ("warm", "light"): "spring",
        ("warm", "deep"): "autumn",
        ("cool", "light"): "summer",
        ("cool", "deep"): "winter",
        ("neutral", "light"): "summer" if profile.temperature <= 0 else "spring",
        ("neutral", "deep"): "autumn" if profile.temperature > 0 else "winter",
    }[(temperature, depth)]
    # Depth alone can't split spring from autumn for mid-depth warm coloring;
    # the discriminator there is clarity: muted golden coloring is soft
    # autumn, not a dusty spring.
    if family == "spring" and profile.clarity < CLARITY_MUTED_WARM:
        family = "autumn"
    return family


def rank_subseasons(drape_scores: dict[str, DrapeScore], profile: FaceProfile) -> list[tuple[str, float]]:
    """Rank a family's candidate seasons on a 0-100 sub-season score:
    the drape's depth + chroma components blended with the profile's fit to
    the sub-season's expected axis centers."""
    ranked = []
    for key, score in drape_scores.items():
        depth_t, clarity_t = SUBSEASON_AXES[key]
        fit = 1.0 - (abs(profile.depth - depth_t) + abs(profile.clarity - clarity_t)) / 2.0
        blended = 100.0 * (
            SUB_W_DEPTH * score.components["depth"]
            + SUB_W_CHROMA * score.components["chroma"]
            + SUB_W_AXES * fit
        )
        ranked.append((key, round(blended, 1)))
    ranked.sort(key=lambda kv: kv[1], reverse=True)
    return ranked
