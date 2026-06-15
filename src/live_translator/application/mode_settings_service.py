from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Callable, Iterable

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
    RpgMakerProject,
    RpgMakerTextEntry,
    RpgMakerTextType,
    TranslationResult,
)

from live_translator.domain.translation_quality import (
    invalid_translation_reason,
    looks_like_invalid_translation,
    should_bypass_rpg_maker_translation,
)
from .rpg_maker_patch_service import (
    DESCRIPTION_LINE_LIMIT,
    MESSAGE_FACE_LINE_LIMIT,
    MESSAGE_LINE_LIMIT,
    RpgMakerPatchApplyResult,
    RpgMakerPatchRestoreResult,
    RpgMakerPatchResult,
    RpgMakerPatchService,
)


ACTIVE_MODE_SETTING_KEY = "operation.active_mode"
RPG_MAKER_PROJECT_PATH_SETTING_KEY = "rpg_maker.project_path"
RPG_MAKER_LAST_PATCH_PATH_SETTING_KEY = "rpg_maker.last_patch_path"
DEFAULT_CATALOG_TRANSLATION_TYPES = frozenset(
    {
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
)
# Tipos narrativos que recebem falas anteriores como contexto no lote. Nomes,
# descricoes e termos de database sao isolados por natureza e ficam sem contexto.
_CONTEXT_RECEIVING_TYPES = frozenset(
    {
        RpgMakerTextType.MESSAGE,
        RpgMakerTextType.CHOICE,
        RpgMakerTextType.SCROLLING_TEXT,
        RpgMakerTextType.TROOP_MESSAGE,
        RpgMakerTextType.TROOP_CHOICE,
        RpgMakerTextType.TROOP_SCROLLING_TEXT,
    }
)
# Tipos que alimentam o contexto: so falas corridas. Escolhas e nomes de quem
# fala confundem mais do que ajudam como "fala anterior".
_CONTEXT_PROVIDING_TYPES = frozenset(
    {
        RpgMakerTextType.MESSAGE,
        RpgMakerTextType.SCROLLING_TEXT,
        RpgMakerTextType.TROOP_MESSAGE,
        RpgMakerTextType.TROOP_SCROLLING_TEXT,
    }
)


def _build_dialogue_contexts(
    entries: Iterable[RpgMakerTextEntry],
    max_lines: int,
) -> dict[int, tuple[str, ...]]:
    """Mapeia id da entrada -> falas fonte anteriores do mesmo bloco.

    O bloco e o evento/pagina (ou objeto de database) de origem: o contexto
    nunca vaza entre eventos, mapas ou paginas diferentes. Recebe o catalogo
    completo, na ordem de importacao, para que lotes filtrados por tipo ainda
    enxerguem as messages vizinhas.
    """
    contexts: dict[int, tuple[str, ...]] = {}
    if max_lines <= 0:
        return contexts

    recent: deque[str] = deque(maxlen=max_lines)
    current_block: tuple[object, ...] | None = None
    for entry in entries:
        origin = entry.origin
        block = (
            origin.file_name,
            origin.map_id,
            origin.event_id,
            origin.page_index,
            origin.database_id,
        )
        if block != current_block:
            recent.clear()
            current_block = block

        if (
            entry.id is not None
            and entry.text_type in _CONTEXT_RECEIVING_TYPES
            and recent
        ):
            contexts[entry.id] = tuple(recent)
        if entry.text_type in _CONTEXT_PROVIDING_TYPES and entry.source_text.strip():
            recent.append(entry.source_text)
    return contexts


@dataclass(frozen=True, slots=True)
class CatalogTranslationProgress:
    total: int
    processed: int
    translated: int
    cache_hits: int
    errors: int
    cancelled: bool = False
    paused: bool = False
    elapsed_seconds: float = 0.0
    average_translation_seconds: float = 0.0
    current_text: str = ""


@dataclass(frozen=True, slots=True)
class CatalogTranslationResult:
    total: int
    processed: int
    translated: int
    cache_hits: int
    errors: int
    cancelled: bool = False
    elapsed_seconds: float = 0.0
    average_translation_seconds: float = 0.0
    # Traducoes do cache descartadas pelo translation_quality, por regra
    # (nomes de invalid_translation_reason), em pares (regra, quantidade).
    rejected_by_rule: tuple[tuple[str, int], ...] = ()


ProgressCallback = Callable[[CatalogTranslationProgress], None]
CancelChecker = Callable[[], bool]
PauseChecker = Callable[[], bool]
PauseWaiter = Callable[[], None]
Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class ModeSettingsService:
    settings_repository: SettingsRepository
    rpg_maker_detector: RpgMakerProjectDetector
    rpg_maker_parser: RpgMakerTextParser
    rpg_maker_catalog: RpgMakerTextCatalog
    translation_cache: TranslationCache
    translator: Translator
    batch_error_repository: CatalogTranslationErrorRepository
    patch_export_root: Path = Path("exports") / "patches"
    patch_backup_root: Path = Path("backups") / "patches"
    patch_message_line_limit: int = MESSAGE_LINE_LIMIT
    patch_message_face_line_limit: int = MESSAGE_FACE_LINE_LIMIT
    patch_description_line_limit: int = DESCRIPTION_LINE_LIMIT
    # Maximo de falas anteriores enviadas como contexto por traducao do lote.
    batch_context_lines: int = 4
    clock: Clock = monotonic
    # Memoiza o scope por caminho de projeto: o runtime consulta o scope a cada
    # fala do bridge e detect() faz I/O de filesystem. Invalidado em
    # set_rpg_maker_project_path. Falhas de detect nao sao memoizadas, para o
    # scope voltar sozinho quando o caminho ficar valido de novo.
    _scope_cache: dict[str, str] = field(default_factory=dict, init=False, repr=False)

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
        self._scope_cache.clear()
        if path is None or not str(path).strip():
            self.settings_repository.delete(RPG_MAKER_PROJECT_PATH_SETTING_KEY)
            return

        self.settings_repository.set(
            RPG_MAKER_PROJECT_PATH_SETTING_KEY,
            str(Path(path)),
        )

    def get_rpg_maker_cache_scope(self) -> str | None:
        project_path = self.get_rpg_maker_project_path()
        if project_path is None:
            return None

        cache_key = str(project_path)
        memoized = self._scope_cache.get(cache_key)
        if memoized is not None:
            return memoized

        project = self.rpg_maker_detector.detect(project_path)
        scope = str(project.root_path)
        self._scope_cache[cache_key] = scope
        return scope

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

        scope = self.get_rpg_maker_cache_scope()
        cached = self.translation_cache.get_by_text(entry.source_text, scope=scope)
        if cached is not None and not looks_like_invalid_translation(
            entry.source_text,
            cached.translated_text,
            text_type=entry.text_type,
        ):
            return cached

        passthrough = _passthrough_translation(entry)
        if passthrough is not None:
            self.translation_cache.save_translation(passthrough, scope=scope)
            return passthrough

        result = self.translator.translate(
            entry.source_text,
            [],
            text_type=entry.text_type,
        )
        self.translation_cache.save_translation(result, scope=scope)
        return result

    def retranslate_catalog_entry(self, entry_id: int) -> TranslationResult | None:
        entry = self.rpg_maker_catalog.get_entry(entry_id)
        if entry is None:
            return None

        scope = self.get_rpg_maker_cache_scope()
        self.translation_cache.delete_by_text(entry.source_text, scope=scope)
        passthrough = _passthrough_translation(entry)
        if passthrough is not None:
            self.translation_cache.save_translation(passthrough, scope=scope)
            return passthrough

        result = self.translator.translate(
            entry.source_text,
            [],
            text_type=entry.text_type,
        )
        self.translation_cache.save_translation(result, scope=scope)
        return result

    def translate_catalog_entries(
        self,
        *,
        limit: int | None = None,
        text_types: set[RpgMakerTextType] | frozenset[RpgMakerTextType] | None = None,
        on_progress: ProgressCallback | None = None,
        should_cancel: CancelChecker | None = None,
        should_pause: PauseChecker | None = None,
        wait_if_paused: PauseWaiter | None = None,
    ) -> CatalogTranslationResult:
        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than zero")

        selected_types = (
            DEFAULT_CATALOG_TRANSLATION_TYPES
            if text_types is None
            else frozenset(text_types)
        )
        if not selected_types:
            raise ValueError("at least one text type must be selected")

        all_entries = self.list_rpg_maker_entries()
        entries = [entry for entry in all_entries if entry.text_type in selected_types]
        if limit is not None:
            entries = entries[:limit]
        # Contexto construido sobre o catalogo completo: um lote filtrado (por
        # exemplo so choices) ainda recebe as messages vizinhas como contexto.
        context_by_entry_id = _build_dialogue_contexts(
            all_entries,
            self.batch_context_lines,
        )

        started_at = self.clock()
        total = len(entries)
        translated = 0
        cache_hits = 0
        errors = 0
        processed = 0
        cancelled = False
        translation_seconds_total = 0.0
        rejected_by_rule: Counter[str] = Counter()
        scope = self.get_rpg_maker_cache_scope()
        # Prefetch em lote (anti-N+1). O catalogo tem textos duplicados em
        # origens diferentes: apos cada save_translation o mapa local e
        # atualizado, para a proxima ocorrencia do mesmo texto contar como
        # acerto de cache em vez de ser retraduzida.
        cached_by_text = self.translation_cache.get_many_by_text(
            [entry.source_text for entry in entries],
            scope=scope,
        )
        self.batch_error_repository.clear_last_batch_errors()

        for entry in entries:
            if should_pause is not None and should_pause():
                if on_progress is not None:
                    on_progress(
                        self._build_progress(
                            total=total,
                            processed=processed,
                            translated=translated,
                            cache_hits=cache_hits,
                            errors=errors,
                            cancelled=cancelled,
                            paused=True,
                            started_at=started_at,
                            translation_seconds_total=translation_seconds_total,
                            current_text=entry.source_text,
                        )
                    )
                if wait_if_paused is not None:
                    wait_if_paused()

            if should_cancel is not None and should_cancel():
                cancelled = True
                break

            try:
                cached = cached_by_text.get(entry.source_text)
                cached_rejection = (
                    None
                    if cached is None
                    else invalid_translation_reason(
                        entry.source_text,
                        cached.translated_text,
                        text_type=entry.text_type,
                    )
                )
                if cached is not None and cached_rejection is None:
                    cache_hits += 1
                else:
                    if cached_rejection is not None:
                        rejected_by_rule[cached_rejection] += 1
                    result = _passthrough_translation(entry)
                    if result is None:
                        translation_started_at = self.clock()
                        result = self.translator.translate(
                            entry.source_text,
                            list(context_by_entry_id.get(entry.id, ())),
                            text_type=entry.text_type,
                        )
                        translation_seconds_total += (
                            self.clock() - translation_started_at
                        )
                    self.translation_cache.save_translation(result, scope=scope)
                    cached_by_text[entry.source_text] = result
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
                            paused=False,
                            elapsed_seconds=self.clock() - started_at,
                            average_translation_seconds=_average(
                                translation_seconds_total,
                                translated,
                            ),
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
            elapsed_seconds=self.clock() - started_at,
            average_translation_seconds=_average(translation_seconds_total, translated),
            rejected_by_rule=tuple(sorted(rejected_by_rule.items())),
        )

    def list_rpg_maker_entries(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RpgMakerTextEntry]:
        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than zero")
        if offset < 0:
            raise ValueError("offset must be zero or greater")

        project_path = self.get_rpg_maker_project_path()
        if project_path is None:
            return []

        project = self.rpg_maker_detector.detect(project_path)
        return self.rpg_maker_catalog.list_project_entries(
            project,
            limit=limit,
            offset=offset,
        )

    def count_rpg_maker_entries(self) -> int:
        project_path = self.get_rpg_maker_project_path()
        if project_path is None:
            return 0

        project = self.rpg_maker_detector.detect(project_path)
        return self.rpg_maker_catalog.count_project_entries(project)

    def get_rpg_maker_entry(self, entry_id: int) -> RpgMakerTextEntry | None:
        return self.rpg_maker_catalog.get_entry(entry_id)

    def count_cached_catalog_entries(self) -> int:
        scope = self.get_rpg_maker_cache_scope()
        entries = self.list_rpg_maker_entries()
        cached_by_text = self.translation_cache.get_many_by_text(
            [entry.source_text for entry in entries],
            scope=scope,
        )
        count = 0
        for entry in entries:
            cached = cached_by_text.get(entry.source_text)
            if cached is None:
                continue
            # Entrada contaminada no cache não é acerto real: lote e patch a
            # retraduzem, então ela não pode inflar a contagem.
            if looks_like_invalid_translation(
                entry.source_text,
                cached.translated_text,
                text_type=entry.text_type,
            ):
                continue
            count += 1
        return count

    def clear_contaminated_catalog_cache(self) -> int:
        scope = self.get_rpg_maker_cache_scope()
        entries = self.list_rpg_maker_entries()
        cached_by_text = self.translation_cache.get_many_by_text(
            [entry.source_text for entry in entries],
            scope=scope,
        )
        deleted = 0
        for entry in entries:
            cached = cached_by_text.get(entry.source_text)
            if cached is None:
                continue
            if not looks_like_invalid_translation(
                entry.source_text,
                cached.translated_text,
                text_type=entry.text_type,
            ):
                continue
            if self.translation_cache.delete_by_text(entry.source_text, scope=scope):
                deleted += 1
        return deleted

    def list_last_batch_errors(self) -> list[CatalogTranslationError]:
        return self.batch_error_repository.list_last_batch_errors()

    def export_rpg_maker_patch(
        self,
        *,
        include_speakers: bool = False,
    ) -> RpgMakerPatchResult:
        project = self._active_rpg_maker_project()
        result = self._patch_service(cache_scope=str(project.root_path)).export_patch(
            project=project,
            entries=self.rpg_maker_catalog.list_project_entries(project),
            include_speakers=include_speakers,
        )
        self.settings_repository.set(
            RPG_MAKER_LAST_PATCH_PATH_SETTING_KEY,
            str(result.patch_path),
        )
        return result

    def apply_last_rpg_maker_patch(self) -> RpgMakerPatchApplyResult:
        project = self._active_rpg_maker_project()
        raw_patch_path = self.settings_repository.get(
            RPG_MAKER_LAST_PATCH_PATH_SETTING_KEY
        )
        if raw_patch_path is None or not raw_patch_path.strip():
            raise FileNotFoundError("no RPG Maker patch has been generated")

        return self._patch_service().apply_patch(
            project=project,
            patch_path=Path(raw_patch_path),
        )

    def restore_last_rpg_maker_patch_backup(self) -> RpgMakerPatchRestoreResult:
        project = self._active_rpg_maker_project()
        return self._patch_service().restore_latest_backup(project=project)

    def _active_rpg_maker_project(self) -> RpgMakerProject:
        project_path = self.get_rpg_maker_project_path()
        if project_path is None:
            raise ValueError("RPG Maker project path is not configured")
        return self.rpg_maker_detector.detect(project_path)

    def _patch_service(self, *, cache_scope: str | None = None) -> RpgMakerPatchService:
        return RpgMakerPatchService(
            self.translation_cache,
            cache_scope=cache_scope,
            export_root=self.patch_export_root,
            backup_root=self.patch_backup_root,
            message_line_limit=self.patch_message_line_limit,
            message_face_line_limit=self.patch_message_face_line_limit,
            description_line_limit=self.patch_description_line_limit,
        )

    def _build_progress(
        self,
        *,
        total: int,
        processed: int,
        translated: int,
        cache_hits: int,
        errors: int,
        cancelled: bool,
        paused: bool,
        started_at: float,
        translation_seconds_total: float,
        current_text: str,
    ) -> CatalogTranslationProgress:
        return CatalogTranslationProgress(
            total=total,
            processed=processed,
            translated=translated,
            cache_hits=cache_hits,
            errors=errors,
            cancelled=cancelled,
            paused=paused,
            elapsed_seconds=self.clock() - started_at,
            average_translation_seconds=_average(
                translation_seconds_total,
                translated,
            ),
            current_text=current_text,
        )


def _format_entry_origin(entry: RpgMakerTextEntry) -> str:
    origin = entry.origin
    parts = [origin.file_name]
    if origin.database_id is not None:
        parts.append(f"id {origin.database_id}")
    if origin.field_name is not None:
        parts.append(origin.field_name)
    if origin.event_id is not None:
        parts.append(f"ev {origin.event_id}")
    if origin.page_index is not None:
        parts.append(f"pg {origin.page_index}")
    if origin.command_index is not None:
        parts.append(f"cmd {origin.command_index}")
    return " | ".join(parts)


def _passthrough_translation(entry: RpgMakerTextEntry) -> TranslationResult | None:
    if not should_bypass_rpg_maker_translation(entry.source_text):
        return None
    return TranslationResult(
        source_text=entry.source_text,
        translated_text=entry.source_text,
    )


def _average(total: float, count: int) -> float:
    if count <= 0:
        return 0.0
    return total / count
