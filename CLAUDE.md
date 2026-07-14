# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

DRAPE: an AI personal-color draping studio built on YouCam APIs for the YouCam API Skin AI & Apparel VTO Hackathon (deadline Aug 17 2026, submit by Aug 15). One selfie → a 3-round adaptive "draping session" that renders test-color garments on the user via generative try-on, scores the **measured pixels of each render** in CIELAB, and produces a 12-season verdict with an interactive palette, scored shop rack, garment checker, and shareable card.

## Commands

```bash
# backend (Python 3.10+; venv lives at backend/.venv)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests -q                 # full suite (offline, zero API units)
.venv/bin/python -m pytest tests/test_scoring.py -k warm   # single test
.venv/bin/python scripts/calibrate.py -v            # golden-set accuracy table (36 archetypes)
.venv/bin/python scripts/make_drapes.py             # regenerate drape assets (required after color changes)
.venv/bin/python scripts/make_personas.py           # synthetic demo selfies
.venv/bin/python scripts/make_catalog.py            # shop catalog + images

# CLI harness
YOUCAM_MOCK=1 .venv/bin/python cli.py analyze assets/personas/amber.jpg --mock
.venv/bin/python cli.py credit                      # live: balance + per-feature costs (free query)
.venv/bin/python cli.py gate <selfie.jpg>           # live go/no-go probes (~28 units)

# dev servers -- ports 8000/5173 are taken by other projects on this machine
backend/.venv/bin/uvicorn app:app --app-dir backend --port 8321   # from repo root
npm run dev --prefix frontend                        # vite on 5321, proxies to 8321

npm run build --prefix frontend                      # production build (FastAPI serves frontend/dist)
```

`YOUCAM_MOCK=1` runs the entire pipeline offline against a pixel-honest mock engine — develop and test there; live units cost real money (~45/session, balance visible at `/api/mode`). Config comes from `.env` at the repo root (see `.env.example`); the API key must never be committed, and neither may anything under `backend/assets/uploads|renders|cards|garments` or `backend/.sessions` (user faces and verdicts — already gitignored).

## Architecture

Pipeline (all orchestration in `backend/drape/agent/session.py`):

1. **Facial Color Tones Analyzer** → hex colors only (there is NO undertone field; temperature is derived in colorlab from Lab b*/chroma, with lip color as a weak vote and an eyebrow-lightness fallback when the hair reading is wild — the live API misreads black hair as blonde on cropped photos).
2. **Skin Analysis SD** (`redness`,`radiance` only; SD/HD concerns must never mix) → score semantics are HIGHER = healthier, so severity = 100 − score.
3. **Three decision rounds** (temperature → depth → sub-season), each rendering 2–3 probe drapes concurrently via **Clothes VTO cloth-v3** and deciding on the axis-specific score *component* (never totals — see `agent/decide.py`, shared with the renderless classifier `colorlab/classify.py` so tuning one tunes both).
4. **Harmony engine** (`colorlab/scoring.py`) scores measured render colors (extraction in `colorlab/extract.py`: hue/chroma from the dominant cluster, lightness from the 75th-percentile of garment pixels because fabric shading drags L down).

Tunable constants live at the top of `colorlab/scoring.py` and in `decide.py` (`SUBSEASON_AXES`, margins, weights). **Any change to them must be validated against the golden archetype set** — `tests/test_golden.py` enforces accuracy floors (temperature ≥95%, family ≥90%, exact ≥80%; currently 100/100/92). Probe drape pairs in `colorlab/seasons.py` must stay lightness-matched: a pair's L midpoint IS the implicit light/deep boundary (a mis-centered pair once silently moved the boundary to depth 0.31).

`backend/app.py` is the web layer: sessions run on worker threads, the frontend polls `/api/session/{sid}` (trace streams live), finished sessions persist to `backend/.sessions/` and restore on demand. The React SPA (`frontend/src`, four screens: Upload → Session → Verdict → Shop) resumes from the URL hash.

### YouCam API client invariants (`backend/drape/api/youcam_client.py`)

- Task failures return HTTP 200 with `task_status:"error"`; the `error` field may be a dict, a bare code string, or null (parse via `task_error()`).
- Two-stage upload: declaring a file does NOT upload it; the presigned PUT is mandatory.
- `file_id` is scoped per feature (enforced by `FileHandle`); cache keys use content digests, never `file_id` (fresh per upload).
- Unpolled successful tasks still bill; failed tasks bill then refund (net zero) — which is why the session retries face-too-small errors with tighter center crops for free (the API is the face detector). Cloth try-on always keeps the original frame (needs shoulders); skin features get the crops.
- `skin-tone-analysis` accepts jpg only.

### Unit-budget guards (do not weaken)

Demo personas always run on the mock engine even on a live server; live upload sessions check a reserve floor (`DRAPE_UNIT_RESERVE`) and a per-IP daily cap (`DRAPE_LIVE_SESSIONS_PER_IP`); every API response is disk-cached by (content digest, feature, params).
