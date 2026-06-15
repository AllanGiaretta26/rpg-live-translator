from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import pytest

from live_translator.application.mode_settings_service import ModeSettingsService
from live_translator.application.mode_settings_service import (
    DEFAULT_CATALOG_TRANSLATION_TYPES,
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
    calls: int = 0
    error: Exception | None = None

    def detect(self, path: str | Path) -> RpgMakerProject:
        self.calls += 1
        if self.error is not None:
            raise self.error
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

    def list_project_entries(
        self,
        project: RpgMakerProject,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RpgMakerTextEntry]:
        entries = self.entries[offset:]
        if limit is not None:
            return entries[:limit]
        return entries

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
    scoped_results: dict[tuple[str, str], TranslationResult] = field(
        default_factory=dict
    )
    saved: list[TranslationResult] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    saved_scopes: list[str | None] = field(default_factory=list)
    deleted_scopes: list[str | None] = field(default_factory=list)

    def get_by_text(
        self,
        source_text: str,
        *,
        scope: str | None = None,
    ) -> TranslationResult | None:
        scoped = self.scoped_results.get((scope or "", source_text))
        if scoped is not None:
            return scoped
        if source_text in self.results:
            return self.results[source_text]
        if source_text in self.cached_texts:
            return TranslationResult(
                source_text=source_text, translated_text=f"cached:{source_text}"
            )
        return self.result

    def get_many_by_text(
        self,
        texts,
        *,
        scope: str | None = None,
    ) -> dict[str, TranslationResult]:
        found: dict[str, TranslationResult] = {}
        for text in texts:
            cached = self.get_by_text(text, scope=scope)
            if cached is not None:
                found[text] = cached
        return found

    def save_translation(
        self,
        result: TranslationResult,
        *,
        scope: str | None = None,
    ) -> None:
        self.saved.append(result)
        self.saved_scopes.append(scope)
        self.results[result.source_text] = result
        self.scoped_results[(scope or "", result.source_text)] = result

    def delete_by_text(
        self,
        source_text: str,
        *,
        scope: str | None = None,
    ) -> bool:
        self.deleted.append(source_text)
        self.deleted_scopes.append(scope)
        self.cached_texts.discard(source_text)
        deleted_scoped = self.scoped_results.pop((scope or "", source_text), None)
        deleted_global = self.results.pop(source_text, None)
        return deleted_scoped is not None or deleted_global is not None


@dataclass
class FakeTranslator:
    calls: list[str] = field(default_factory=list)
    text_types: list[RpgMakerTextType | None] = field(default_factory=list)
    contexts: list[list[str]] = field(default_factory=list)
    failures: set[str] = field(default_factory=set)

    def translate(
        self,
        text: str,
        context: Sequence[str],
        *,
        text_type: RpgMakerTextType | None = None,
    ) -> TranslationResult:
        self.calls.append(text)
        self.text_types.append(text_type)
        self.contexts.append(list(context))
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


def _typed_entry(
    entry_id: int,
    source_text: str,
    text_type: RpgMakerTextType,
) -> RpgMakerTextEntry:
    return RpgMakerTextEntry(
        id=entry_id,
        source_text=source_text,
        text_type=text_type,
        origin=RpgMakerTextOrigin(
            file_name="Map001.json",
            origin_key=f"Map001.json|1|2|0|{entry_id}|0",
            map_id=1,
            event_id=2,
            page_index=0,
            command_index=entry_id,
            parameter_index=0,
        ),
    )


@dataclass
class StepClock:
    current: float = 0.0
    step: float = 1.0

    def __call__(self) -> float:
        value = self.current
        self.current += self.step
        return value


def _service(
    *,
    settings: FakeSettingsRepository | None = None,
    catalog: FakeCatalog | None = None,
    cache: FakeTranslationCache | None = None,
    translator: FakeTranslator | None = None,
    batch_errors: FakeBatchErrorRepository | None = None,
    clock=None,
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
        clock=clock or StepClock(step=0.0),
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


def test_cache_scope_is_memoized_until_project_path_changes():
    service = _service()
    detector = service.rpg_maker_detector

    first = service.get_rpg_maker_cache_scope()
    second = service.get_rpg_maker_cache_scope()

    assert first == second == str(Path("C:/game"))
    assert detector.calls == 1

    service.set_rpg_maker_project_path("C:/game")
    service.get_rpg_maker_cache_scope()

    assert detector.calls == 2


def test_cache_scope_detect_failure_is_not_memoized():
    service = _service()
    detector = service.rpg_maker_detector
    detector.error = ValueError("pasta MV/MZ invalida")

    with pytest.raises(ValueError):
        service.get_rpg_maker_cache_scope()

    detector.error = None

    assert service.get_rpg_maker_cache_scope() == str(Path("C:/game"))


def test_translate_catalog_entry_uses_existing_cache():
    cached = TranslationResult(source_text="Hello there", translated_text="Ola")
    cache = FakeTranslationCache(result=cached)
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog([_entry()]), cache=cache, translator=translator
    )

    result = service.translate_catalog_entry(1)

    assert result == cached
    assert translator.calls == []
    assert cache.saved == []


def test_translate_catalog_entry_uses_active_project_cache_scope():
    active_scope = str(Path("C:/game"))
    other_scope = str(Path("D:/other"))
    cache = FakeTranslationCache(
        scoped_results={
            (active_scope, "Hello there"): TranslationResult(
                source_text="Hello there",
                translated_text="Ola do jogo A",
            ),
            (other_scope, "Hello there"): TranslationResult(
                source_text="Hello there",
                translated_text="Ola do jogo B",
            ),
        }
    )
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog([_entry()]), cache=cache, translator=translator
    )

    result = service.translate_catalog_entry(1)

    assert result is not None
    assert result.translated_text == "Ola do jogo A"
    assert translator.calls == []


