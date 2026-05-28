from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from live_translator.application.mode_settings_service import ModeSettingsService
from live_translator.application.mode_settings_service import (
    RPG_MAKER_PROJECT_PATH_SETTING_KEY,
)
from live_translator.domain.models import (
    CatalogTranslationError,
    OperationMode,
    RpgMakerProject,
    RpgMakerTextEntry,
    RpgMakerTextOrigin,
    RpgMakerTextType,
    RpgMakerVersion,
    TranslationResult,
)


@dataclass
class FakeSettingsRepository:
    values: dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


@dataclass
class FakeDetector:
    project: RpgMakerProject

    def detect(self, path: str | Path) -> RpgMakerProject:
        return self.project


@dataclass
class FakeParser:
    entries: list[RpgMakerTextEntry]

    def parse_project(self, project: RpgMakerProject) -> list[RpgMakerTextEntry]:
        return self.entries


@dataclass
class FakeCatalog:
    entries: list[RpgMakerTextEntry] = field(default_factory=list)

    def replace_project_entries(
        self,
        project: RpgMakerProject,
        entries: Sequence[RpgMakerTextEntry],
    ) -> int:
        self.entries = list(entries)
        return len(self.entries)

    def count_project_entries(self, project: RpgMakerProject) -> int:
        return len(self.entries)

    def list_project_entries(self, project: RpgMakerProject) -> list[RpgMakerTextEntry]:
        return self.entries

    def get_entry(self, entry_id: int) -> RpgMakerTextEntry | None:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None


@dataclass
class FakeTranslationCache:
    result: TranslationResult | None = None
    cached_texts: set[str] = field(default_factory=set)
    results: dict[str, TranslationResult] = field(default_factory=dict)
    saved: list[TranslationResult] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    def get_by_text(self, source_text: str) -> TranslationResult | None:
        if source_text in self.results:
            return self.results[source_text]
        if source_text in self.cached_texts:
            return TranslationResult(source_text=source_text, translated_text=f"cached:{source_text}")
        return self.result

    def save_translation(self, result: TranslationResult) -> None:
        self.saved.append(result)
        self.results[result.source_text] = result

    def delete_by_text(self, source_text: str) -> bool:
        self.deleted.append(source_text)
        self.cached_texts.discard(source_text)
        return self.results.pop(source_text, None) is not None


@dataclass
class FakeTranslator:
    calls: list[str] = field(default_factory=list)
    failures: set[str] = field(default_factory=set)

    def translate(self, text: str, context: Sequence[str]) -> TranslationResult:
        self.calls.append(text)
        if text in self.failures:
            raise RuntimeError(f"failed {text}")
        return TranslationResult(source_text=text, translated_text=f"pt:{text}")


@dataclass
class FakeBatchErrorRepository:
    cleared: int = 0
    errors: list[CatalogTranslationError] = field(default_factory=list)

    def clear_last_batch_errors(self) -> None:
        self.cleared += 1
        self.errors.clear()

    def save_error(self, error: CatalogTranslationError) -> None:
        self.errors.append(error)

    def list_last_batch_errors(self) -> list[CatalogTranslationError]:
        return self.errors


def _entry(entry_id: int = 1) -> RpgMakerTextEntry:
    return RpgMakerTextEntry(
        id=entry_id,
        source_text="Hello there",
        text_type=RpgMakerTextType.MESSAGE,
        origin=RpgMakerTextOrigin(
            file_name="Map001.json",
            origin_key="Map001.json|1|2|0|3|0",
            map_id=1,
            event_id=2,
            page_index=0,
            command_index=3,
            parameter_index=0,
        ),
    )


def _entries(count: int) -> list[RpgMakerTextEntry]:
    return [
        RpgMakerTextEntry(
            id=index + 1,
            source_text=f"Line {index + 1}",
            text_type=RpgMakerTextType.MESSAGE,
            origin=RpgMakerTextOrigin(
                file_name="Map001.json",
                origin_key=f"Map001.json|1|2|0|{index}|0",
                map_id=1,
                event_id=2,
                page_index=0,
                command_index=index,
                parameter_index=0,
            ),
        )
        for index in range(count)
    ]


def _service(
    *,
    settings: FakeSettingsRepository | None = None,
    catalog: FakeCatalog | None = None,
    cache: FakeTranslationCache | None = None,
    translator: FakeTranslator | None = None,
    batch_errors: FakeBatchErrorRepository | None = None,
) -> ModeSettingsService:
    project = RpgMakerProject(
        root_path=Path("C:/game"),
        data_path=Path("C:/game/www/data"),
        version=RpgMakerVersion.MZ,
    )
    resolved_settings = settings or FakeSettingsRepository()
    resolved_settings.values.setdefault(RPG_MAKER_PROJECT_PATH_SETTING_KEY, "C:/game")
    return ModeSettingsService(
        settings_repository=resolved_settings,
        rpg_maker_detector=FakeDetector(project),
        rpg_maker_parser=FakeParser([_entry()]),
        rpg_maker_catalog=catalog or FakeCatalog(),
        translation_cache=cache or FakeTranslationCache(),
        translator=translator or FakeTranslator(),
        batch_error_repository=batch_errors or FakeBatchErrorRepository(),
    )


