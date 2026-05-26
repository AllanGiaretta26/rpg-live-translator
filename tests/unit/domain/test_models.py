from __future__ import annotations

import pytest

from live_translator.domain.models import OverlayPlacement


def test_overlay_placement_accepts_valid_values():
    placement = OverlayPlacement(
        x=10,
        y=20,
        width=900,
        height=120,
        opacity=0.8,
        font_size=24,
    )

    assert placement.width == 900
    assert placement.opacity == 0.8


def test_overlay_placement_rejects_invalid_size():
    with pytest.raises(ValueError, match="width must be greater than zero"):
        OverlayPlacement(x=0, y=0, width=0, height=120)


def test_overlay_placement_rejects_invalid_opacity():
    with pytest.raises(ValueError, match="opacity"):
        OverlayPlacement(x=0, y=0, width=900, height=120, opacity=1.5)
