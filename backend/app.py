"""DRAPE web backend: draping sessions over HTTP.

  POST /api/session            selfie upload or {persona} -> session_id
  GET  /api/session/{sid}      status + live trace + verdict when done
  GET  /api/catalog/{sid}      demo catalog scored against the verdict
  GET  /api/personas           demo-mode personas
  /assets/*                    drapes, renders, personas, catalog images

Sessions run on a worker thread; the frontend polls. In-memory session store
is deliberate: single-process demo app, no persistence requirements.
"""

from __future__ import annotations

import io
import json
import os
import threading
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

from drape import config
from drape.agent.session import DrapingSession
from drape.api import cloth_vto
from drape.api.skin_analysis import SkinState
from drape.api.skin_tone import FacialColors
from drape.api.youcam_client import YouCamClient, YouCamError
from drape.colorlab import extract
from drape.colorlab.lab import hex_to_lab
from drape.colorlab.scoring import FaceProfile, score_drape

app = FastAPI(title="DRAPE")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5321", "http://127.0.0.1:5321"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: dict[str, dict] = {}
UPLOADS_DIR = config.ASSETS_DIR / "uploads"
SESSIONS_DIR = config.BACKEND_ROOT / ".sessions"
CATALOG = json.loads((config.BACKEND_ROOT / "drape" / "catalog" / "catalog.json").read_text())

# Budget guard: a live session costs ~45 units (skin tone 20 + SD skin
# analysis 9 + ~8 cloth-v3 renders x 2, measured Jul 2026). Refuse to start
# one that would dip below the reserve. Cache hits bypass the API and are
# not affected.
SESSION_COST_EST = 45.0
UNIT_RESERVE = float(os.environ.get("DRAPE_UNIT_RESERVE", "150"))
_units_cache: dict = {"value": None, "at": 0.0}


def _remaining_units(client: YouCamClient | None = None) -> float | None:
    import time as _time

    if config.MOCK:
        return None
    if _time.monotonic() - _units_cache["at"] < 60 and _units_cache["value"] is not None:
        return _units_cache["value"]
    try:
        units = (client or YouCamClient()).remaining_units()
    except Exception:
        return _units_cache["value"]
    _units_cache.update(value=units, at=_time.monotonic())
    return units


def _persist(sid: str) -> None:
    """Finished sessions survive a backend restart (renders are on disk too)."""
    entry = SESSIONS[sid]
    if entry["status"] in ("done", "error"):
        SESSIONS_DIR.mkdir(exist_ok=True)
        (SESSIONS_DIR / f"{sid}.json").write_text(json.dumps(entry, default=str))


def _restore(sid: str) -> dict | None:
    path = SESSIONS_DIR / f"{sid}.json"
    if path.exists():
        entry = json.loads(path.read_text())
        SESSIONS[sid] = entry
        return entry
    return None

# Friendly copy for the API's photo-quality errors: direction, not mood.
FACE_TOO_SMALL = (
    "Your face needs to fill more of the frame -- at least 60% of the photo's width. "
    "Move closer or crop the photo tighter (chest up, face centered) and try again."
)
ERROR_COPY = {
    "error_src_face_too_small": FACE_TOO_SMALL,
    "error_face_position_too_small": FACE_TOO_SMALL,
    "error_face_position_invalid": "Face the camera straight on, centered in the frame, with nothing covering your face.",
    "error_face_position_out_of_boundary": "Part of your face is outside the photo. Center your face and retake it.",
    "error_face_not_forward_facing": "Turn to face the camera directly and retake the photo.",
    "error_face_angle_upward": "Your head is tilted up -- lower your chin slightly and retake.",
    "error_face_angle_downward": "Your head is tilted down -- raise your chin slightly and retake.",
    "error_face_angle_leftward": "Your head is turned left -- face the camera and retake.",
    "error_face_angle_rightward": "Your head is turned right -- face the camera and retake.",
    "error_face_angle_left_tilt": "Your head is tilted -- straighten it and retake.",
    "error_face_angle_right_tilt": "Your head is tilted -- straighten it and retake.",
    "error_lighting_dark": "The photo is too dark. Retake it facing a window or light source.",
    "error_below_min_image_size": "The photo is too small. Use one at least 480px on its short side.",
    "error_pose": "We couldn't read your pose. Stand or sit facing forward, chest up, and retake.",
}


def _asset_url(path: str | Path) -> str:
    return "/assets/" + str(Path(path).resolve().relative_to(config.ASSETS_DIR.resolve()))


def _run_session(sid: str, selfie: Path, mock: bool | None = None) -> None:
    entry = SESSIONS[sid]
    try:
        client = YouCamClient(mock=mock)
        session = DrapingSession(client=client, selfie=selfie)
        entry["trace"] = session.trace  # shared list; polls see events live
        verdict = session.run()
        v = asdict(verdict)
        for r in (v["best"], v["worst"]):
            r["render_url"] = _asset_url(r["render_path"])
        for event in v["trace"]:
            if "render" in event:
                event["render_url"] = _asset_url(event["render"])
        entry["verdict"] = v
        entry["status"] = "done"
    except YouCamError as exc:
        entry["status"] = "error"
        entry["error"] = ERROR_COPY.get(exc.error_code or "", str(exc))
        entry["error_code"] = exc.error_code
    except Exception as exc:  # surface anything else honestly
        entry["status"] = "error"
        entry["error"] = str(exc)
    finally:
        _persist(sid)


