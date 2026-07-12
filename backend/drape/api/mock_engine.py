"""Offline simulation of the YouCam API for development and tests.

Zero units, zero network. The simulation is honest enough to exercise the
whole pipeline: skin tone is sampled from the actual selfie pixels, and cloth
try-on composites the requested garment's color onto the selfie's torso
region, so colorlab.extract measures roughly what a real render would show.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from drape import config
from drape.api import youcam_client as yc


def _path_from_file_id(file_id: str) -> Path:
    if not file_id.startswith("mock:"):
        raise ValueError(f"mock engine got a non-mock file_id: {file_id!r}")
    return Path(file_id.split(":", 2)[2])


def _face_box(img: Image.Image) -> tuple[int, int, int, int]:
    """Assume a selfie framed per API requirements: face centered, upper half."""
    w, h = img.size
    return (int(w * 0.30), int(h * 0.12), int(w * 0.70), int(h * 0.55))


def _avg(img: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    region = img.crop(box).resize((1, 1), Image.LANCZOS)
    return region.getpixel((0, 0))[:3]


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def run(feature: str, params: dict) -> dict:
    if feature == yc.SKIN_TONE:
        return _skin_tone(params)
    if feature == yc.SKIN_ANALYSIS:
        return _skin_analysis(params)
    if feature == yc.CLOTH:
        return _cloth(params)
    raise ValueError(f"mock engine does not support feature {feature!r}")


def _skin_tone(params: dict) -> dict:
    img = Image.open(_path_from_file_id(params["src_file_id"])).convert("RGB")
    w, h = img.size
    fx0, fy0, fx1, fy1 = _face_box(img)
    # Cheek band for skin, top strip for hair, eye line for eyes.
    skin = _avg(img, (fx0 + (fx1 - fx0) // 6, (fy0 + fy1) // 2, fx1 - (fx1 - fx0) // 6, fy1 - (fy1 - fy0) // 6))
    hair = _avg(img, (int(w * 0.35), 0, int(w * 0.65), max(1, int(h * 0.08))))
    eyes = _avg(img, (fx0, fy0 + (fy1 - fy0) // 3, fx1, fy0 + (fy1 - fy0) // 2))
    return {
        "task_status": "success",
        "results": {
            "color": {
                "skin_color": _hex(skin),
                "hair_color": _hex(hair),
                "hair_color_name": "Brown",
                "eye_color": _hex(eyes),
                "eye_color_name": "Brown",
                "eyebrow_color": _hex(hair),
                "lip_color": "#c06a6a",
            }
        },
    }


def _skin_analysis(params: dict) -> dict:
    img = Image.open(_path_from_file_id(params["src_file_id"])).convert("RGB")
    fx0, fy0, fx1, fy1 = _face_box(img)
    r, g, b = _avg(img, (fx0, (fy0 + fy1) // 2, fx1, fy1))
    # Redder-than-average cheeks -> lower redness score (API: higher = healthier).
    excess_red = max(0, r - (g + b) // 2)
    redness = max(20, 95 - excess_red)
    luma = int(0.299 * r + 0.587 * g + 0.114 * b)
    radiance = max(25, min(95, 40 + luma // 3))
    output = []
    for action in params.get("dst_actions", []):
        score = {"redness": redness, "radiance": radiance}.get(action, 75)
        output.append({"type": action, "ui_score": score, "raw_score": float(score), "mask_urls": []})
    return {"task_status": "success", "results": {"output": output}}


def _cloth(params: dict) -> dict:
    src = Image.open(_path_from_file_id(params["src_file_id"])).convert("RGB")
    if "ref_file_id" in params:
        ref_path = _path_from_file_id(params["ref_file_id"])
    else:
        ref_path = Path(params["ref_file_url"].removeprefix("file://"))
    ref = Image.open(ref_path).convert("RGB")
    # Garment color = average of the reference's center (product shots are
    # garment-on-plain-background, so the center is fabric).
    rw, rh = ref.size
    garment_rgb = _avg(ref, (rw // 4, rh // 4, rw * 3 // 4, rh * 3 // 4))

    out = src.copy()
    w, h = out.size
    torso = Image.new("RGB", (int(w * 0.8), int(h * 0.35)), garment_rgb)
    out.paste(torso, (int(w * 0.1), int(h * 0.62)))

    config.RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    import hashlib

    name = hashlib.sha256(f"{params}".encode()).hexdigest()[:16]
    dst = config.RENDERS_DIR / f"mock_render_{name}.jpg"
    out.save(dst, quality=90)
    return {"task_status": "success", "results": {"url": dst.resolve().as_uri()}}
