"""Renderless season classification: the agent's decision tree over direct
hex scoring, no VTO calls.

Used by the golden-set calibration harness (and available as a zero-unit
"instant estimate"). Shares decide.py with the live agent, so tuning the
thresholds tunes both paths identically. The live agent should agree with
this except where measured render colors drift from requested ones.
"""

from __future__ import annotations

from dataclasses import dataclass

from drape.agent import decide
from drape.api.skin_analysis import SkinState
from drape.colorlab import seasons
from drape.colorlab.lab import hex_to_lab
from drape.colorlab.scoring import FaceProfile, score_drape
from drape.colorlab.seasons import SIGNATURE


@dataclass(frozen=True)
class Classification:
    season_key: str
    family: str
    temperature: str
    depth: str
    neutral_path: bool
    margins: dict


def _probe(profile: FaceProfile, drape: tuple[str, str, str], state: SkinState | None):
    return score_drape(profile, hex_to_lab(drape[1]), state)


def classify(profile: FaceProfile, state: SkinState | None = None) -> Classification:
    warm = _probe(profile, seasons.PROBE_WARM, state)
    cool = _probe(profile, seasons.PROBE_COOL, state)
    d1 = decide.decide_temperature(warm, cool, profile)

    pair = (
        (seasons.PROBE_WARM_LIGHT, seasons.PROBE_WARM_DEEP)
        if d1.choice == "warm"
        else (seasons.PROBE_COOL_LIGHT, seasons.PROBE_COOL_DEEP)
    )
    d2 = decide.decide_depth(_probe(profile, pair[0], state), _probe(profile, pair[1], state), profile)

    family = decide.family_for(d1.choice, d2.choice, profile)

    drape_scores = {}
    for key in seasons.FAMILIES[family]:
        season = seasons.SEASONS[key]
        hex_, _name = season.palette[SIGNATURE[key]]
        drape_scores[key] = score_drape(profile, hex_to_lab(hex_), state)
    scored = decide.rank_subseasons(drape_scores, profile)

    return Classification(
        season_key=scored[0][0],
        family=family,
        temperature=d1.choice,
        depth=d2.choice,
        neutral_path=d1.tiebreak == "neutral",
        margins={
            "round1": round(d1.margin, 1),
            "round2": round(d2.margin, 1),
            "round3": round(scored[0][1] - scored[1][1], 1),
        },
    )
