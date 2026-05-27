from __future__ import annotations

import pytest

from live_translator.domain.models import TextRegion
from live_translator.ui.region_selector_window import (
    normalize_region,
    region_from_local_points,
)
from live_translator.ui.screen_geometry import ScreenRect


def test_normalize_region_from_top_left_to_bottom_right():
    assert normalize_region(10, 20, 110, 70) == TextRegion(
        x=10,
        y=20,
        width=100,
        height=50,
    )


def test_normalize_region_from_bottom_right_to_top_left():
    assert normalize_region(110, 70, 10, 20) == TextRegion(
        x=10,
        y=20,
        width=100,
        height=50,
    )


def test_normalize_region_rejects_empty_selection():
    with pytest.raises(ValueError, match="width must be greater than zero"):
        normalize_region(10, 20, 10, 70)


def test_region_from_local_points_uses_screen_origin_and_scale():
    screen = ScreenRect(x=100, y=200, width=1280, height=720, scale=1.25)

    assert region_from_local_points(700, 350, 1100, 470, screen) == TextRegion(
        x=975,
        y=638,
        width=500,
        height=150,
    )


def test_region_from_local_points_normalizes_reverse_drag():
    screen = ScreenRect(x=0, y=0, width=1920, height=1080, scale=1.5)

    assert region_from_local_points(900, 700, 700, 600, screen) == TextRegion(
        x=1050,
        y=900,
        width=300,
        height=150,
    )