@app.post("/api/session")
async def create_session(
    file: UploadFile | None = File(None), persona: str | None = Form(None)
) -> dict:
    if file is None and persona is None:
        raise HTTPException(400, "Upload a selfie or pick a demo persona.")

    sid = uuid.uuid4().hex[:12]
    if persona is not None:
        # Demo personas always run on the mock engine: zero units, can't fail
        # face validation, works identically on a live deployment.
        selfie = config.ASSETS_DIR / "personas" / f"{persona}.jpg"
        if not selfie.exists():
            raise HTTPException(404, f"No demo persona named {persona!r}.")
        mock = True
    else:
        mock = None  # follow server mode; live uploads spend units
        units = _remaining_units()
        if units is not None and units < UNIT_RESERVE + SESSION_COST_EST:
            raise HTTPException(
                402,
                f"Not enough API units for a live session ({units:.0f} left; a session costs "
                f"~{SESSION_COST_EST:.0f} and {UNIT_RESERVE:.0f} are held in reserve). "
                "Try a demo persona instead, or top up units.",
            )
        raw = await file.read()
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            raise HTTPException(400, "That file isn't an image we can read. Use a jpg or png selfie.")
        # skin-tone-analysis is jpg-only and caps the long side at 4096;
        # normalize every upload once here.
        img.thumbnail((2560, 2560))
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        selfie = UPLOADS_DIR / f"{sid}.jpg"
        img.save(selfie, "JPEG", quality=92)

    SESSIONS[sid] = {
        "status": "running",
        "trace": [],
        "verdict": None,
        "selfie": str(selfie),
        "mock": bool(mock) if mock is not None else config.MOCK,
    }
    threading.Thread(target=_run_session, args=(sid, selfie, mock), daemon=True).start()
    return {"session_id": sid}


class DrapeRequest(BaseModel):
    name: str  # palette color name from the verdict


@app.post("/api/session/{sid}/drape")
def drape_swatch(sid: str, req: DrapeRequest) -> dict:
    """Render one of the verdict's palette colors on the user, on demand.

    First render of a color costs 2 units (live mode); repeats are served
    from the disk cache. This is the interactive draping room: click a
    swatch, see it on your own body."""
    entry = SESSIONS.get(sid) or _restore(sid)
    if entry is None or entry["status"] != "done":
        raise HTTPException(404, "Finish a draping session first.")
    v = entry["verdict"]
    match = next((p for p in v["palette"] if p["name"] == req.name), None)
    if match is None:
        raise HTTPException(404, f"{req.name!r} isn't in this verdict's palette.")

    drape_id = f"{v['season_key']}_{req.name.replace(' ', '_')}"
    drape_path = config.DRAPES_DIR / f"{drape_id}.jpg"
    if not drape_path.exists():
        raise HTTPException(404, "No drape asset for that color.")

    # entry["mock"] is set at session creation; older persisted sessions
    # lack it and fall back to the server's mode (None).
    client = YouCamClient(mock=entry.get("mock"))
    render = cloth_vto.try_on(client, Path(entry["selfie"]), drape_path)
    profile = FaceProfile.from_colors(FacialColors(**v["facial_colors"]))
    state = SkinState(
        redness_score=100.0 - v["skin_state"]["redness_severity"],
        radiance_score=100.0 - v["skin_state"]["dullness"],
    )
    measured_hex, measured_lab = extract.garment_color(render, skin=profile.skin)
    score = score_drape(profile, measured_lab, state)
    return {
        "name": req.name,
        "requested_hex": match["hex"],
        "measured_hex": measured_hex,
        "render_url": _asset_url(render),
        "score": score.score,
        "reasons": score.reasons,
    }


@app.get("/api/session/{sid}")
def get_session(sid: str) -> dict:
    entry = SESSIONS.get(sid) or _restore(sid)
    if entry is None:
        raise HTTPException(404, "Unknown session.")
    trace = []
    for event in list(entry["trace"]):
        event = dict(event)
        if "render" in event:
            event["render_url"] = _asset_url(event["render"])
        trace.append(event)
    return {
        "status": entry["status"],
        "trace": trace,
        "verdict": entry["verdict"],
        "error": entry.get("error"),
    }