def test_translate_catalog_entry_translates_and_saves_cache_miss():
    cache = FakeTranslationCache()
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog([_entry()]), cache=cache, translator=translator
    )

    result = service.translate_catalog_entry(1)

    assert result is not None
    assert result.translated_text == "pt:Hello there"
    assert translator.calls == ["Hello there"]
    assert translator.text_types == [RpgMakerTextType.MESSAGE]
    assert cache.saved == [result]
    assert cache.saved_scopes == [str(Path("C:/game"))]


def test_retranslate_catalog_entry_ignores_existing_cache_and_saves_new_result():
    cached = TranslationResult(source_text="Hello there", translated_text="Ruim")
    cache = FakeTranslationCache(result=cached)
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog([_entry()]), cache=cache, translator=translator
    )

    result = service.retranslate_catalog_entry(1)

    assert result is not None
    assert result.translated_text == "pt:Hello there"
    assert cache.deleted == ["Hello there"]
    assert cache.deleted_scopes == [str(Path("C:/game"))]
    assert translator.calls == ["Hello there"]
    assert translator.text_types == [RpgMakerTextType.MESSAGE]
    assert cache.saved == [result]
    assert cache.saved_scopes == [str(Path("C:/game"))]


def test_retranslate_catalog_entry_returns_none_for_missing_id():
    translator = FakeTranslator()
    service = _service(catalog=FakeCatalog([_entry()]), translator=translator)

    result = service.retranslate_catalog_entry(999)

    assert result is None
    assert translator.calls == []


def test_list_rpg_maker_entries_supports_limit_and_offset():
    service = _service(catalog=FakeCatalog(_entries(4)))

    entries = service.list_rpg_maker_entries(limit=2, offset=1)

    assert [entry.source_text for entry in entries] == ["Line 2", "Line 3"]
    assert service.count_rpg_maker_entries() == 4
    assert service.get_rpg_maker_entry(3).source_text == "Line 3"


def test_list_rpg_maker_entries_rejects_invalid_paging_arguments():
    service = _service(catalog=FakeCatalog(_entries(1)))

    try:
        service.list_rpg_maker_entries(limit=0)
    except ValueError as error:
        assert str(error) == "limit must be greater than zero"
    else:
        raise AssertionError("expected ValueError")

    try:
        service.list_rpg_maker_entries(offset=-1)
    except ValueError as error:
        assert str(error) == "offset must be zero or greater"
    else:
        raise AssertionError("expected ValueError")


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


