"""Generate the drape wardrobe: one garment image per test color.

Two modes:
  synthetic (default)  draws a clean crew-neck top product shot per color.
  --base FILE          recolors a real garment product photo per color
                       (grayscale luminance re-mapped to the target shade).

Run once; outputs land in assets/drapes/{drape_id}.jpg. Zero API cost.
The day-1/2 live-API gate decides which mode's output cloth-v3 renders
consistently; swap modes without touching any other code.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drape import config  # noqa: E402
from drape.colorlab import seasons  # noqa: E402
from drape.colorlab.lab import hex_to_rgb  # noqa: E402

CANVAS = (768, 1024)
BG = (245, 245, 247)


def _shade(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)


def draw_tee(rgb: tuple[int, int, int]) -> Image.Image:
    """A front-facing crew-neck top product shot on a plain background."""
    w, h = CANVAS
    img = Image.new("RGB", CANVAS, BG)
    d = ImageDraw.Draw(img)

    cx = w // 2
    top = int(h * 0.14)
    shoulder_w = int(w * 0.62)
    hem = int(h * 0.88)
    body_w = int(w * 0.52)
    sleeve_drop = int(h * 0.36)

    body = [
        (cx - shoulder_w // 2, top + int(h * 0.05)),          # left shoulder
        (cx - int(w * 0.10), top),                             # left neck
        (cx + int(w * 0.10), top),                             # right neck
        (cx + shoulder_w // 2, top + int(h * 0.05)),           # right shoulder
        (cx + shoulder_w // 2 + int(w * 0.10), sleeve_drop),   # right sleeve end
        (cx + body_w // 2, sleeve_drop - int(h * 0.02)),       # right underarm
        (cx + body_w // 2, hem),                               # right hem
        (cx - body_w // 2, hem),                               # left hem
        (cx - body_w // 2, sleeve_drop - int(h * 0.02)),       # left underarm
        (cx - shoulder_w // 2 - int(w * 0.10), sleeve_drop),   # left sleeve end
    ]
    d.polygon(body, fill=rgb)

    # neckline
    d.ellipse(
        (cx - int(w * 0.11), top - int(h * 0.025), cx + int(w * 0.11), top + int(h * 0.035)),
        fill=BG,
    )
    d.arc(
        (cx - int(w * 0.11), top - int(h * 0.02), cx + int(w * 0.11), top + int(h * 0.045)),
        start=0,
        end=180,
        fill=_shade(rgb, 0.75),
        width=6,
    )

    # soft fabric shading: darker side panels + a center highlight
    shade = Image.new("L", CANVAS, 0)
    sd = ImageDraw.Draw(shade)
    sd.polygon(body, fill=40)
    sd.rectangle((cx - body_w // 2, sleeve_drop, cx - body_w // 4, hem), fill=70)
    sd.rectangle((cx + body_w // 4, sleeve_drop, cx + body_w // 2, hem), fill=70)
    shade = shade.filter(ImageFilter.GaussianBlur(30))
    dark = Image.new("RGB", CANVAS, _shade(rgb, 0.82))
    img = Image.composite(dark, img, shade.point(lambda p: min(p, 70)))

    return img


def recolor_base(base: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    """Re-map a real product photo's luminance to the target color."""
    gray = ImageOps.grayscale(base)
    black = _shade(rgb, 0.25)
    white = _shade(rgb, 1.35)
    colorized = ImageOps.colorize(gray, black=black, mid=rgb, white=white)
    # keep near-white background white so it still reads as a product shot
    mask = gray.point(lambda p: 255 if p > 235 else 0)
    colorized.paste(Image.new("RGB", base.size, BG), mask=mask)
    return colorized


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, help="real garment product photo to recolor")
    args = parser.parse_args()

    base = Image.open(args.base).convert("RGB") if args.base else None
    config.DRAPES_DIR.mkdir(parents=True, exist_ok=True)

    colors = seasons.all_drape_colors()
    for drape_id, (hex_, name) in colors.items():
        rgb = hex_to_rgb(hex_)
        img = recolor_base(base, rgb) if base is not None else draw_tee(rgb)
        out = config.DRAPES_DIR / f"{drape_id}.jpg"
        img.save(out, quality=92)
    print(f"wrote {len(colors)} drapes to {config.DRAPES_DIR}")


if __name__ == "__main__":
    main()
