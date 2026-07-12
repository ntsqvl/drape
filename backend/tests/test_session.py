"""End-to-end pipeline tests in mock mode: persona selfie -> verdict."""

import pytest

from drape.agent.session import DrapingSession


@pytest.mark.parametrize(
    "persona,expected_temps",
    [
        ("amber", {"warm"}),           # golden tan + dark warm hair
        ("elsa", {"cool", "neutral"}),  # rosy light + ash hair
        ("sunny", {"warm", "neutral"}),  # golden light + warm blonde
    ],
)
def test_session_reaches_plausible_verdict(mock_client, persona_dir, persona, expected_temps):
    session = DrapingSession(client=mock_client, selfie=persona_dir / f"{persona}.jpg")
    verdict = session.run()

    assert verdict.temperature in expected_temps
    assert verdict.confidence in ("high", "moderate", "low")
    assert verdict.season_key
    assert len(verdict.palette) == 6
    # palette comes back ranked
    scores = [p["score"] for p in verdict.palette]
    assert scores == sorted(scores, reverse=True)
    # best should outscore worst -- that's the whole reveal
    assert verdict.best.score.score > verdict.worst.score.score
    # unit budget: the agent must stay within its render budget
    # (8 probes + possibly a neutral probe + possibly the top palette color)
    assert verdict.renders_used <= 10
    # the reveal always shows the #1 palette color on the user's body
    assert verdict.best.name == verdict.palette[0]["name"]
    assert verdict.trace


def test_session_is_deterministic(mock_client, persona_dir):
    v1 = DrapingSession(client=mock_client, selfie=persona_dir / "amber.jpg").run()
    v2 = DrapingSession(client=mock_client, selfie=persona_dir / "amber.jpg").run()
    assert v1.season_key == v2.season_key
    assert v1.confidence == v2.confidence


def test_cache_prevents_repeat_api_calls(mock_client, persona_dir, monkeypatch):
    DrapingSession(client=mock_client, selfie=persona_dir / "amber.jpg").run()

    # Second run: every task must be served from the disk cache.
    calls = []
    from drape.api import mock_engine

    original = mock_engine.run

    def counting_run(feature, params):
        calls.append(feature)
        return original(feature, params)

    monkeypatch.setattr(mock_engine, "run", counting_run)
    DrapingSession(client=mock_client, selfie=persona_dir / "amber.jpg").run()
    assert calls == []
