from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from live_translator.domain.interfaces import ScreenCapture
from live_translator.domain.models import TextRegion


def _validate_region(region: TextRegion) -> None:
    if region.x < 0 or region.y < 0:
        raise ValueError("capture region coordinates must be zero or greater")
    if region.width <= 0 or region.height <= 0:
        raise ValueError("capture region size must be greater than zero")


@dataclass(frozen=True, slots=True)
class MSSScreenCapture(ScreenCapture):
    mss_factory: Callable[[], Any] | None = None

    def capture_region(self, region: TextRegion) -> object:
        _validate_region(region)
        mss_factory = self.mss_factory
        if mss_factory is None:
            from mss import mss as mss_factory

        monitor = {
            "left": region.x,
            "top": region.y,
            "width": region.width,
            "height": region.height,
        }
        with mss_factory() as screen_capture:
            screenshot = screen_capture.grab(monitor)

        from PIL import Image

        return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
