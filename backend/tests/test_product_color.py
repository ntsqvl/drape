from PIL import Image

from drape.colorlab import extract
from drape.colorlab.lab import delta_e, rgb_to_lab


def _product_shot(tmp_path, garment_rgb, bg=(246, 246, 248)):
    """Garment blob centered on a light e-commerce backdrop."""
    img = Image.new("RGB", (900, 1100), bg)
    tee = Image.new("RGB", (520, 640), garment_rgb)
    img.paste(tee, (190, 230))
    path = tmp_path / "product.jpg"
    img.save(path, quality=95)
    return path


def test_reads_fabric_not_backdrop(tmp_path):
    rust = (156, 71, 34)
    _hex, lab = extract.product_color(_product_shot(tmp_path, rust))
    assert delta_e(lab, rgb_to_lab(rust)) < 12


def test_light_garment_on_light_backdrop(tmp_path):
    powder = (174, 203, 235)
    _hex, lab = extract.product_color(_product_shot(tmp_path, powder))
    assert delta_e(lab, rgb_to_lab(powder)) < 12


def test_degenerate_white_on_white_still_returns_a_color(tmp_path):
    white = (250, 250, 250)
    hex_, _lab = extract.product_color(_product_shot(tmp_path, white))
    assert hex_.startswith("#")
