"""Calibration harness: run the classifier over the golden archetype set and
report accuracy at three grains (temperature / family / exact season).

Exact sub-season boundaries are fuzzy even between human colorists, so the
tiers matter more the coarser they are: temperature errors are disqualifying,
family errors are bad, sub-season disagreements are expected noise.

  python scripts/calibrate.py            # accuracy table
  python scripts/calibrate.py -v         # per-case rows including passes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drape.api.skin_tone import FacialColors  # noqa: E402
from drape.colorlab.classify import classify  # noqa: E402
from drape.colorlab.scoring import FaceProfile  # noqa: E402
from drape.colorlab.seasons import SEASONS  # noqa: E402

GOLDEN = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "golden_archetypes.json"

TEMP_OF_FAMILY = {"spring": "warm", "autumn": "warm", "summer": "cool", "winter": "cool"}


def load_cases() -> list[dict]:
    return json.loads(GOLDEN.read_text())["archetypes"]


def run_case(case: dict):
    colors = FacialColors(
        skin=case["skin"],
        hair=case["hair"],
        eye=case["eye"],
        eyebrow=case.get("eyebrow", case["hair"]),
        lip=case["lip"],
        hair_name="",
        eye_name="",
    )
    return classify(FaceProfile.from_colors(colors))


def evaluate(verbose: bool = False) -> dict:
    cases = load_cases()
    hits = {"temperature": 0, "family": 0, "exact": 0}
    rows = []
    for case in cases:
        result = run_case(case)
        want_family = SEASONS[case["season"]].family
        want_temp = TEMP_OF_FAMILY[want_family]
        temp_ok = result.temperature == want_temp or result.temperature == "neutral"
        family_ok = result.family == want_family
        exact_ok = result.season_key == case["season"]
        hits["temperature"] += temp_ok
        hits["family"] += family_ok
        hits["exact"] += exact_ok
        rows.append((case, result, temp_ok, family_ok, exact_ok))

    n = len(cases)
    summary = {k: v / n for k, v in hits.items()}

    for case, result, temp_ok, family_ok, exact_ok in rows:
        if verbose or not family_ok:
            mark = "OK " if exact_ok else ("fam" if family_ok else ("tmp" if temp_ok else "XXX"))
            print(
                f"[{mark}] want {case['season']:<14} got {result.season_key:<14} "
                f"(temp {result.temperature}, depth {result.depth}, margins {result.margins}) "
                f"-- {case['name']}"
            )
    print(f"\nn={n}  temperature {summary['temperature']:.0%}  "
          f"family {summary['family']:.0%}  exact {summary['exact']:.0%}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    evaluate(verbose=args.verbose)
