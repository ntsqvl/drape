"""The adaptive draping session: a deterministic decision-tree agent.

Mirrors how a human colorist runs a draping appointment -- probe, observe,
narrow -- with the consultant's eye replaced by the harmony engine scoring
the *measured* color of each VTO render. Three rounds:

  1. temperature  warm gold vs cool orchid
  2. depth        light vs deep probe within the temperature branch
  3. sub-season   one signature drape per season in the chosen family

Round decisions live in decide.py and read the axis-specific component of
each probe's score (see that module for why). Renders within a round are
independent, so each round submits its drapes concurrently: ~8 renders in 4
waves instead of 8 sequential waits. An inconclusive round falls back to the
face profile's own axis; if that is also ambiguous the session goes down the
neutral path and the verdict is capped at low confidence.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from drape import config
from drape.agent import decide
from drape.api import cloth_vto, skin_analysis, skin_tone
from drape.api.youcam_client import CLOTH, FileHandle, YouCamClient, YouCamError

# Photo-framing errors that a tighter center crop can fix. Failed tasks cost
# zero units, so the API itself serves as the face detector: try the full
# frame, then retry cropped. Cloth try-on always keeps the ORIGINAL frame --
# it needs the shoulders the skin features want cropped away.
FACE_SMALL_CODES = {
    "error_src_face_too_small",
    "error_face_position_too_small",
    "error_face_position_invalid",
}
FACE_CROP_FRACTIONS = (0.70, 0.55)
from drape.colorlab import extract, seasons
from drape.colorlab.lab import hex_to_lab
from drape.colorlab.scoring import DrapeScore, FaceProfile, score_drape

SIGNATURE = seasons.SIGNATURE  # round-3 signature drapes live with the season data


@dataclass
class DrapeResult:
    drape_id: str
    requested_hex: str
    name: str
    measured_hex: str
    render_path: str
    score: DrapeScore


@dataclass
class Verdict:
    season_key: str
    season_name: str
    tagline: str
    confidence: str  # high | moderate | low
    confidence_note: str
    temperature: str  # warm | cool | neutral
    palette: list[dict]  # ranked: {hex, name, score, reasons}
    best: DrapeResult
    worst: DrapeResult
    profile_axes: dict
    facial_colors: dict
    skin_state: dict
    margins: dict
    renders_used: int
    trace: list[dict]


@dataclass
class DrapingSession:
    client: YouCamClient
    selfie: Path
    trace: list[dict] = field(default_factory=list)
    renders_used: int = 0
    _cloth_handle: FileHandle | None = None

    # ------------------------------------------------------------- helpers

    def log(self, round_: str, message: str, **detail) -> None:
        event = {"round": round_, "message": message, **detail}
        self.trace.append(event)

    def _face_variants(self) -> list[Path]:
        """Original selfie plus progressively tighter center crops."""
        variants = [self.selfie]
        img = Image.open(self.selfie)
        w, h = img.size
        for frac in FACE_CROP_FRACTIONS:
            cw = int(w * frac)
            if cw < 500:  # would violate the SD short-side floor
                continue
            left = (w - cw) // 2
            top = int(h * 0.02)  # faces sit upper-center in selfies
            bottom = min(h, top + int(cw * 1.25))
            path = self.selfie.with_name(f"{self.selfie.stem}_face{int(frac * 100)}.jpg")
            img.crop((left, top, left + cw, bottom)).convert("RGB").save(path, quality=92)
            variants.append(path)
        return variants

    def _analyze_with_face_retry(self, analyze, variants: list[Path], start: int):
        """Run `analyze` against face variants from index `start`; returns
        (result, index of the variant that worked)."""
        last: YouCamError | None = None
        for i in range(start, len(variants)):
            try:
                return analyze(variants[i]), i
            except YouCamError as exc:
                if exc.error_code not in FACE_SMALL_CODES or i == len(variants) - 1:
                    raise
                last = exc
                self.log(
                    "analyze",
                    f"face reads too small at this framing ({exc.error_code}); retrying with a tighter crop",
                )
        raise last or YouCamError("face analysis failed")

    def _drape_path(self, drape_id: str) -> Path:
        path = config.DRAPES_DIR / f"{drape_id}.jpg"
        if not path.exists():
            raise FileNotFoundError(
                f"drape asset missing: {path}. Run scripts/make_drapes.py first."
            )
        return path

    def _render_and_score(
        self,
        drape: tuple[str, str, str],
        profile: FaceProfile,
        skin_state: skin_analysis.SkinState,
    ) -> DrapeResult:
        drape_id, hex_, name = drape
        render = cloth_vto.try_on(self.client, self._cloth_handle, self._drape_path(drape_id))
        measured_hex, measured_lab = extract.garment_color(render, skin=profile.skin)
        score = score_drape(profile, measured_lab, skin_state)
        self.log(
            "render",
            f"draped {name}: scored {score.score}",
            drape_id=drape_id,
            name=name,
            requested=hex_,
            measured=measured_hex,
            score=score.score,
            render=str(render),
        )
        return DrapeResult(drape_id, hex_, name, measured_hex, str(render), score)

    def _render_batch(
        self,
        drapes: list[tuple[str, str, str]],
        profile: FaceProfile,
        skin_state: skin_analysis.SkinState,
    ) -> list[DrapeResult]:
        """Render a round's drapes concurrently; results in input order.

        The renders inside a round are independent -- only the choice of the
        NEXT round depends on their scores -- so waiting for them serially
        wastes wall-clock time on the live API.
        """
        if self._cloth_handle is None:  # upload the selfie once, before fan-out
            self._cloth_handle = self.client.upload(CLOTH, self.selfie)
        self.renders_used += len(drapes)  # counted here, not in worker threads
        if len(drapes) == 1:
            return [self._render_and_score(drapes[0], profile, skin_state)]
        with ThreadPoolExecutor(max_workers=len(drapes)) as pool:
            return list(pool.map(lambda d: self._render_and_score(d, profile, skin_state), drapes))

    # ---------------------------------------------------------------- run

    def run(self) -> Verdict:
        self.log("analyze", "reading facial colors (AI Facial Color Tones Analyzer)")
        variants = self._face_variants()
        colors, variant_idx = self._analyze_with_face_retry(
            lambda p: skin_tone.analyze(self.client, p), variants, 0
        )
        profile = FaceProfile.from_colors(colors)
        if FaceProfile.hair_reading_suspect(colors):
            self.log(
                "analyze",
                f"hair read as {colors.hair} but eyebrows are {colors.eyebrow}; "
                "trusting eyebrow depth for the hair signal",
            )
        self.log(
            "analyze",
            f"skin {colors.skin}, hair {colors.hair} ({colors.hair_name}), eyes {colors.eye}",
            temperature=round(profile.temperature, 2),
            depth=round(profile.depth, 2),
            clarity=round(profile.clarity, 2),
        )

        self.log("analyze", "reading today's skin state (AI Skin Analysis, SD)")
        state, _ = self._analyze_with_face_retry(
            lambda p: skin_analysis.analyze(self.client, p), variants, variant_idx
        )
        self.log(
            "analyze",
            f"redness severity {state.redness_severity:.0f}/100, dullness {state.dullness:.0f}/100",
        )

        # ---------------- round 1: temperature --------------------------
        warm, cool = self._render_batch([seasons.PROBE_WARM, seasons.PROBE_COOL], profile, state)
        d1 = decide.decide_temperature(warm.score, cool.score, profile)
        temperature = d1.choice
        neutral_path = d1.tiebreak == "neutral"
        if d1.tiebreak is None:
            self.log("round1", f"{temperature} drape won on the temperature axis by {d1.margin:.0f} -> you lean {temperature}")
        elif d1.tiebreak == "profile":
            self.log("round1", f"probes nearly tied ({d1.margin:.0f} apart); skin hue itself breaks the tie -> {temperature}")
        else:
            neutral = self._render_batch([seasons.PROBE_NEUTRAL], profile, state)[0]
            self.log(
                "round1",
                f"probes and skin hue both ambiguous; neutral drape scored {neutral.score.score} -> neutral path",
            )

        # ---------------- round 2: depth ---------------------------------
        if temperature == "warm":
            pair = [seasons.PROBE_WARM_LIGHT, seasons.PROBE_WARM_DEEP]
        else:  # cool and neutral both probe the cool depth pair; depth axis is temperature-agnostic
            pair = [seasons.PROBE_COOL_LIGHT, seasons.PROBE_COOL_DEEP]
        light_r, deep_r = self._render_batch(pair, profile, state)
        d2 = decide.decide_depth(light_r.score, deep_r.score, profile)
        depth = d2.choice
        if d2.tiebreak is None:
            self.log("round2", f"{depth} drape won on the depth axis by {d2.margin:.0f}")
        else:
            self.log("round2", f"depth probes tied ({d2.margin:.0f} apart); measured depth axis says {depth}")

        family = decide.family_for(temperature, depth, profile)
        self.log("round2", f"family: {family}")

        # ---------------- round 3: sub-season ----------------------------
        candidates = []
        for key in seasons.FAMILIES[family]:
            season = seasons.SEASONS[key]
            hex_, name = season.palette[SIGNATURE[key]]
            candidates.append((key, (f"{key}_{name.replace(' ', '_')}", hex_, name)))
        batch = self._render_batch([drape for _, drape in candidates], profile, state)
        results = {key: res for (key, _), res in zip(candidates, batch)}
        ranked = decide.rank_subseasons(
            {key: res.score for key, res in results.items()}, profile
        )
        season_key = ranked[0][0]
        round3_margin = ranked[0][1] - ranked[1][1]
        self.log("round3", f"{seasons.SEASONS[season_key].name} leads the family by {round3_margin:.0f}")

        season = seasons.SEASONS[season_key]

        # ---------------- verdict ----------------------------------------
        palette_scored = []
        for hex_, name in season.palette:
            s = score_drape(profile, hex_to_lab(hex_), state)
            palette_scored.append({"hex": hex_, "name": name, "score": s.score, "reasons": s.reasons})
        palette_scored.sort(key=lambda p: p["score"], reverse=True)

        # The reveal must show the season's #1 palette color on the user --
        # not merely the best drape the session happened to render. Reuse the
        # round-3 render when they coincide; otherwise it's one more render.
        best = results[season_key]
        top = palette_scored[0]
        if top["name"] != best.name:
            best = self._render_batch(
                [(f"{season_key}_{top['name'].replace(' ', '_')}", top["hex"], top["name"])],
                profile,
                state,
            )[0]
        whex, wname, wwhy = season.worst
        worst = self._render_batch(
            [(f"{season_key}_worst_{wname.replace(' ', '_')}", whex, wname)], profile, state
        )[0]
        self.log("reveal", f"best: {best.name} ({best.score.score}) vs worst: {wname} ({worst.score.score}) -- {wwhy}")

        # Round 3 separates *neighboring* seasons whose palettes genuinely
        # overlap, so its margins run structurally smaller; weight it double
        # before applying the shared thresholds.
        margins = {"round1": round(d1.margin, 1), "round2": round(d2.margin, 1), "round3": round(round3_margin, 1)}
        min_margin = min(d1.margin, d2.margin, 2.0 * round3_margin)
        confidence = (
            "high" if min_margin >= 2 * decide.MARGIN else "moderate" if min_margin >= decide.MARGIN else "low"
        )
        if neutral_path:
            confidence = "low"
        weakest = min(margins, key=lambda k: margins[k] * (2.0 if k == "round3" else 1.0))
        confidence_note = (
            "temperature was ambiguous; verdict follows the neutral path"
            if neutral_path
            else f"narrowest gap was {ROUND_NAMES[weakest]} ({margins[weakest]:.0f} pts)"
        )

        return Verdict(
            season_key=season_key,
            season_name=season.name + (" (neutral lean)" if neutral_path else ""),
            tagline=season.tagline,
            confidence=confidence,
            confidence_note=confidence_note,
            temperature=temperature,
            palette=palette_scored,
            best=best,
            worst=worst,
            profile_axes={
                "temperature": round(profile.temperature, 3),
                "depth": round(profile.depth, 3),
                "clarity": round(profile.clarity, 3),
            },
            facial_colors=vars(colors),
            skin_state={
                "redness_severity": round(state.redness_severity, 1),
                "dullness": round(state.dullness, 1),
            },
            margins=margins,
            renders_used=self.renders_used,
            trace=self.trace,
        )


ROUND_NAMES = {"round1": "the temperature round", "round2": "the depth round", "round3": "the season round"}
