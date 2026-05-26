import pytest

from live_translator.ui.screen_geometry import ScreenRect, select_screen_for_point


def test_selects_screen_containing_point():
    screens = (
        ScreenRect(x=0, y=0, width=1920, height=1080),
        ScreenRect(x=1920, y=0, width=1920, height=1080),
    )

    assert select_screen_for_point(2000, 500, screens) == screens[1]


def test_uses_first_screen_as_fallback():
    screens = (
        ScreenRect(x=0, y=0, width=1920, height=1080),
        ScreenRect(x=1920, y=0, width=1920, height=1080),
    )

    assert select_screen_for_point(-500, -500, screens) == screens[0]


def test_rejects_empty_screen_list():
    with pytest.raises(ValueError, match="at least one screen is required"):
        select_screen_for_point(0, 0, ())