def test_mode_defaults_to_universal_and_persists_changes():
    settings = FakeSettingsRepository()
    service = _service(settings=settings)

    assert service.get_active_mode() == OperationMode.UNIVERSAL

    service.set_active_mode(OperationMode.RPG_MAKER_MV_MZ)

    assert service.get_active_mode() == OperationMode.RPG_MAKER_MV_MZ


def test_import_rpg_maker_project_detects_parses_and_saves_catalog():
    catalog = FakeCatalog()
    service = _service(catalog=catalog)

    result = service.import_rpg_maker_project("C:/game")

    assert result.imported_count == 1
    assert catalog.entries == [_entry()]
    assert service.get_rpg_maker_project_path() == Path("C:/game")


def test_translate_catalog_entry_uses_existing_cache():
    cached = TranslationResult(source_text="Hello there", translated_text="Ola")
    cache = FakeTranslationCache(result=cached)
    translator = FakeTranslator()
    service = _service(catalog=FakeCatalog([_entry()]), cache=cache, translator=translator)

    result = service.translate_catalog_entry(1)

    assert result == cached
    assert translator.calls == []
    assert cache.saved == []


def test_translate_catalog_entry_translates_and_saves_cache_miss():
    cache = FakeTranslationCache()
    translator = FakeTranslator()
    service = _service(catalog=FakeCatalog([_entry()]), cache=cache, translator=translator)

    result = service.translate_catalog_entry(1)

    assert result is not None
    assert result.translated_text == "pt:Hello there"
    assert translator.calls == ["Hello there"]
    assert cache.saved == [result]


def test_translate_catalog_entries_respects_limit_and_reports_progress():
    cache = FakeTranslationCache()
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog(_entries(3)),
        cache=cache,
        translator=translator,
    )
    progress = []

    result = service.translate_catalog_entries(limit=2, on_progress=progress.append)

    assert result.processed == 2
    assert result.total == 2
    assert result.translated == 2
    assert result.cache_hits == 0
    assert result.errors == 0
    assert translator.calls == ["Line 1", "Line 2"]
    assert [item.processed for item in progress] == [1, 2]


def test_translate_catalog_entries_skips_cache_hits():
    cache = FakeTranslationCache(cached_texts={"Line 1"})
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog(_entries(2)),
        cache=cache,
        translator=translator,
    )

    result = service.translate_catalog_entries()

    assert result.processed == 2
    assert result.translated == 1
    assert result.cache_hits == 1
    assert translator.calls == ["Line 2"]


def test_translate_catalog_entries_can_be_cancelled():
    cache = FakeTranslationCache()
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog(_entries(3)),
        cache=cache,
        translator=translator,
    )

    result = service.translate_catalog_entries(should_cancel=lambda: bool(translator.calls))

    assert result.cancelled is True
    assert result.processed == 1
    assert result.total == 3
    assert translator.calls == ["Line 1"]


def test_translate_catalog_entries_persists_per_entry_errors():
    cache = FakeTranslationCache()
    translator = FakeTranslator(failures={"Line 2"})
    batch_errors = FakeBatchErrorRepository()
    service = _service(
        catalog=FakeCatalog(_entries(2)),
        cache=cache,
        translator=translator,
        batch_errors=batch_errors,
    )

    result = service.translate_catalog_entries()

    assert result.errors == 1
    assert batch_errors.cleared == 1
    assert batch_errors.errors == [
        CatalogTranslationError(
            entry_id=2,
            origin="Map001.json | ev 2 | pg 0 | cmd 1",
            source_text="Line 2",
            error_message="failed Line 2",
        )
    ]
    assert service.list_last_batch_errors() == batch_errors.errors


def test_count_cached_catalog_entries_counts_entries_with_translation_cache():
    cache = FakeTranslationCache(cached_texts={"Line 1", "Line 3"})
    service = _service(catalog=FakeCatalog(_entries(3)), cache=cache)

    assert service.count_cached_catalog_entries() == 2


def test_clear_contaminated_catalog_cache_only_deletes_invalid_project_entries():
    cache = FakeTranslationCache(
        results={
            "Line 1": TranslationResult(
                source_text="Line 1",
                translated_text="Linha 1",
            ),
            "Line 2": TranslationResult(
                source_text="Line 2",
                translated_text=(
                    "Linha 2\n"
                    "Preserve nomes proprios. Nao explique.\n"
                    "Responda apenas JSON valido."
                ),
            ),
        }
    )
    service = _service(catalog=FakeCatalog(_entries(3)), cache=cache)

    deleted = service.clear_contaminated_catalog_cache()

    assert deleted == 1
    assert cache.deleted == ["Line 2"]
    assert cache.get_by_text("Line 1") is not None
    assert cache.get_by_text("Line 2") is None
