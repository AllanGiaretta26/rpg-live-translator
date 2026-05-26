from __future__ import annotations

import pytest

from domain.models import TextRegion
from infrastructure.capture.mss_screen_capture import MSSScreenCapture


class FakeScreenshot:
    size = (2, 1)
    rgb = bytes([255, 0, 0, 0, 255, 0])


class FakeMSS:
    def __init__(self):
        self.monitors: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def grab(self, monitor):
        self.monitors.append(monitor)
        return FakeScreenshot()


def test_mss_screen_capture_captures_region_by_coordinates():
    fake = FakeMSS()
    capture = MSSScreenCapture(mss_factory=lambda: fake)

    image = capture.capture_region(TextRegion(x=1, y=2, width=3, height=4))

    assert fake.monitors == [{"left": 1, "top": 2, "width": 3, "height": 4}]
    assert image.size == (2, 1)


def test_mss_screen_capture_rejects_invalid_region():
    capture = MSSScreenCapture(mss_factory=FakeMSS)

    with pytest.raises(ValueError, match="width"):
        capture.capture_region(TextRegion(x=1, y=2, width=0, height=4))
