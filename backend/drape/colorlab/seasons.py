"""The 12-season personal color model: probe drapes, palettes, worst colors.

Palette hex values follow commonly published seasonal color guides; they are
inputs to a heuristic, not ground truth. Every color here has a matching
pre-generated drape image in assets/drapes/ (see scripts/make_drapes.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------- probes

# Round 1: temperature. Similar lightness/chroma class, opposite temperature
# (gold b*/C = +0.98 vs orchid -0.54; fuchsia was rejected as a cool probe --
# its Lab b* is only -0.11, too temperature-ambiguous to separate cleanly).
PROBE_WARM = ("probe_warm_gold", "#d8a13b", "warm gold")
PROBE_COOL = ("probe_cool_orchid", "#b45fb2", "cool orchid")
# Neutral tiebreaker probe (used only when round 1 is inconclusive).
PROBE_NEUTRAL = ("probe_soft_teal", "#4f8a8b", "soft teal")

# Round 2: depth, within each temperature branch. Each pair's L midpoint must
# sit at ~51 (profile depth 0.5): the pair's midpoint IS the implicit
# light/deep boundary. (Rust, L=40.7, once served as the warm-deep probe and
# silently moved that boundary to depth 0.31 -- caught by the golden set.)
PROBE_WARM_LIGHT = ("probe_peach", "#f4b183", "light peach")  # L 77.5
PROBE_WARM_DEEP = ("probe_espresso", "#6a3a1b", "deep espresso")  # L 29.8
PROBE_COOL_LIGHT = ("probe_powder_blue", "#9fc2e0", "powder blue")  # L 76.9
PROBE_COOL_DEEP = ("probe_burgundy", "#6e1e3c", "burgundy")  # L 25.5


@dataclass(frozen=True)
class Season:
    key: str
    name: str
    family: str  # spring | summer | autumn | winter
    tagline: str
    palette: tuple[tuple[str, str], ...]  # (hex, display name)
    worst: tuple[str, str, str] = field(default=("#000000", "black", ""))  # hex, name, why


SEASONS: dict[str, Season] = {
    s.key: s
    for s in [
        # ------------------------------------------------ spring (warm + light/clear)
        Season(
            "light_spring",
            "Light Spring",
            "spring",
            "Sunlit, delicate warmth",
            (
                ("#ffd1a9", "peach"),
                ("#fff3b0", "buttercream"),
                ("#a8e6cf", "fresh mint"),
                ("#ffaaa5", "salmon pink"),
                ("#b5eaea", "powder aqua"),
                ("#f9c784", "apricot cream"),
            ),
            ("#1c1c1e", "black", "hard black overwhelms light-warm coloring"),
        ),
        Season(
            "true_spring",
            "True Spring",
            "spring",
            "Clear, golden, alive",
            (
                ("#ff7f50", "coral"),
                ("#ffc94a", "golden yellow"),
                ("#66bb6a", "leaf green"),
                ("#40c4e0", "clear aqua"),
                ("#ff8c42", "apricot"),
                ("#e8503a", "poppy red"),
            ),
            ("#4a4e57", "cool charcoal", "ashy gray drains golden warmth"),
        ),
        Season(
            "bright_spring",
            "Bright Spring",
            "spring",
            "High-voltage warm brilliance",
            (
                ("#ff6f61", "bright coral"),
                ("#ffd34e", "sunflower"),
                ("#3ec1d3", "turquoise"),
                ("#7fb800", "lime green"),
                ("#ff9633", "tangerine"),
                ("#f45b69", "watermelon"),
            ),
            ("#9e7b8c", "dusty mauve", "muted rose grays out bright coloring"),
        ),
        # ------------------------------------------------ summer (cool + light/muted)
        Season(
            "light_summer",
            "Light Summer",
            "summer",
            "Misty, airy coolness",
            (
                ("#aecbeb", "powder blue"),
                ("#e3b7d2", "orchid pink"),
                ("#b8e0d2", "seafoam"),
                ("#d6c6e1", "lilac"),
                ("#f5c7cb", "shell rose"),
                ("#9fb9df", "cornflower"),
            ),
            ("#c46210", "pumpkin orange", "hot orange clashes with cool delicacy"),
        ),
        Season(
            "true_summer",
            "True Summer",
            "summer",
            "Cool, calm, rose-toned",
            (
                ("#6c8ebf", "soft blue"),
                ("#b57ba6", "mauve"),
                ("#5f9ea0", "cadet teal"),
                ("#c97b8b", "raspberry rose"),
                ("#8896c6", "periwinkle"),
                ("#7a9e7e", "sage"),
            ),
            ("#ff7518", "bright orange", "warm brights overpower cool softness"),
        ),
        Season(
            "soft_summer",
            "Soft Summer",
            "summer",
            "Muted, shadowed elegance",
            (
                ("#93a9bb", "gray blue"),
                ("#a9868f", "rose taupe"),
                ("#7e9680", "gray sage"),
                ("#9b8aa6", "dusty plum"),
                ("#b0899b", "heather rose"),
                ("#6e7f99", "slate"),
            ),
            ("#e8e337", "neon yellow", "acid brights make muted coloring vanish"),
        ),
        # ------------------------------------------------ autumn (warm + deep/muted)
        Season(
            "soft_autumn",
            "Soft Autumn",
            "autumn",
            "Golden haze, quiet earth",
            (
                ("#c2a878", "camel"),
                ("#9a8b4f", "olive gold"),
                ("#b97455", "terracotta rose"),
                ("#8a9a5b", "moss"),
                ("#a9746e", "clay rose"),
                ("#c99b67", "honey"),
            ),
            ("#e0218a", "fuchsia", "cool neon pink fights soft golden tones"),
        ),
        Season(
            "true_autumn",
            "True Autumn",
            "autumn",
            "Rich, spiced, sun-baked",
            (
                ("#b5651d", "rust"),
                ("#808000", "olive"),
                ("#d2691e", "pumpkin spice"),
                ("#8b4513", "saddle brown"),
                ("#cc9900", "mustard"),
                ("#556b2f", "forest olive"),
            ),
            ("#f3c9dd", "icy pink", "frosty pastels wash out rich warmth"),
        ),
        Season(
            "deep_autumn",
            "Deep Autumn",
            "autumn",
            "Ember-dark warmth",
            (
                ("#7c3f00", "espresso rust"),
                ("#654321", "dark chocolate"),
                ("#9a2a2a", "brick red"),
                ("#4b5320", "army green"),
                ("#b8860b", "dark gold"),
                ("#5c4033", "mahogany"),
            ),
            ("#c9b8e8", "pastel lavender", "powdery cool tints go flat on deep warmth"),
        ),
        # ------------------------------------------------ winter (cool + deep/clear)
        Season(
            "bright_winter",
            "Bright Winter",
            "winter",
            "Electric cool contrast",
            (
                ("#e4002b", "true red"),
                ("#0057b8", "royal blue"),
                ("#ff1493", "shocking pink"),
                ("#00a86b", "emerald"),
                ("#7d2ae8", "violet"),
                ("#00ced1", "ice turquoise"),
            ),
            ("#8f8060", "muted khaki", "grayed earth tones dull high contrast"),
        ),
        Season(
            "true_winter",
            "True Winter",
            "winter",
            "Stark, jewel-toned clarity",
            (
                ("#c8102e", "crimson"),
                ("#003da5", "cobalt"),
                ("#00843d", "emerald green"),
                ("#f4f6f8", "pure white"),
                ("#101014", "true black"),
                ("#6a0dad", "royal purple"),
            ),
            ("#c8a97c", "warm beige", "golden beige muddies cool clarity"),
        ),
        Season(
            "deep_winter",
            "Deep Winter",
            "winter",
            "Midnight richness",
            (
                ("#500b28", "wine"),
                ("#0b3d2e", "pine"),
                ("#191970", "midnight blue"),
                ("#4b0082", "indigo"),
                ("#8a0303", "blood red"),
                ("#2f4f4f", "dark slate"),
            ),
            ("#ffb49a", "peach cream", "warm pastels look chalky on deep coolness"),
        ),
    ]
}

FAMILIES = {
    "spring": ["light_spring", "true_spring", "bright_spring"],
    "summer": ["light_summer", "true_summer", "soft_summer"],
    "autumn": ["soft_autumn", "true_autumn", "deep_autumn"],
    "winter": ["bright_winter", "true_winter", "deep_winter"],
}

# Signature drape per season used in round 3 (index into season.palette).
# bright_winter deliberately uses shocking pink, not its true red: red's
# b*/chroma reads warm in the harmony engine, which would sabotage the
# season's own signature on the cool profiles it belongs to.
SIGNATURE = {
    "light_spring": 0, "true_spring": 0, "bright_spring": 0,
    "light_summer": 0, "true_summer": 3, "soft_summer": 1,
    "soft_autumn": 2, "true_autumn": 0, "deep_autumn": 2,
    "bright_winter": 2, "true_winter": 1, "deep_winter": 0,
}


def all_drape_colors() -> dict[str, tuple[str, str]]:
    """Every color that needs a pre-generated drape image: id -> (hex, name)."""
    colors: dict[str, tuple[str, str]] = {}
    for pid, hex_, name in [
        PROBE_WARM,
        PROBE_COOL,
        PROBE_NEUTRAL,
        PROBE_WARM_LIGHT,
        PROBE_WARM_DEEP,
        PROBE_COOL_LIGHT,
        PROBE_COOL_DEEP,
    ]:
        colors[pid] = (hex_, name)
    for season in SEASONS.values():
        for hex_, name in season.palette:
            colors[f"{season.key}_{name.replace(' ', '_')}"] = (hex_, name)
        whex, wname, _ = season.worst
        colors[f"{season.key}_worst_{wname.replace(' ', '_')}"] = (whex, wname)
    return colors
