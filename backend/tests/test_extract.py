from PIL import Image

from drape.colorlab import extract
from drape.colorlab.lab import delta_e, hex_to_lab, rgb_to_lab


def _fake_render(tmp_path, garment_rgb, skin_rgb=(200, 160, 140)):
    """Selfie-shaped image: skin-toned top half, garment-colored torso."""
    img = Image.new("RGB", (400, 500), (230, 230, 234))
    face = Image.new("RGB", (200, 220), skin_rgb)
    img.paste(face, (100, 50))
    torso = Image.new("RGB", (320, 175), garment_rgb)
    img.paste(torso, (40, 310))
    path = tmp_path / "render.jpg"
    img.save(path, quality=95)
    return path


def test_extracts_garment_not_skin(tmp_path):
    garment = (156, 71, 34)  # rust
    render = _fake_render(tmp_path, garment)
    _hex, lab = extract.garment_color(render, skin=rgb_to_lab((200, 160, 140)))
    assert delta_e(lab, rgb_to_lab(garment)) < 12


def test_extracts_cool_garment(tmp_path):
    garment = (110, 30, 60)  # burgundy
    render = _fake_render(tmp_path, garment)
    _hex, lab = extract.garment_color(render, skin=rgb_to_lab((200, 160, 140)))
    assert delta_e(lab, rgb_to_lab(garment)) < 12
    assert delta_e(lab, hex_to_lab("#d8a13b")) > 30  # definitely not gold
