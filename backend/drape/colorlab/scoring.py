"""The harmony engine: score a garment color against a face profile.

This is a heuristic implementation of the 12-season draping method -- a
formalization of what human colorists judge by eye -- NOT a clinically
validated diagnostic. Constants below are tuned on the persona fixtures and
are deliberately exposed at module level for tuning.

Axis derivation (all from measured Lab values; the API provides no undertone):
  temperature  skin hue angle. Warm skin reads yellow-golden (higher hue
               angle in the skin cluster, ~50-75deg); cool skin reads
               pink-rosy (~20-45deg).
  depth        lightness of skin and hair combined.
  clarity      feature contrast: eye/hair chroma plus skin-vs-hair
               lightness spread.

Score semantics from AI Skin Analysis: higher raw_score = healthier, so
redness severity = 100 - redness_score (inverted upstream in SkinState).
"""

from __future__ import annotations

from dataclasses import dataclass

from drape.api.skin_analysis import SkinState
from drape.api.skin_tone import FacialColors
from drape.colorlab.lab import LabColor, hex_to_lab

# --- tunable constants -----------------------------------------------------
WARM_SKIN_HUE = 62.0  # skin hue angle at/above which skin reads fully warm
COOL_SKIN_HUE = 40.0  # at/below which skin reads fully cool
NEUTRAL_CHROMA = 18.0  # garments below this chroma are near-neutral
RED_BAND = (5.0, 55.0)  # garment hues that can amplify facial redness
LIP_NEUTRAL_BC = 0.40  # lips are always reddish; b*/C above this reads warm
LIP_WEIGHT = 0.20  # lip evidence share of the temperature axis
# The tone analyzer sometimes misreads hair color badly (observed live: black
# hair returned as pale blonde #FAF0BE on a cropped photo). Eyebrows track
# natural hair depth, so when hair and eyebrow lightness disagree by more
# than this, the eyebrow reading substitutes for hair.
HAIR_EYEBROW_MAX_DL = 45.0

W_TEMPERATURE = 0.40
W_DEPTH = 0.25
W_CHROMA = 0.20
W_REDNESS = 0.10
W_DULLNESS = 0.05


@dataclass(frozen=True)
class FaceProfile:
    skin: LabColor
    hair: LabColor
    eye: LabColor
    eyebrow: LabColor
    lip: LabColor

    @classmethod
    def from_colors(cls, colors: FacialColors) -> "FaceProfile":
        hair = hex_to_lab(colors.hair)
        eyebrow = hex_to_lab(colors.eyebrow)
        if cls.hair_reading_suspect(colors):
            hair = eyebrow  # trust the eyebrow's depth over a wild hair read
        return cls(
            skin=hex_to_lab(colors.skin),
            hair=hair,
            eye=hex_to_lab(colors.eye),
            eyebrow=eyebrow,
            lip=hex_to_lab(colors.lip),
        )

    @staticmethod
    def hair_reading_suspect(colors: FacialColors) -> bool:
        return abs(hex_to_lab(colors.hair).L - hex_to_lab(colors.eyebrow).L) > HAIR_EYEBROW_MAX_DL

    @property
    def temperature(self) -> float:
        """-1 (fully cool) .. +1 (fully warm).

        Primary evidence is skin hue angle; lip color contributes a small
        secondary vote. Lips are reddish on everyone, so the lip signal is
        the b*/chroma share re-centered at LIP_NEUTRAL_BC: a blue-pink lip
        pulls cool, a coral lip pulls warm.
        """
        h = self.skin.hue_deg
        mid = (WARM_SKIN_HUE + COOL_SKIN_HUE) / 2
        half = (WARM_SKIN_HUE - COOL_SKIN_HUE) / 2
        skin_t = max(-1.0, min(1.0, (h - mid) / half))
        lip_bc = self.lip.b / max(self.lip.chroma, 1e-6)
        lip_t = max(-1.0, min(1.0, (lip_bc - LIP_NEUTRAL_BC) / LIP_NEUTRAL_BC))
        return max(-1.0, min(1.0, (1.0 - LIP_WEIGHT) * skin_t + LIP_WEIGHT * lip_t))

    @property
    def depth(self) -> float:
        """0 (very light coloring) .. 1 (very deep)."""
        blend = 0.45 * self.skin.L + 0.55 * self.hair.L
        return max(0.0, min(1.0, 1.0 - blend / 95.0))

    @property
    def clarity(self) -> float:
        """0 (muted, low contrast) .. 1 (clear, high contrast)."""
        contrast = abs(self.skin.L - self.hair.L) / 90.0
        feature_chroma = max(self.eye.chroma, self.hair.chroma) / 60.0
        return max(0.0, min(1.0, 0.6 * contrast + 0.4 * feature_chroma))


