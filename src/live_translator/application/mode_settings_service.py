from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from live_translator.domain.interfaces import (
    RpgMakerProjectDetector,
    RpgMakerTextCatalog,
    RpgMakerTextParser,
    SettingsRepository,
    TranslationCache,
    Translator,
)
from live_translator.domain.models import (
    OperationMode,
    RpgMakerImportResult,
    RpgMakerTextEntry,
    TranslationResult,
)


ACTIVE_MODE_SETTING_KEY = "operation.active_mode"
RPG_MAKER_PROJECT_PATH_SETTING_KEY = "rpg_maker.project_path"


@dataclass(frozen=True, slots=True)
class ModeSettingsService:
    settings_repository: SettingsRepository
    rpg_maker_detector: RpgMakerProjectDetector
    rpg_maker_parser: RpgMakerTextParser
    rpg_maker_catalog: RpgMakerTextCatalog
    translation_cache: TranslationCache
    translator: Translator

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

    def list_rpg_maker_entries(self) -> list[RpgMakerTextEntry]:
        project_path = self.get_rpg_maker_project_path()
        if project_path is None:
            return []

        project = self.rpg_maker_detector.detect(project_path)
        return self.rpg_maker_catalog.list_project_entries(project)
