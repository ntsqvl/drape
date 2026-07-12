"""Compose the shareable verdict card: a 1080x1350 PNG (4:5, feed-friendly)
with the season name, the best-drape render, and the ranked palette.

Fonts are bundled OFL variable fonts; variation axes are set best-effort and
fall back to the default instance if the FreeType build lacks support.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from drape import config

W, H = 1080, 1350
PLASTER = (233, 230, 223)
BONE = (251, 250, 247)
INK = (43, 36, 48)
TAUPE = (109, 100, 88)
HAIRLINE = (214, 209, 199)

FONTS = config.ASSETS_DIR / "fonts"


def _font(name: str, size: int, axes: dict | None = None) -> ImageFont.FreeTypeFont:
    try:
        font = ImageFont.truetype(str(FONTS / name), size)
        if axes:
            try:
                names = [a.axis.decode() if isinstance(a.axis, bytes) else a.axis for a in font.get_variation_axes()]
                font.set_variation_by_axes([axes.get(n, d.default) for n, d in zip(names, font.get_variation_axes())])
            except Exception:
                pass
        return font
    except Exception:
        return ImageFont.load_default(size)


def _hex_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), radius=radius, fill=255)
    out = Image.new("RGBA", img.size)
    out.paste(img, (0, 0), mask)
    return out


def render_card(verdict: dict, out_path: Path) -> Path:
    card = Image.new("RGB", (W, H), PLASTER)
    d = ImageDraw.Draw(card)
    accent = _hex_rgb(verdict["palette"][0]["hex"])

    display = _font("Fraunces-Italic.ttf", 108, {"opsz": 144, "wght": 420})
    body = _font("Archivo.ttf", 30, {"wght": 500})
    body_sm = _font("Archivo.ttf", 26, {"wght": 400})
    mono = _font("IBMPlexMono-Regular.ttf", 24)
    mono_sm = _font("IBMPlexMono-Regular.ttf", 20)

    # masthead
    d.text((72, 64), "D R A P E", font=body, fill=INK)
    d.text((W - 72, 68), "PERSONAL COLOR VERDICT", font=mono_sm, fill=TAUPE, anchor="ra")
    d.line((72, 128, W - 72, 128), fill=HAIRLINE, width=2)

    # season
    season = verdict["season_name"].replace(" (neutral lean)", "")
    d.text((72, 168), season, font=display, fill=INK)
    d.text((76, 320), verdict["tagline"], font=mono, fill=TAUPE)
    d.text(
        (W - 72, 320),
        f"{verdict['confidence']} confidence",
        font=mono_sm,
        fill=TAUPE,
        anchor="ra",
    )

    # best render, framed
    render_path = Path(verdict["best"]["render_path"])
    if render_path.exists():
        photo = Image.open(render_path).convert("RGB")
        pw, ph = 470, 588
        scale = max(pw / photo.width, ph / photo.height)
        photo = photo.resize((int(photo.width * scale) + 1, int(photo.height * scale) + 1))
        photo = photo.crop(((photo.width - pw) // 2, 0, (photo.width - pw) // 2 + pw, ph))
        frame = Image.new("RGB", (pw + 20, ph + 20), BONE)
        frame.paste(photo, (10, 10))
        card.paste(_rounded(frame, 14), (72, 400), _rounded(frame, 14))
        sw = _hex_rgb(verdict["best"]["measured_hex"])
        d.rounded_rectangle((82, 400 + ph + 36, 106, 400 + ph + 60), 6, fill=sw, outline=HAIRLINE)
        d.text((120, 400 + ph + 34), f"{verdict['best']['name']} — yours", font=body_sm, fill=INK)

    # palette column
    x0 = 620
    d.text((x0, 408), "YOUR PALETTE, RANKED", font=mono_sm, fill=TAUPE)
    for i, p in enumerate(verdict["palette"][:6]):
        y = 452 + i * 96
        d.rounded_rectangle((x0, y, x0 + 64, y + 64), 10, fill=_hex_rgb(p["hex"]), outline=HAIRLINE)
        d.text((x0 + 84, y + 4), p["name"], font=body, fill=INK)
        d.text((x0 + 84, y + 38), f"fit {p['score']:.0f}", font=mono_sm, fill=TAUPE)

    # footer
    d.line((72, H - 132, W - 72, H - 132), fill=accent, width=4)
    d.text((72, H - 96), "a draping session, from one selfie", font=mono, fill=TAUPE)
    d.text((W - 72, H - 96), "DRAPE", font=body, fill=INK, anchor="ra")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(out_path, "PNG")
    return out_path
