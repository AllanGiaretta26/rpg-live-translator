from __future__ import annotations

from dataclasses import dataclass

from live_translator.domain.interfaces import SettingsRepository
from live_translator.domain.models import OverlayPlacement


OVERLAY_SETTING_PREFIX = "overlay"


@dataclass(frozen=True, slots=True)
class OverlaySettingsService:
    settings_repository: SettingsRepository
    default_placement: OverlayPlacement

    def get_placement(self) -> OverlayPlacement:
        values = {
            "x": self._get_int("x", self.default_placement.x),
            "y": self._get_int("y", self.default_placement.y),
            "width": self._get_int("width", self.default_placement.width),
            "height": self._get_int("height", self.default_placement.height),
            "opacity": self._get_float("opacity", self.default_placement.opacity),
            "font_size": self._get_int(
                "font_size",
                self.default_placement.font_size,
            ),
        }
        try:
            return OverlayPlacement(**values)
        except ValueError:
            return self.default_placement

    def save_placement(self, placement: OverlayPlacement) -> None:
        self.settings_repository.set(self._key("x"), str(placement.x))
        self.settings_repository.set(self._key("y"), str(placement.y))
        self.settings_repository.set(self._key("width"), str(placement.width))
        self.settings_repository.set(self._key("height"), str(placement.height))
        self.settings_repository.set(self._key("opacity"), str(placement.opacity))
        self.settings_repository.set(self._key("font_size"), str(placement.font_size))

    def _get_int(self, name: str, default: int) -> int:
        value = self.settings_repository.get(self._key(name))
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _get_float(self, name: str, default: float) -> float:
        value = self.settings_repository.get(self._key(name))
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _key(self, name: str) -> str:
        return f"{OVERLAY_SETTING_PREFIX}.{name}"
