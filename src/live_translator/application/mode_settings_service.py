from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from live_translator.domain.interfaces import (
    CatalogTranslationErrorRepository,
    RpgMakerProjectDetector,
    RpgMakerTextCatalog,
    RpgMakerTextParser,
    SettingsRepository,
    TranslationCache,
    Translator,
)
from live_translator.domain.models import (
    CatalogTranslationError,
    OperationMode,
    RpgMakerImportResult,
    RpgMakerTextEntry,
    TranslationResult,
)

from .translation_quality import looks_like_invalid_translation


ACTIVE_MODE_SETTING_KEY = "operation.active_mode"
RPG_MAKER_PROJECT_PATH_SETTING_KEY = "rpg_maker.project_path"


@dataclass(frozen=True, slots=True)
class CatalogTranslationProgress:
    total: int
    processed: int
    translated: int
    cache_hits: int
    errors: int
    cancelled: bool = False
    current_text: str = ""


@dataclass(frozen=True, slots=True)
class CatalogTranslationResult:
    total: int
    processed: int
    translated: int
    cache_hits: int
    errors: int
    cancelled: bool = False


ProgressCallback = Callable[[CatalogTranslationProgress], None]
CancelChecker = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class ModeSettingsService:
    settings_repository: SettingsRepository
    rpg_maker_detector: RpgMakerProjectDetector
    rpg_maker_parser: RpgMakerTextParser
    rpg_maker_catalog: RpgMakerTextCatalog
    translation_cache: TranslationCache
    translator: Translator
    batch_error_repository: CatalogTranslationErrorRepository

    def get_active_mode(self) -> OperationMode:
        raw_value = self.settings_repository.get(ACTIVE_MODE_SETTING_KEY)
        if raw_value is None:
            return OperationMode.UNIVERSAL

        try:
            return OperationMode(raw_value)
        except ValueError:
            return OperationMode.UNIVERSAL

    def set_active_mode(self, mode: OperationMode) -> None:
        self.settings_repository.set(ACTIVE_MODE_SETTING_KEY, mode.value)

    def get_rpg_maker_project_path(self) -> Path | None:
        raw_value = self.settings_repository.get(RPG_MAKER_PROJECT_PATH_SETTING_KEY)
        if raw_value is None or not raw_value.strip():
            return None
        return Path(raw_value)

    def set_rpg_maker_project_path(self, path: str | Path | None) -> None:
        if path is None or not str(path).strip():
            self.settings_repository.delete(RPG_MAKER_PROJECT_PATH_SETTING_KEY)
            return

        self.settings_repository.set(
            RPG_MAKER_PROJECT_PATH_SETTING_KEY,
            str(Path(path)),
        )

    def import_rpg_maker_project(self, path: str | Path) -> RpgMakerImportResult:
        project = self.rpg_maker_detector.detect(path)
        entries = self.rpg_maker_parser.parse_project(project)
        imported_count = self.rpg_maker_catalog.replace_project_entries(
            project,
            entries,
        )
        self.set_rpg_maker_project_path(project.root_path)
        return RpgMakerImportResult(project=project, imported_count=imported_count)

    def translate_catalog_entry(self, entry_id: int) -> TranslationResult | None:
        entry = self.rpg_maker_catalog.get_entry(entry_id)
        if entry is None:
            return None

        cached = self.translation_cache.get_by_text(entry.source_text)
        if cached is not None:
            return cached

        result = self.translator.translate(entry.source_text, [])
        self.translation_cache.save_translation(result)
        return result

    def translate_catalog_entries(
        self,
        *,
        limit: int | None = None,
        on_progress: ProgressCallback | None = None,
        should_cancel: CancelChecker | None = None,
    ) -> CatalogTranslationResult:
        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than zero")

        entries = self.list_rpg_maker_entries()
        if limit is not None:
            entries = entries[:limit]

        total = len(entries)
        translated = 0
        cache_hits = 0
        errors = 0
        processed = 0
        cancelled = False
        self.batch_error_repository.clear_last_batch_errors()

        for entry in entries:
            if should_cancel is not None and should_cancel():
                cancelled = True
                break

            try:
                cached = self.translation_cache.get_by_text(entry.source_text)
                if cached is not None:
                    cache_hits += 1
                else:
                    result = self.translator.translate(entry.source_text, [])
                    self.translation_cache.save_translation(result)
                    translated += 1
            except Exception as error:
                errors += 1
                self.batch_error_repository.save_error(
                    CatalogTranslationError(
                        entry_id=entry.id,
                        origin=_format_entry_origin(entry),
                        source_text=entry.source_text,
                        error_message=str(error),
                    )
                )
            finally:
                processed += 1
                if on_progress is not None:
                    on_progress(
                        CatalogTranslationProgress(
                            total=total,
                            processed=processed,
                            translated=translated,
                            cache_hits=cache_hits,
                            errors=errors,
                            cancelled=cancelled,
                            current_text=entry.source_text,
                        )
                    )

        return CatalogTranslationResult(
            total=total,
            processed=processed,
            translated=translated,
            cache_hits=cache_hits,
            errors=errors,
            cancelled=cancelled,
        )

    def list_rpg_maker_entries(self) -> list[RpgMakerTextEntry]:
        project_path = self.get_rpg_maker_project_path()
        if project_path is None:
            return []

        project = self.rpg_maker_detector.detect(project_path)
        return self.rpg_maker_catalog.list_project_entries(project)

    def count_cached_catalog_entries(self) -> int:
        count = 0
        for entry in self.list_rpg_maker_entries():
            if self.translation_cache.get_by_text(entry.source_text) is not None:
                count += 1
        return count

    def clear_contaminated_catalog_cache(self) -> int:
        deleted = 0
        for entry in self.list_rpg_maker_entries():
            cached = self.translation_cache.get_by_text(entry.source_text)
            if cached is None:
                continue
            if not looks_like_invalid_translation(entry.source_text, cached.translated_text):
                continue
            if self.translation_cache.delete_by_text(entry.source_text):
                deleted += 1
        return deleted

    def list_last_batch_errors(self) -> list[CatalogTranslationError]:
        return self.batch_error_repository.list_last_batch_errors()


def _format_entry_origin(entry: RpgMakerTextEntry) -> str:
    origin = entry.origin
    parts = [origin.file_name]
    if origin.event_id is not None:
        parts.append(f"ev {origin.event_id}")
    if origin.page_index is not None:
        parts.append(f"pg {origin.page_index}")
    if origin.command_index is not None:
        parts.append(f"cmd {origin.command_index}")
    return " | ".join(parts)
