from PIL import Image

from drape.api import photo_qc


def _codes(img):
    return {i["code"] for i in photo_qc.check(img)}


def _selfie(size=(800, 1000), bg=(226, 228, 232), brightness=1.0):
    img = Image.new("RGB", size, tuple(int(c * brightness) for c in bg))
    # face-ish blob so the frame isn't uniform
    face = Image.new("RGB", (size[0] // 2, size[1] // 2), tuple(int(c * brightness) for c in (200, 160, 140)))
    img.paste(face, (size[0] // 4, size[1] // 8))
    return img


def test_good_photo_passes():
    assert _codes(_selfie()) == set()


def test_small_photo_blocks():
    issues = photo_qc.check(_selfie(size=(400, 500)))
    assert any(i["code"] == "too_small" and i["level"] == "block" for i in issues)


def test_dark_photo_warns():
    assert "too_dark" in _codes(_selfie(brightness=0.15))


def test_warm_cast_warns():
    img = _selfie(bg=(232, 205, 160))  # warm lamp glow on the backdrop
    issues = photo_qc.check(img)
    cast = [i for i in issues if i["code"] == "color_cast"]
    assert cast and "warm" in cast[0]["message"]