@app.get("/api/catalog/{sid}")
def get_catalog(sid: str) -> dict:
    entry = SESSIONS.get(sid) or _restore(sid)
    if entry is None or entry["status"] != "done":
        raise HTTPException(404, "Finish a draping session first.")
    v = entry["verdict"]
    profile = FaceProfile.from_colors(FacialColors(**v["facial_colors"]))
    state = SkinState(
        redness_score=100.0 - v["skin_state"]["redness_severity"],
        radiance_score=100.0 - v["skin_state"]["dullness"],
    )
    items = []
    for item in CATALOG:
        s = score_drape(profile, hex_to_lab(item["hex"]), state)
        items.append(
            {
                **item,
                "image_url": _asset_url(config.ASSETS_DIR / item["image"]),
                "match": s.score,
                "reason": s.reasons[0],
            }
        )
    items.sort(key=lambda i: i["match"], reverse=True)
    return {"items": items, "season": v["season_name"]}


GARMENTS_DIR = config.ASSETS_DIR / "garments"


def _session_scoring_context(entry: dict):
    v = entry["verdict"]
    profile = FaceProfile.from_colors(FacialColors(**v["facial_colors"]))
    state = SkinState(
        redness_score=100.0 - v["skin_state"]["redness_severity"],
        radiance_score=100.0 - v["skin_state"]["dullness"],
    )
    return profile, state


@app.post("/api/session/{sid}/check-garment")
async def check_garment(sid: str, file: UploadFile = File(...)) -> dict:
    """Score any store's product photo against the verdict palette. Free --
    color extraction and scoring are local; no API units involved."""
    entry = SESSIONS.get(sid) or _restore(sid)
    if entry is None or entry["status"] != "done":
        raise HTTPException(404, "Finish a draping session first.")
    raw = await file.read()
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(400, "That file isn't an image we can read. Use a jpg or png product photo.")
    img.thumbnail((2048, 2048))
    gid = uuid.uuid4().hex[:10]
    GARMENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = GARMENTS_DIR / f"{sid}_{gid}.jpg"
    img.save(path, "JPEG", quality=92)

    measured_hex, measured_lab = extract.product_color(path)
    profile, state = _session_scoring_context(entry)
    score = score_drape(profile, measured_lab, state)
    entry.setdefault("garments", {})[gid] = str(path)
    _persist(sid)
    return {
        "garment_id": gid,
        "measured_hex": measured_hex,
        "match": score.score,
        "reasons": score.reasons,
    }


class TryGarmentRequest(BaseModel):
    garment_id: str


@app.post("/api/session/{sid}/try-garment")
def try_garment(sid: str, req: TryGarmentRequest) -> dict:
    """Render a checked garment on the user (2 units live, then cached)."""
    entry = SESSIONS.get(sid) or _restore(sid)
    if entry is None or entry["status"] != "done":
        raise HTTPException(404, "Finish a draping session first.")
    path = (entry.get("garments") or {}).get(req.garment_id)
    if path is None or not Path(path).exists():
        raise HTTPException(404, "Check that garment first, then try it on.")
    client = YouCamClient(mock=entry.get("mock"))
    try:
        render = cloth_vto.try_on(client, Path(entry["selfie"]), Path(path))
    except YouCamError as exc:
        raise HTTPException(
            422,
            ERROR_COPY.get(
                exc.error_code or "",
                "The try-on engine couldn't use that photo -- a front-facing product shot of a single garment works best.",
            ),
        )
    profile, state = _session_scoring_context(entry)
    measured_hex, measured_lab = extract.garment_color(render, skin=profile.skin)
    score = score_drape(profile, measured_lab, state)
    return {
        "render_url": _asset_url(render),
        "measured_hex": measured_hex,
        "score": score.score,
        "reasons": score.reasons,
    }


@app.get("/api/session/{sid}/card")
def get_card(sid: str) -> dict:
    """Build (once) and return the shareable verdict card PNG."""
    entry = SESSIONS.get(sid) or _restore(sid)
    if entry is None or entry["status"] != "done":
        raise HTTPException(404, "Finish a draping session first.")
    out = config.ASSETS_DIR / "cards" / f"{sid}.png"
    if not out.exists():
        from drape import share_card

        share_card.render_card(entry["verdict"], out)
    return {"card_url": _asset_url(out)}


@app.post("/api/precheck")
async def precheck(file: UploadFile = File(...)) -> dict:
    """Photo quality gate, run before any units are spent."""
    from drape.api import photo_qc

    raw = await file.read()
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        return {
            "issues": [
                {
                    "level": "block",
                    "code": "not_an_image",
                    "message": "That file isn't an image we can read. Use a jpg or png selfie.",
                }
            ]
        }
    return {"issues": photo_qc.check(img)}


@app.get("/api/mode")
def get_mode() -> dict:
    return {"mock": config.MOCK, "units": _remaining_units()}


@app.get("/api/personas")
def get_personas() -> dict:
    persona_dir = config.ASSETS_DIR / "personas"
    return {
        "personas": [
            {"name": p.stem, "image_url": _asset_url(p)}
            for p in sorted(persona_dir.glob("*.jpg"))
        ]
    }


app.mount("/assets", StaticFiles(directory=config.ASSETS_DIR), name="assets")

# Serve the built frontend when it exists (single-service deploy).
_dist = config.BACKEND_ROOT.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
