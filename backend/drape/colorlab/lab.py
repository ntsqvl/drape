"""sRGB <-> CIELAB conversion and color helpers (D65, 2-degree observer).

Pure Python on purpose: no numpy dependency for a handful of 3-vectors.
Delta-E is CIE76 -- adequate for ranking drape candidates, and simple enough
to explain in the README.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_D65 = (95.047, 100.0, 108.883)


@dataclass(frozen=True)
class LabColor:
    L: float
    a: float
    b: float

    @property
    def chroma(self) -> float:
        return math.hypot(self.a, self.b)

    @property
    def hue_deg(self) -> float:
        """LCh hue angle in [0, 360). ~40deg is red-orange, ~90 yellow, ~270 blue."""
        return math.degrees(math.atan2(self.b, self.a)) % 360.0


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.lstrip("#")
    if len(s) != 6:
        raise ValueError(f"expected #rrggbb, got {hex_str!r}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _srgb_to_linear(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb: tuple[int, int, int]) -> LabColor:
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    # linear sRGB -> XYZ (D65)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) * 100.0
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) * 100.0
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) * 100.0

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16.0 / 116.0)

    fx, fy, fz = (f(v / w) for v, w in zip((x, y, z), _D65))
    return LabColor(L=116.0 * fy - 16.0, a=500.0 * (fx - fy), b=200.0 * (fy - fz))


def hex_to_lab(hex_str: str) -> LabColor:
    return rgb_to_lab(hex_to_rgb(hex_str))


def delta_e(c1: LabColor, c2: LabColor) -> float:
    return math.sqrt((c1.L - c2.L) ** 2 + (c1.a - c2.a) ** 2 + (c1.b - c2.b) ** 2)


def hue_distance_deg(h1: float, h2: float) -> float:
    """Shortest angular distance between two hue angles, in [0, 180]."""
    d = abs(h1 - h2) % 360.0
    return min(d, 360.0 - d)