def test_translate_catalog_entries_translates_duplicate_text_only_once():
    # O catalogo tem o mesmo texto em origens diferentes: a 2a ocorrencia deve
    # aproveitar a traducao salva pela 1a na mesma execucao (o prefetch em lote
    # nao pode retraduzir duplicatas).
    entries = [
        _typed_entry(1, "Hello there", RpgMakerTextType.MESSAGE),
        _typed_entry(2, "Hello there", RpgMakerTextType.MESSAGE),
    ]
    cache = FakeTranslationCache()
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog(entries),
        cache=cache,
        translator=translator,
    )

    result = service.translate_catalog_entries()

    assert translator.calls == ["Hello there"]
    assert result.processed == 2
    assert result.translated == 1
    assert result.cache_hits == 1
    assert result.errors == 0


def test_translate_catalog_entries_saves_punctuation_without_translator():
    cache = FakeTranslationCache()
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog(
            [
                _typed_entry(1, "...", RpgMakerTextType.MESSAGE),
            ]
        ),
        cache=cache,
        translator=translator,
    )

    result = service.translate_catalog_entries()

    assert result.processed == 1
    assert result.translated == 1
    assert result.errors == 0
    assert translator.calls == []
    assert cache.saved == [TranslationResult(source_text="...", translated_text="...")]
    assert cache.saved_scopes == [str(Path("C:/game"))]


def test_translate_catalog_entries_can_be_cancelled():
    cache = FakeTranslationCache()
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog(_entries(3)),
        cache=cache,
        translator=translator,
    )

    result = service.translate_catalog_entries(
        should_cancel=lambda: bool(translator.calls)
    )

    assert result.cancelled is True
    assert result.processed == 1
    assert result.total == 3
    assert translator.calls == ["Line 1"]


def test_translate_catalog_entries_uses_default_types_without_speaker():
    entries = [
        _typed_entry(1, "Dialogue", RpgMakerTextType.MESSAGE),
        _typed_entry(2, "Hero", RpgMakerTextType.SPEAKER),
        _typed_entry(3, "Choice", RpgMakerTextType.CHOICE),
        _typed_entry(4, "Scroll", RpgMakerTextType.SCROLLING_TEXT),
        _typed_entry(5, "Potion", RpgMakerTextType.ITEM_NAME),
        _typed_entry(6, "Restores HP.", RpgMakerTextType.ITEM_DESCRIPTION),
        _typed_entry(7, "Fire", RpgMakerTextType.SKILL_NAME),
        _typed_entry(8, "Deals fire damage.", RpgMakerTextType.SKILL_DESCRIPTION),
        _typed_entry(9, "%1 casts %2!", RpgMakerTextType.SKILL_MESSAGE),
        _typed_entry(10, "Sword", RpgMakerTextType.WEAPON_NAME),
        _typed_entry(11, "A sharp blade.", RpgMakerTextType.WEAPON_DESCRIPTION),
        _typed_entry(12, "Shield", RpgMakerTextType.ARMOR_NAME),
        _typed_entry(13, "Blocks hits.", RpgMakerTextType.ARMOR_DESCRIPTION),
        _typed_entry(14, "Poison", RpgMakerTextType.STATE_NAME),
        _typed_entry(15, "%1 is poisoned!", RpgMakerTextType.STATE_MESSAGE),
        _typed_entry(16, "Warrior", RpgMakerTextType.CLASS_NAME),
        _typed_entry(17, "Slime", RpgMakerTextType.ENEMY_NAME),
        _typed_entry(18, "Hero", RpgMakerTextType.ACTOR_NAME),
        _typed_entry(19, "Item", RpgMakerTextType.SYSTEM_TERM),
        _typed_entry(20, "Battle line", RpgMakerTextType.TROOP_MESSAGE),
        _typed_entry(21, "Battle choice", RpgMakerTextType.TROOP_CHOICE),
        _typed_entry(22, "Battle scroll", RpgMakerTextType.TROOP_SCROLLING_TEXT),
        _typed_entry(23, "General", RpgMakerTextType.TROOP_SPEAKER),
    ]
    translator = FakeTranslator()
    service = _service(catalog=FakeCatalog(entries), translator=translator)

    result = service.translate_catalog_entries()

    assert DEFAULT_CATALOG_TRANSLATION_TYPES == {
        RpgMakerTextType.MESSAGE,
        RpgMakerTextType.CHOICE,
        RpgMakerTextType.SCROLLING_TEXT,
        RpgMakerTextType.ITEM_NAME,
        RpgMakerTextType.ITEM_DESCRIPTION,
        RpgMakerTextType.SKILL_NAME,
        RpgMakerTextType.SKILL_DESCRIPTION,
        RpgMakerTextType.SKILL_MESSAGE,
        RpgMakerTextType.WEAPON_NAME,
        RpgMakerTextType.WEAPON_DESCRIPTION,
        RpgMakerTextType.ARMOR_NAME,
        RpgMakerTextType.ARMOR_DESCRIPTION,
        RpgMakerTextType.STATE_NAME,
        RpgMakerTextType.STATE_MESSAGE,
        RpgMakerTextType.CLASS_NAME,
        RpgMakerTextType.ENEMY_NAME,
        RpgMakerTextType.ACTOR_NAME,
        RpgMakerTextType.SYSTEM_TERM,
        RpgMakerTextType.TROOP_MESSAGE,
        RpgMakerTextType.TROOP_CHOICE,
        RpgMakerTextType.TROOP_SCROLLING_TEXT,
        RpgMakerTextType.TROOP_SPEAKER,
    }
    assert result.total == 22
    assert translator.calls == [
        "Dialogue",
        "Choice",
        "Scroll",
        "Potion",
        "Restores HP.",
        "Fire",
        "Deals fire damage.",
        "%1 casts %2!",
        "Sword",
        "A sharp blade.",
        "Shield",
        "Blocks hits.",
        "Poison",
        "%1 is poisoned!",
        "Warrior",
        "Slime",
        "Hero",
        "Item",
        "Battle line",
        "Battle choice",
        "Battle scroll",
        "General",
    ]


