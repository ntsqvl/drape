"""Measure the garment color actually present in a VTO render.

We score what the render shows, not what we asked for: generative VTO can
drift the garment color, so the harmony engine is fed the dominant color
sampled from the torso region of the output image.

Cluster selection is careful about two traps:
  * the background can leak into the torso crop -> estimate it from the image
    corners and exclude matching clusters outright;
  * warm garments (rust, camel...) are legitimately CLOSE to skin in Lab, so a
    skin-like top cluster is only skipped when a strong runner-up exists --
    never excluded unconditionally.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from drape.colorlab.lab import LabColor, delta_e, rgb_to_hex, rgb_to_lab

# Torso band for a chest-up, front-facing photo per cloth-v3 spec.
TORSO_BOX = (0.18, 0.60, 0.82, 0.95)  # fractions of (left, top, right, bottom)
BACKGROUND_DELTA_E = 14.0
SKIN_DELTA_E = 18.0
RUNNER_UP_RATIO = 0.4
QUANT_COLORS = 8


def _background_lab(img: Image.Image) -> LabColor:
    """Estimate the backdrop from the top corners (never the person)."""
    w, h = img.size
    px, py = max(2, w // 20), max(2, h // 20)
    corners = [img.crop((0, 0, px, py)), img.crop((w - px, 0, w, py))]
    rgbs = [c.resize((1, 1), Image.LANCZOS).getpixel((0, 0))[:3] for c in corners]
    avg = tuple(sum(c[i] for c in rgbs) // len(rgbs) for i in range(3))
    return rgb_to_lab(avg)


def garment_color(render: str | Path, skin: LabColor | None = None) -> tuple[str, LabColor]:
    """Dominant garment color of the render's torso region -> (hex, Lab)."""
    img = Image.open(render).convert("RGB")
    w, h = img.size
    box = (
        int(TORSO_BOX[0] * w),
        int(TORSO_BOX[1] * h),
        int(TORSO_BOX[2] * w),
        int(TORSO_BOX[3] * h),
    )
    background = _background_lab(img)
    region = img.crop(box)
    # Median-cut quantization gives us cluster centers + pixel counts cheaply.
    quant = region.quantize(colors=QUANT_COLORS, method=Image.Quantize.MEDIANCUT)
    palette = quant.getpalette()[: QUANT_COLORS * 3]
    counts = sorted(quant.getcolors(), reverse=True)  # [(count, palette_index)]

    clusters: list[tuple[int, tuple[int, int, int], LabColor]] = []
    for count, idx in counts:
        rgb = tuple(palette[idx * 3 : idx * 3 + 3])
        lab = rgb_to_lab(rgb)
        if delta_e(lab, background) < BACKGROUND_DELTA_E:
            continue
        clusters.append((count, rgb, lab))
    if not clusters:  # degenerate: torso crop is all backdrop
        count, idx = counts[0]
        rgb = tuple(palette[idx * 3 : idx * 3 + 3])
        return rgb_to_hex(rgb), rgb_to_lab(rgb)

    top = clusters[0]
    if (
        skin is not None
        and len(clusters) > 1
        and delta_e(top[2], skin) < SKIN_DELTA_E
        and clusters[1][0] >= RUNNER_UP_RATIO * top[0]
    ):
        top = clusters[1]
    return rgb_to_hex(top[1]), top[2]


# Center region for e-commerce product shots: the garment fills the middle,
# the backdrop fills the edges.
PRODUCT_BOX = (0.22, 0.22, 0.78, 0.78)


def product_color(image: str | Path) -> tuple[str, LabColor]:
    """Dominant fabric color of a product photo -> (hex, Lab).

    Unlike garment_color this has no person to exclude -- only the backdrop,
    estimated from the image corners.
    """
    img = Image.open(image).convert("RGB")
    w, h = img.size
    box = (
        int(PRODUCT_BOX[0] * w),
        int(PRODUCT_BOX[1] * h),
        int(PRODUCT_BOX[2] * w),
        int(PRODUCT_BOX[3] * h),
    )
    background = _background_lab(img)
    quant = img.crop(box).quantize(colors=QUANT_COLORS, method=Image.Quantize.MEDIANCUT)
    palette = quant.getpalette()[: QUANT_COLORS * 3]
    counts = sorted(quant.getcolors(), reverse=True)

    for count, idx in counts:
        rgb = tuple(palette[idx * 3 : idx * 3 + 3])
        lab = rgb_to_lab(rgb)
        if delta_e(lab, background) >= BACKGROUND_DELTA_E:
            return rgb_to_hex(rgb), lab
    # degenerate: garment matches the backdrop; report the dominant color
    count, idx = counts[0]
    rgb = tuple(palette[idx * 3 : idx * 3 + 3])
    return rgb_to_hex(rgb), rgb_to_lab(rgb)
