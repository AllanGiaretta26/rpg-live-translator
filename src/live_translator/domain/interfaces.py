from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from .models import (
    CatalogTranslationError,
    ExtractedText,
    GameProfile,
    RpgMakerProject,
    RpgMakerTextEntry,
    RpgMakerTextType,
    TextRegion,
    TranslationResult,
)


class ScreenCapture(Protocol):
    def capture_region(self, region: TextRegion) -> object:
        """Capture and return an image-like object for the given region."""


class TextExtractor(Protocol):
    def extract(self, image: object) -> ExtractedText:
        """Extract source text from an image-like object."""


class Translator(Protocol):
    def translate(
        self,
        text: str,
        context: Sequence[str],
        *,
        text_type: RpgMakerTextType | None = None,
    ) -> TranslationResult:
        """Translate source text using optional short context history."""


class TranslationCache(Protocol):
    def get_by_text(
        self,
        source_text: str,
        *,
        scope: str | None = None,
    ) -> TranslationResult | None:
        """Return cached translation by normalized source text."""

    def get_many_by_text(
        self,
        texts: Sequence[str],
        *,
        scope: str | None = None,
    ) -> dict[str, TranslationResult]:
        """Return cached translations for many texts in a single lookup.

        The returned mapping is keyed by the original input text and omits any
        text without a cached translation.
        """

    def save_translation(
        self,
        result: TranslationResult,
        *,
        scope: str | None = None,
    ) -> None:
        """Store a translation result in cache."""

    def delete_by_text(
        self,
        source_text: str,
        *,
        scope: str | None = None,
    ) -> bool:
        """Remove a cached translation by normalized source text."""


class ImageCache(Protocol):
    def get_by_hash(self, image_hash: str) -> TranslationResult | None:
        """Return cached translation associated with an image hash."""

    def save_image_result(self, image_hash: str, result: TranslationResult) -> None:
        """Store mapping from image hash to translation result."""


class ImageHasher(Protocol):
    def hash_image(self, image: object) -> str:
        """Return a stable hash for an image-like object."""


class ImageChangeDetector(Protocol):
    def has_changed(self, image: object) -> bool:
        """Return whether an image differs enough from the previous frame."""


class TextNormalizer(Protocol):
    def normalize(self, text: str) -> str:
        """Normalize extracted text before cache lookup and translation."""


class OverlayRenderer(Protocol):
    def show_text(self, text: str) -> None:
        """Render text in overlay."""

    def hide(self) -> None:
        """Hide overlay."""


class GameProfileRepository(Protocol):
    def get_active_profile(self) -> GameProfile | None:
        """Return the active profile when available."""

    def save(self, profile: GameProfile) -> None:
        """Create or update a game profile."""


class SettingsRepository(Protocol):
    def get(self, key: str) -> str | None:
        """Return the stored value for a settings key."""

    def set(self, key: str, value: str) -> None:
        """Store or replace a settings value."""

    def delete(self, key: str) -> None:
        """Remove a settings entry when it exists."""


class RpgMakerProjectDetector(Protocol):
    def detect(self, path: str | Path) -> RpgMakerProject:
        """Detect an RPG Maker MV/MZ project from a root or data path."""


class RpgMakerTextParser(Protocol):
    def parse_project(self, project: RpgMakerProject) -> list[RpgMakerTextEntry]:
        """Return text entries extracted from an RPG Maker MV/MZ project."""


class RpgMakerTextCatalog(Protocol):
    def replace_project_entries(
        self,
        project: RpgMakerProject,
        entries: Sequence[RpgMakerTextEntry],
    ) -> int:
        """Replace all catalog entries for a project and return the saved count."""

    def count_project_entries(self, project: RpgMakerProject) -> int:
        """Return the number of catalog entries stored for a project."""

    def list_project_entries(
        self,
        project: RpgMakerProject,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RpgMakerTextEntry]:
        """Return catalog entries stored for a project."""

    def get_entry(self, entry_id: int) -> RpgMakerTextEntry | None:
        """Return one catalog entry by identifier."""


class CatalogTranslationErrorRepository(Protocol):
    def clear_last_batch_errors(self) -> None:
        """Remove stored errors from the previous catalog batch."""

    def save_error(self, error: CatalogTranslationError) -> None:
        """Store one catalog batch translation error."""

    def list_last_batch_errors(self) -> list[CatalogTranslationError]:
        """Return stored errors from the most recent catalog batch."""
