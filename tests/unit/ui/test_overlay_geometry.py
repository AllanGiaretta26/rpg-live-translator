from live_translator.ui.overlay_geometry import (
    ResizeHandle,
    WindowGeometry,
    detect_resize_handle,
    resize_geometry,
)


def test_detects_corner_resize_handle():
    assert detect_resize_handle(398, 118, 400, 120) == ResizeHandle.BOTTOM_RIGHT


def test_detects_left_edge_resize_handle():
    assert detect_resize_handle(2, 60, 400, 120) == ResizeHandle.LEFT


def test_detects_move_area_when_not_on_resize_handle():
    assert detect_resize_handle(200, 60, 400, 120) == ResizeHandle.MOVE


def test_resize_from_right_edge_changes_width():
    geometry = WindowGeometry(x=100, y=100, width=400, height=120)

    resized = resize_geometry(geometry, ResizeHandle.RIGHT, delta_x=50, delta_y=0)

    assert resized == WindowGeometry(x=100, y=100, width=450, height=120)


def test_resize_from_left_edge_moves_x_and_changes_width():
    geometry = WindowGeometry(x=100, y=100, width=400, height=120)

    resized = resize_geometry(geometry, ResizeHandle.LEFT, delta_x=50, delta_y=0)

    assert resized == WindowGeometry(x=150, y=100, width=350, height=120)


def test_resize_respects_minimum_size():
    geometry = WindowGeometry(x=100, y=100, width=180, height=70)

    resized = resize_geometry(geometry, ResizeHandle.TOP_LEFT, delta_x=100, delta_y=80)

    assert resized.width == 160
    assert resized.height == 60