def test_translate_catalog_entries_respects_selected_text_types():
    entries = [
        _typed_entry(1, "Dialogue", RpgMakerTextType.MESSAGE),
        _typed_entry(2, "Hero", RpgMakerTextType.SPEAKER),
        _typed_entry(3, "Choice", RpgMakerTextType.CHOICE),
    ]
    translator = FakeTranslator()
    service = _service(catalog=FakeCatalog(entries), translator=translator)

    result = service.translate_catalog_entries(text_types={RpgMakerTextType.SPEAKER})

    assert result.total == 1
    assert translator.calls == ["Hero"]


def test_translate_catalog_entries_rejects_empty_text_type_filter():
    service = _service(catalog=FakeCatalog(_entries(1)))

    try:
        service.translate_catalog_entries(text_types=set())
    except ValueError as error:
        assert str(error) == "at least one text type must be selected"
    else:
        raise AssertionError("expected ValueError")


def test_translate_catalog_entries_retranslates_contaminated_cache():
    cache = FakeTranslationCache(
        results={
            "Line 1": TranslationResult(
                source_text="Line 1",
                translated_text=(
                    "Linha 1\n"
                    "Preserve nomes proprios. Nao explique.\n"
                    "Responda apenas JSON valido."
                ),
            ),
            "Line 2": TranslationResult(
                source_text="Line 2",
                translated_text="Linha 2",
            ),
        }
    )
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog(_entries(2)),
        cache=cache,
        translator=translator,
    )

    result = service.translate_catalog_entries()

    assert result.translated == 1
    assert result.cache_hits == 1
    assert translator.calls == ["Line 1"]
    assert cache.get_by_text("Line 1").translated_text == "pt:Line 1"


def test_translate_catalog_entries_retranslates_overlong_skill_description_cache():
    source_text = (
        "A skill that tears through all enemies in a flash. Deals dark damage "
        "to all enemies. Medium chance of inflicting Slip."
    )
    cache = FakeTranslationCache(
        results={
            source_text: TranslationResult(
                source_text=source_text,
                translated_text=(
                    "Uma habilidade que atravessa todos os inimigos em um flash e "
                    "causa dano sombrio a todos os inimigos, com chance media de "
                    "infligir Slip e mais detalhes explicativos que nao cabem na UI."
                ),
            ),
        }
    )
    translator = FakeTranslator()
    service = _service(
        catalog=FakeCatalog(
            [_typed_entry(1, source_text, RpgMakerTextType.SKILL_DESCRIPTION)]
        ),
        cache=cache,
        translator=translator,
    )

    result = service.translate_catalog_entries()

    assert result.translated == 1
    assert result.cache_hits == 0
    assert translator.calls == [source_text]
    assert cache.get_by_text(source_text).translated_text == f"pt:{source_text}"


