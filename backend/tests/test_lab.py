import pytest

from drape.colorlab.lab import delta_e, hex_to_lab, hue_distance_deg


def test_white_and_black_endpoints():
    white = hex_to_lab("#ffffff")
    assert white.L == pytest.approx(100.0, abs=0.1)
    assert white.chroma < 0.5
    black = hex_to_lab("#000000")
    assert black.L == pytest.approx(0.0, abs=0.1)


def test_primary_red_reference_values():
    red = hex_to_lab("#ff0000")
    # canonical sRGB red in Lab: L~53.2, a~80.1, b~67.2
    assert red.L == pytest.approx(53.2, abs=0.5)
    assert red.a == pytest.approx(80.1, abs=0.7)
    assert red.b == pytest.approx(67.2, abs=0.7)


def test_delta_e_identity_and_symmetry():
    c1, c2 = hex_to_lab("#d8a13b"), hex_to_lab("#c13a7c")
    assert delta_e(c1, c1) == 0
    assert delta_e(c1, c2) == pytest.approx(delta_e(c2, c1))
    assert delta_e(c1, c2) > 30  # gold vs fuchsia are far apart


def test_hue_angles_land_in_expected_quadrants():
    assert 60 <= hex_to_lab("#ffc94a").hue_deg <= 100  # golden yellow
    assert 230 <= hex_to_lab("#0057b8").hue_deg <= 300  # royal blue


def test_hue_distance_wraps():
    assert hue_distance_deg(350, 10) == 20
    assert hue_distance_deg(0, 180) == 180
