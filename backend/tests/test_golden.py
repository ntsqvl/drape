"""Golden archetype regression: the classifier must hold its accuracy on the
36 labeled season archetypes. Thresholds sit slightly below current measured
performance (100% / 100% / 92%) so legitimate re-tuning has headroom, while a
real regression -- especially in temperature, the disqualifying error -- fails
loudly. Run scripts/calibrate.py -v for the per-case table."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from calibrate import evaluate, load_cases, run_case  # noqa: E402


def test_golden_accuracy_thresholds(capsys):
    summary = evaluate()
    capsys.readouterr()  # swallow the harness's table output
    assert summary["temperature"] >= 0.95, "temperature errors are disqualifying"
    assert summary["family"] >= 0.90
    assert summary["exact"] >= 0.80


def test_every_season_is_reachable():
    got = {run_case(case).season_key for case in load_cases()}
    assert len(got) >= 10, f"classifier collapsed to few seasons: {sorted(got)}"