def test_translate_catalog_entries_reports_cache_rejections_by_rule():
    cache = FakeTranslationCache(
        results={
            "Line 1": TranslationResult(
                source_text="Line 1",
                translated_text="Linha 1",
            ),
            "Line 2": TranslationResult(
                source_text="Line 2",
                translated_text="Linha 2. Preserve nomes proprios. Nao explique.",
            ),
            "Line 3": TranslationResult(
                source_text="Line 3",
                translated_text=(
                    "Linha 3.\nUma fala extra.\nOutra fala extra.\nMais uma fala."
                ),
            ),
        }
    )
    service = _service(catalog=FakeCatalog(_entries(3)), cache=cache)

    result = service.translate_catalog_entries()

    assert result.cache_hits == 1
    assert result.translated == 2
    assert result.rejected_by_rule == (
        ("context_leak", 1),
        ("prompt_leak", 1),
    )


def test_translate_catalog_entries_reports_no_rejections_for_clean_batch():
    service = _service(catalog=FakeCatalog(_entries(2)))

    result = service.translate_catalog_entries()

    assert result.rejected_by_rule == ()


def test_translate_catalog_entries_waits_while_paused():
    translator = FakeTranslator()
    service = _service(catalog=FakeCatalog(_entries(2)), translator=translator)
    paused = {"value": True}
    wait_calls = []
    progress = []

    def _should_pause() -> bool:
        return paused["value"]

    def _wait_if_paused() -> None:
        wait_calls.append(True)
        paused["value"] = False

    result = service.translate_catalog_entries(
        should_pause=_should_pause,
        wait_if_paused=_wait_if_paused,
        on_progress=progress.append,
    )

    assert result.processed == 2
    assert wait_calls == [True]
    assert progress[0].paused is True
    assert translator.calls == ["Line 1", "Line 2"]


def test_translate_catalog_entries_tracks_elapsed_and_average_translation_time():
    service = _service(
        catalog=FakeCatalog(_entries(2)),
        clock=StepClock(step=1.0),
    )

    result = service.translate_catalog_entries()

    assert result.elapsed_seconds > 0.0
    assert result.average_translation_seconds == 1.0


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


def test_count_cached_catalog_entries_excludes_contaminated_translations():
    cache = FakeTranslationCache(
        results={
            "Line 1": TranslationResult(
                source_text="Line 1", translated_text="Linha um"
            ),
            "Line 2": TranslationResult(
                source_text="Line 2",
                translated_text="Preserve nomes proprios e responda apenas json",
            ),
        }
    )
    service = _service(catalog=FakeCatalog(_entries(3)), cache=cache)

    # Linha 1 é válida, linha 2 está contaminada, linha 3 não tem cache.
    assert service.count_cached_catalog_entries() == 1


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


def test_clear_contaminated_catalog_cache_keeps_other_project_scope():
    active_scope = str(Path("C:/game"))
    other_scope = str(Path("D:/other"))
    invalid = TranslationResult(
        source_text="Line 1",
        translated_text="Linha 1\nResponda apenas JSON valido.",
    )
    cache = FakeTranslationCache(
        scoped_results={
            (active_scope, "Line 1"): invalid,
            (other_scope, "Line 1"): invalid,
        }
    )
    service = _service(catalog=FakeCatalog(_entries(1)), cache=cache)

    deleted = service.clear_contaminated_catalog_cache()

    assert deleted == 1
    assert cache.deleted_scopes == [active_scope]
    assert cache.get_by_text("Line 1", scope=active_scope) is None
    assert cache.get_by_text("Line 1", scope=other_scope) is not None


def _dialogue_entry(
    entry_id: int,
    source_text: str,
    *,
    text_type: RpgMakerTextType = RpgMakerTextType.MESSAGE,
    file_name: str = "Map001.json",
    map_id: int | None = 1,
    event_id: int | None = 2,
    page_index: int | None = 0,
) -> RpgMakerTextEntry:
    return RpgMakerTextEntry(
        id=entry_id,
        source_text=source_text,
        text_type=text_type,
        origin=RpgMakerTextOrigin(
            file_name=file_name,
            origin_key=f"{file_name}|{map_id}|{event_id}|{page_index}|{entry_id}|0",
            map_id=map_id,
            event_id=event_id,
            page_index=page_index,
            command_index=entry_id,
            parameter_index=0,
        ),
    )


