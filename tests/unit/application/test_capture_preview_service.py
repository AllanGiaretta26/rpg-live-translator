from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from live_translator.application.capture_preview_service import CapturePreviewService
from live_translator.domain.models import TextRegion


@dataclass
class FakeImage:
    saved_path: Path | None = None

    def save(self, path: str | Path) -> None:
        self.saved_path = Path(path)
        self.saved_path.write_bytes(b"preview")


class FakeScreenCapture:
    def __init__(self) -> None:
        self.calls: list[TextRegion] = []
        self.image = FakeImage()

    def capture_region(self, region: TextRegion) -> FakeImage:
        self.calls.append(region)
        return self.image


class UnsavableScreenCapture:
    def capture_region(self, region: TextRegion) -> object:
        return object()


def test_capture_preview_saves_region_image(tmp_path):
    capture = FakeScreenCapture()
    output = tmp_path / "nested" / "preview.png"
    service = CapturePreviewService(capture, output)

    result = service.capture_preview(x=10, y=20, width=300, height=120)

    assert result == output
    assert output.read_bytes() == b"preview"
    assert capture.image.saved_path == output
    assert capture.calls == [TextRegion(x=10, y=20, width=300, height=120)]


def test_capture_preview_rejects_invalid_region(tmp_path):
    capture = FakeScreenCapture()
    service = CapturePreviewService(capture, tmp_path / "preview.png")

    with pytest.raises(ValueError, match="width must be greater than zero"):
        service.capture_preview(x=10, y=20, width=0, height=120)

    assert capture.calls == []


def test_capture_preview_requires_savable_image(tmp_path):
    service = CapturePreviewService(
        UnsavableScreenCapture(),
        tmp_path / "preview.png",
    )

    with pytest.raises(RuntimeError, match="cannot be saved"):
        service.capture_preview(x=10, y=20, width=300, height=120)
