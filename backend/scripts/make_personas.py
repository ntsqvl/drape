"""Generate synthetic persona selfies for offline dev and tests.

Framing matches the API selfie requirements (face centered, >=60% width,
chest-up) and the mock engine's sampling regions. These are geometric stand-
ins, not real photos: good enough to exercise the pipeline deterministically,
never shown in the demo.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drape import config  # noqa: E402

SIZE = (800, 1000)

PERSONAS = {
    # golden tan skin, dark warm hair -> should lean warm/deep (autumn-ish)
    "amber": {"skin": (141, 96, 59), "hair": (46, 29, 16), "eye": (94, 62, 40)},
    # rosy light skin, ash hair -> should lean cool/light (summer-ish)
    "elsa": {"skin": (236, 195, 189), "hair": (156, 142, 125), "eye": (90, 105, 140)},
    # golden light skin, warm blonde -> should lean warm/light (spring-ish)
    "sunny": {"skin": (242, 201, 154), "hair": (191, 142, 80), "eye": (110, 130, 90)},
}


def make(name: str, skin, hair, eye) -> Path:
    w, h = SIZE
    img = Image.new("RGB", SIZE, (226, 228, 232))
    d = ImageDraw.Draw(img)

    # face fills 30-70% x, 12-55% y (the mock engine's face box)
    d.ellipse((w * 0.28, h * 0.10, w * 0.72, h * 0.58), fill=skin)
    # hair: cap over the top of the head + the very top strip the mock samples
    d.rectangle((w * 0.33, 0, w * 0.67, h * 0.09), fill=hair)
    d.ellipse((w * 0.26, h * 0.06, w * 0.74, h * 0.30), fill=hair)
    d.ellipse((w * 0.30, h * 0.14, w * 0.70, h * 0.52), fill=skin)
    # eyes on the eye line (~ y 0.27-0.34)
    for ex in (0.41, 0.59):
        d.ellipse((w * ex - 14, h * 0.29, w * ex + 14, h * 0.33), fill=eye)
    # neck + plain tee torso
    d.rectangle((w * 0.42, h * 0.55, w * 0.58, h * 0.66), fill=skin)
    d.rectangle((w * 0.15, h * 0.64, w * 0.85, h), fill=(140, 140, 145))

    out = config.ASSETS_DIR / "personas" / f"{name}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def main() -> None:
    for name, c in PERSONAS.items():
        path = make(name, c["skin"], c["hair"], c["eye"])
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