def test_translate_catalog_entries_passes_previous_lines_as_context():
    translator = FakeTranslator()
    catalog = FakeCatalog(
        [
            _dialogue_entry(1, "First line"),
            _dialogue_entry(2, "Second line"),
            _dialogue_entry(3, "Third line"),
        ]
    )
    service = _service(catalog=catalog, translator=translator)

    service.translate_catalog_entries()

    assert translator.calls == ["First line", "Second line", "Third line"]
    assert translator.contexts == [
        [],
        ["First line"],
        ["First line", "Second line"],
    ]


def test_translate_catalog_entries_resets_context_across_events_and_pages():
    translator = FakeTranslator()
    catalog = FakeCatalog(
        [
            _dialogue_entry(1, "Event one line", event_id=1),
            _dialogue_entry(2, "Other event line", event_id=2),
            _dialogue_entry(3, "Other page line", event_id=2, page_index=1),
        ]
    )
    service = _service(catalog=catalog, translator=translator)

    service.translate_catalog_entries()

    # Cada entrada abre um bloco novo, entao nenhuma recebe contexto.
    assert translator.contexts == [[], [], []]


def test_translate_catalog_entries_choice_batch_gets_message_context():
    translator = FakeTranslator()
    catalog = FakeCatalog(
        [
            _dialogue_entry(1, "Will you come with me?"),
            _dialogue_entry(2, "Yes", text_type=RpgMakerTextType.CHOICE),
        ]
    )
    service = _service(catalog=catalog, translator=translator)

    service.translate_catalog_entries(text_types={RpgMakerTextType.CHOICE})

    # Mesmo com o lote filtrado por escolha, a mensagem vizinha vira contexto.
    assert translator.calls == ["Yes"]
    assert translator.contexts == [["Will you come with me?"]]


def test_translate_catalog_entries_choices_do_not_feed_context():
    translator = FakeTranslator()
    catalog = FakeCatalog(
        [
            _dialogue_entry(1, "Pick one."),
            _dialogue_entry(2, "Yes", text_type=RpgMakerTextType.CHOICE),
            _dialogue_entry(3, "Good choice."),
        ]
    )
    service = _service(catalog=catalog, translator=translator)

    service.translate_catalog_entries()

    # A escolha recebe contexto, mas nao entra como "fala anterior".
    assert translator.contexts == [[], ["Pick one."], ["Pick one."]]


def test_translate_catalog_entries_database_types_get_no_context():
    translator = FakeTranslator()
    catalog = FakeCatalog(
        [
            _dialogue_entry(1, "A long day ends."),
            _typed_entry(2, "Potion", RpgMakerTextType.ITEM_NAME),
        ]
    )
    service = _service(catalog=catalog, translator=translator)

    service.translate_catalog_entries()

    assert translator.contexts == [[], []]


def test_translate_catalog_entries_caps_context_at_batch_context_lines():
    translator = FakeTranslator()
    catalog = FakeCatalog(
        [_dialogue_entry(index, f"Line {index}") for index in range(1, 7)]
    )
    service = _service(catalog=catalog, translator=translator)

    service.translate_catalog_entries()

    # batch_context_lines padrao = 4: a sexta fala ve apenas as 4 anteriores.
    assert translator.contexts[-1] == ["Line 2", "Line 3", "Line 4", "Line 5"]


def test_translate_catalog_entry_single_stays_without_context():
    # Decisao atual: traducao/retraducao individual nao usa contexto
    # (follow-up possivel). So o lote monta o contexto de dialogo.
    translator = FakeTranslator()
    catalog = FakeCatalog(
        [
            _dialogue_entry(1, "First line"),
            _dialogue_entry(2, "Second line"),
        ]
    )
    service = _service(catalog=catalog, translator=translator)

    service.translate_catalog_entry(2)
    service.retranslate_catalog_entry(2)

    assert translator.contexts == [[], []]


def test_clear_contaminated_catalog_cache_deletes_expanded_punctuation_text():
    cache = FakeTranslationCache(
        results={
            "...": TranslationResult(
                source_text="...",
                translated_text="Eu nao sei quem voce e, mas me pediram para falar.",
            ),
        }
    )
    service = _service(
        catalog=FakeCatalog([_typed_entry(1, "...", RpgMakerTextType.MESSAGE)]),
        cache=cache,
    )

    deleted = service.clear_contaminated_catalog_cache()

    assert deleted == 1
    assert cache.deleted == ["..."]
