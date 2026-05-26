from __future__ import annotations

from dataclasses import dataclass

from live_translator.domain.interfaces import GameProfileRepository
from live_translator.domain.models import GameProfile, TextRegion


@dataclass(frozen=True, slots=True)
class ProfileSettingsService:
    profile_repository: GameProfileRepository

    def get_active_profile(self) -> GameProfile | None:
        return self.profile_repository.get_active_profile()

    def save_profile(
        self,
        *,
        name: str,
        window_title: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> GameProfile:
        profile = GameProfile(
            name=name,
            window_title=window_title,
            text_region=TextRegion(x=x, y=y, width=width, height=height),
        )
        self.profile_repository.save(profile)
        return profile
