from __future__ import annotations

from dataclasses import dataclass, field

from live_translator.application.overlay_settings_service import OverlaySettingsService
from live_translator.domain.models import OverlayPlacement


@dataclass
class FakeSettingsRepository:
    values: dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


def test_overlay_settings_returns_default_when_missing():
    default = OverlayPlacement(x=100, y=200, width=900, height=120)
    service = OverlaySettingsService(FakeSettingsRepository(), default)

    assert service.get_placement() == default


def test_overlay_settings_saves_and_loads_placement():
    repository = FakeSettingsRepository()
    service = OverlaySettingsService(
        repository,
        OverlayPlacement(x=0, y=0, width=900, height=120),
    )
    placement = OverlayPlacement(
        x=10,
        y=20,
        width=700,
        height=140,
        opacity=0.7,
        font_size=28,
    )

    service.save_placement(placement)

    assert service.get_placement() == placement
    assert repository.values["overlay.x"] == "10"
    assert repository.values["overlay.opacity"] == "0.7"


def test_overlay_settings_falls_back_when_saved_values_are_invalid():
    default = OverlayPlacement(x=100, y=200, width=900, height=120)
    repository = FakeSettingsRepository({"overlay.width": "0"})
    service = OverlaySettingsService(repository, default)

    assert service.get_placement() == default
