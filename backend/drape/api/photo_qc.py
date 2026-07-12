"""Pre-flight selfie checks, run BEFORE any units are spent.

Catches locally what would otherwise fail (or silently mislead) at the API:
resolution floors, bad exposure, and -- the silent verdict-killer -- a strong
color cast from warm indoor lighting, which shifts every measured skin value
warm. Levels: "block" stops the session; "warn" is shown with a continue
option.
"""

from __future__ import annotations

from PIL import Image

from drape.colorlab.lab import rgb_to_lab

MIN_SHORT_SIDE = 480  # SD skin-analysis floor per API docs
DARK_LUMA = 60
BRIGHT_LUMA = 232
CAST_CHROMA = 13.0  # background corner chroma above this = colored light


def _region_rgb(img: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    return img.crop(box).resize((1, 1), Image.LANCZOS).getpixel((0, 0))[:3]


def check(img: Image.Image) -> list[dict]:
    issues: list[dict] = []
    w, h = img.size

    if min(w, h) < MIN_SHORT_SIDE:
        issues.append({
            "level": "block",
            "code": "too_small",
            "message": f"This photo is {w}x{h}px; the skin analysis needs at least "
                       f"{MIN_SHORT_SIDE}px on the short side. Use a larger photo.",
        })

    small = img.convert("RGB").resize((64, 64), Image.LANCZOS)
    pixels = list(small.getdata())
    luma = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels) / len(pixels)
    if luma < DARK_LUMA:
        issues.append({
            "level": "warn",
            "code": "too_dark",
            "message": "The photo looks dark. Colors read wrong in dim light -- retake it facing a window if you can.",
        })
    elif luma > BRIGHT_LUMA:
        issues.append({
            "level": "warn",
            "code": "overexposed",
            "message": "The photo looks blown out. Strong highlights wash out your real coloring.",
        })

    # Color cast: sample the top corners (assumed backdrop, not face). Colored
    # ambient light shifts skin readings the same direction it shifts the wall.
    px, py = max(2, w // 12), max(2, h // 12)
    rgb = img.convert("RGB")
    corners = [_region_rgb(rgb, (0, 0, px, py)), _region_rgb(rgb, (w - px, 0, w, py))]
    avg = tuple(sum(c[i] for c in corners) // 2 for i in range(3))
    corner_lab = rgb_to_lab(avg)
    if corner_lab.chroma > CAST_CHROMA and corner_lab.L > 25:
        tint = "warm" if corner_lab.b > 0 else "cool"
        issues.append({
            "level": "warn",
            "code": "color_cast",
            "message": f"The lighting looks {tint}-tinted, which can skew your undertone reading. "
                       "Daylight from a window gives the truest verdict.",
        })

    return issues
