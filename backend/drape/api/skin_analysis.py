"""AI Skin Analysis (SD): selfie -> redness + radiance scores.

We deliberately request only the two SD concerns DRAPE uses (cheapest call;
SD and HD concerns must never be mixed in one request). Score semantics per
docs: HIGHER raw_score = healthier skin. So "elevated redness" is a LOW
redness score -- downstream code uses severity = 100 - raw_score.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from drape.api.youcam_client import SKIN_ANALYSIS, YouCamClient, YouCamError

DST_ACTIONS = ["redness", "radiance"]


@dataclass
class SkinState:
    redness_score: float  # 1-100, higher = calmer skin
    radiance_score: float  # 1-100, higher = brighter skin

    @property
    def redness_severity(self) -> float:
        return 100.0 - self.redness_score

    @property
    def dullness(self) -> float:
        return 100.0 - self.radiance_score


def analyze(client: YouCamClient, selfie: str | Path) -> SkinState:
    handle = client.upload(SKIN_ANALYSIS, selfie)
    result = client.run_task(
        SKIN_ANALYSIS,
        {"dst_actions": DST_ACTIONS, "format": "json"},
        src=handle,
    )
    scores: dict[str, float] = {}
    for item in result.results.get("output", []):
        scores[item["type"]] = float(item.get("raw_score", item.get("ui_score", 0)))
    missing = [a for a in DST_ACTIONS if a not in scores]
    if missing:
        raise YouCamError(f"skin-analysis result missing concerns: {missing}", payload=result.payload)
    return SkinState(redness_score=scores["redness"], radiance_score=scores["radiance"])
