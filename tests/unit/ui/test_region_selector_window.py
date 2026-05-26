from __future__ import annotations

import pytest

from live_translator.domain.models import TextRegion
from live_translator.ui.region_selector_window import normalize_region


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
