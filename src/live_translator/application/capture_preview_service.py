from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from live_translator.domain.interfaces import ScreenCapture
from live_translator.domain.models import TextRegion


class SavableImage(Protocol):
    def save(self, path: str | Path) -> None:
        """Persist the image to disk."""


@dataclass(frozen=True, slots=True)
class CapturePreviewService:
    screen_capture: ScreenCapture
    preview_path: Path

    def capture_preview(
        self,
        *,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Path:
        region = TextRegion(x=x, y=y, width=width, height=height)
        image = self.screen_capture.capture_region(region)
        if not hasattr(image, "save"):
            raise RuntimeError("captured image cannot be saved")

        self.preview_path.parent.mkdir(parents=True, exist_ok=True)
        savable = cast(SavableImage, image)
        savable.save(self.preview_path)
        return self.preview_path
