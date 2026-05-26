from __future__ import annotations

from dataclasses import dataclass

import pytest

from live_translator.infrastructure.image.image_change_detector import ImageChangeDetector


@dataclass
class StubImage:
    hash_value: str


def test_change_detector_skips_repeated_frames_after_baseline():
    detector = ImageChangeDetector(hasher=lambda image: image.hash_value)
    image = StubImage(hash_value="0000000000000000")

    assert detector.has_changed(image) is True
    assert detector.has_changed(StubImage(hash_value="0000000000000000")) is False


def test_change_detector_uses_configurable_threshold():
    detector = ImageChangeDetector(threshold=1, hasher=lambda image: image.hash_value)

    assert detector.has_changed(StubImage(hash_value="0000000000000000")) is True
    assert detector.has_changed(StubImage(hash_value="0000000000000001")) is False
    assert detector.has_changed(StubImage(hash_value="0000000000000007")) is True


def test_change_detector_rejects_negative_threshold():
    with pytest.raises(ValueError, match="threshold"):
        ImageChangeDetector(threshold=-1)