@dataclass
class DrapeScore:
    score: float  # 0-100
    components: dict[str, float]
    reasons: list[str]


def garment_warmth(garment: LabColor) -> float:
    """-1 (pure cool hue) .. +1 (pure warm hue); damped toward 0 for neutrals.

    Warmth is the yellow-vs-blue share of the color: b*/chroma. This matches
    colorist intuition better than hue-angle distance -- magenta/fuchsia sits
    near red in Lab hue but is COOL in draping terms because of its blue
    content, which the negative b* captures directly.
    """
    raw = garment.b / max(garment.chroma, 1e-6)
    damp = min(1.0, garment.chroma / NEUTRAL_CHROMA)
    return raw * damp


def score_drape(profile: FaceProfile, garment: LabColor, skin_state: SkinState | None = None) -> DrapeScore:
    reasons: list[str] = []

    # -- temperature alignment: warm garment on warm profile is good, etc.
    t_align = garment_warmth(garment) * profile.temperature  # [-1, 1]
    t_score = (t_align + 1.0) / 2.0
    if t_align > 0.25:
        side = "warm" if profile.temperature > 0 else "cool"
        reasons.append(f"matches your {side} undertone")
    elif t_align < -0.25:
        side = "warm" if garment_warmth(garment) > 0 else "cool"
        reasons.append(f"this {side} tone fights your undertone")

    # -- depth: light coloring wants lighter garments, deep wants darker.
    ideal_l = 72.0 - 42.0 * profile.depth
    d_score = max(0.0, 1.0 - abs(garment.L - ideal_l) / 50.0)
    if d_score > 0.75:
        reasons.append("sits at your natural depth")
    elif garment.L > ideal_l + 25:
        reasons.append("may read pale against your contrast level")
    elif garment.L < ideal_l - 25:
        reasons.append("heavier than your natural depth")

    # -- chroma: clear coloring carries saturation; muted coloring prefers dusty.
    ideal_c = 24.0 + 42.0 * profile.clarity
    c_score = max(0.0, 1.0 - abs(garment.chroma - ideal_c) / 55.0)
    if c_score > 0.75 and garment.chroma > 40:
        reasons.append("bold enough to keep up with your contrast")
    elif garment.chroma > ideal_c + 25:
        reasons.append("more saturated than your coloring carries")

    # -- skin-state modifiers (today's skin, from AI Skin Analysis) ----------
    red_penalty = 0.0
    dull_penalty = 0.0
    if skin_state is not None:
        in_red_band = RED_BAND[0] <= garment.hue_deg <= RED_BAND[1] and garment.chroma > 32
        if in_red_band:
            red_penalty = skin_state.redness_severity / 100.0
            if red_penalty > 0.3:
                reasons.append("saturated red risks amplifying today's redness")
        if garment.chroma < 20:
            dull_penalty = (skin_state.dullness / 100.0) * (20.0 - garment.chroma) / 20.0
            if dull_penalty > 0.3:
                reasons.append("this muted shade may flatten low-radiance skin")

    raw = (
        W_TEMPERATURE * t_score
        + W_DEPTH * d_score
        + W_CHROMA * c_score
        - W_REDNESS * red_penalty
        - W_DULLNESS * dull_penalty
    ) / (W_TEMPERATURE + W_DEPTH + W_CHROMA)
    score = max(0.0, min(100.0, raw * 100.0))

    if not reasons:
        reasons.append("a workable, if unremarkable, match")
    return DrapeScore(
        score=round(score, 1),
        components={
            "temperature": round(t_score, 3),
            "depth": round(d_score, 3),
            "chroma": round(c_score, 3),
            "redness_penalty": round(red_penalty, 3),
            "dullness_penalty": round(dull_penalty, 3),
        },
        reasons=reasons,
    )
