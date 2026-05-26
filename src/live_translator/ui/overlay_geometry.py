from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResizeHandle(str, Enum):
    MOVE = "move"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass(frozen=True, slots=True)
class WindowGeometry:
    x: int
    y: int
    width: int
    height: int


def detect_resize_handle(
    local_x: int,
    local_y: int,
    width: int,
    height: int,
    margin: int = 14,
) -> ResizeHandle:
    near_left = local_x <= margin
    near_right = width - local_x <= margin
    near_top = local_y <= margin
    near_bottom = height - local_y <= margin

    if near_top and near_left:
        return ResizeHandle.TOP_LEFT
    if near_top and near_right:
        return ResizeHandle.TOP_RIGHT
    if near_bottom and near_left:
        return ResizeHandle.BOTTOM_LEFT
    if near_bottom and near_right:
        return ResizeHandle.BOTTOM_RIGHT
    if near_left:
        return ResizeHandle.LEFT
    if near_right:
        return ResizeHandle.RIGHT
    if near_top:
        return ResizeHandle.TOP
    if near_bottom:
        return ResizeHandle.BOTTOM
    return ResizeHandle.MOVE


def resize_geometry(
    geometry: WindowGeometry,
    handle: ResizeHandle,
    *,
    delta_x: int,
    delta_y: int,
    min_width: int = 160,
    min_height: int = 60,
) -> WindowGeometry:
    x = geometry.x
    y = geometry.y
    width = geometry.width
    height = geometry.height

    if handle in {
        ResizeHandle.LEFT,
        ResizeHandle.TOP_LEFT,
        ResizeHandle.BOTTOM_LEFT,
    }:
        requested_width = width - delta_x
        width = max(min_width, requested_width)
        x = x + (geometry.width - width)
    elif handle in {
        ResizeHandle.RIGHT,
        ResizeHandle.TOP_RIGHT,
        ResizeHandle.BOTTOM_RIGHT,
    }:
        width = max(min_width, width + delta_x)

    if handle in {
        ResizeHandle.TOP,
        ResizeHandle.TOP_LEFT,
        ResizeHandle.TOP_RIGHT,
    }:
        requested_height = height - delta_y
        height = max(min_height, requested_height)
        y = y + (geometry.height - height)
    elif handle in {
        ResizeHandle.BOTTOM,
        ResizeHandle.BOTTOM_LEFT,
        ResizeHandle.BOTTOM_RIGHT,
    }:
        height = max(min_height, height + delta_y)

    return WindowGeometry(x=x, y=y, width=width, height=height)
