from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScreenRect:
    x: int
    y: int
    width: int
    height: int


def select_screen_for_point(
    point_x: int,
    point_y: int,
    screens: Sequence[ScreenRect],
) -> ScreenRect:
    if not screens:
        raise ValueError("at least one screen is required")

    for screen in screens:
        if (
            screen.x <= point_x < screen.x + screen.width
            and screen.y <= point_y < screen.y + screen.height
        ):
            return screen
    return screens[0]
