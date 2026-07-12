"""Generate the demo shop catalog: 12 garments spanning the seasonal map.

Writes catalog.json + a product image per item (offline, zero API cost).
Colors are hand-labeled so match scoring never depends on extraction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drape import config  # noqa: E402
from drape.colorlab.lab import hex_to_rgb  # noqa: E402
from scripts.make_drapes import draw_tee  # noqa: E402

ITEMS = [
    {"id": "rust-crew", "name": "Rust crew tee", "hex": "#b5651d", "price": 38},
    {"id": "wine-rib-top", "name": "Wine ribbed top", "hex": "#500b28", "price": 52},
    {"id": "powder-boxy-tee", "name": "Powder blue boxy tee", "hex": "#aecbeb", "price": 34},
    {"id": "coral-scoop", "name": "Bright coral scoop", "hex": "#ff6f61", "price": 42},
    {"id": "slate-longsleeve", "name": "Slate long sleeve", "hex": "#6e7f99", "price": 48},
    {"id": "golden-crew", "name": "Golden yellow crew", "hex": "#ffc94a", "price": 36},
    {"id": "army-utility-top", "name": "Army green utility top", "hex": "#4b5320", "price": 58},
    {"id": "cobalt-tee", "name": "Cobalt tee", "hex": "#003da5", "price": 40},
    {"id": "peach-drape-top", "name": "Peach drape top", "hex": "#ffd1a9", "price": 44},
    {"id": "camel-knit", "name": "Camel knit tee", "hex": "#c2a878", "price": 56},
    {"id": "emerald-vneck", "name": "Emerald v-neck", "hex": "#00a86b", "price": 46},
    {"id": "mauve-relaxed", "name": "Mauve relaxed tee", "hex": "#b57ba6", "price": 39},
]


def main() -> None:
    out_dir = config.ASSETS_DIR / "catalog"
    out_dir.mkdir(parents=True, exist_ok=True)
    for item in ITEMS:
        draw_tee(hex_to_rgb(item["hex"])).save(out_dir / f"{item['id']}.jpg", quality=92)
        item["image"] = f"catalog/{item['id']}.jpg"
    catalog_path = config.BACKEND_ROOT / "drape" / "catalog" / "catalog.json"
    catalog_path.write_text(json.dumps(ITEMS, indent=2))
    print(f"wrote {len(ITEMS)} items -> {catalog_path} and images -> {out_dir}")


if __name__ == "__main__":
    main()
