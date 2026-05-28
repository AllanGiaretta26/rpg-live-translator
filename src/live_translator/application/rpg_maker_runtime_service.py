from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Callable

from live_translator.application.translation_pipeline_service import DefaultTextNormalizer
from live_translator.application.translation_quality import looks_like_invalid_translation
from live_translator.domain.interfaces import (
    OverlayRenderer,
    TextNormalizer,
    TranslationCache,
    Translator,
)
from live_translator.domain.models import OperationMode, TranslationResult

from .mode_settings_service import ModeSettingsService


Clock = Callable[[], float]


@dataclass(slots=True)
class RpgMakerRuntimeService:
    mode_settings: ModeSettingsService
    translation_cache: TranslationCache
    translator: Translator
    overlay: OverlayRenderer
    text_normalizer: TextNormalizer = field(default_factory=DefaultTextNormalizer)
    clock: Clock = monotonic
    _last_diagnostic: str | None = field(default=None, init=False, repr=False)
    _last_timing_summary: str | None = field(default=None, init=False, repr=False)
    _last_source_text: str | None = field(default=None, init=False, repr=False)
    _last_translated_text: str | None = field(default=None, init=False, repr=False)
    _latest_request_id: int = field(default=0, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @property
    def last_diagnostic(self) -> str | None:
        with self._lock:
            return self._last_diagnostic

    @property
    def last_timing_summary(self) -> str | None:
        with self._lock:
            return self._last_timing_summary

    @property
    def last_source_text(self) -> str | None:
        with self._lock:
            return self._last_source_text

    @property
    def last_translated_text(self) -> str | None:
        with self._lock:
            return self._last_translated_text

    def process_text(self, text: str) -> TranslationResult | None:
        started_at = self.clock()
        translation_seconds: float | None = None
        if self.mode_settings.get_active_mode() != OperationMode.RPG_MAKER_MV_MZ:
            self._set_diagnostics("ignorado: modo universal", started_at)
            return None

        normalized_text = self.text_normalizer.normalize(text)
        if not normalized_text:
            self._set_diagnostics("sem texto runtime", started_at)
            return None

        request_id = self._start_request(normalized_text)
        cached = self.translation_cache.get_by_text(normalized_text)
        if cached is not None:
            if looks_like_invalid_translation(normalized_text, cached.translated_text):
                self._set_diagnostic("runtime cache invalido")
            else:
                if self._is_latest_request(request_id):
                    self.overlay.show_text(cached.translated_text)
                    self._set_last_translated_text(cached.translated_text)
                    self._set_diagnostics("runtime cache texto", started_at)
                return cached

        self._set_diagnostic("runtime traduzindo")
        translation_started_at = self.clock()
        try:
            result = self.translator.translate(normalized_text, [])
        except Exception as error:
            translation_seconds = self.clock() - translation_started_at
            self._set_diagnostics(
                f"runtime traducao falhou: {error}",
                started_at,
                translation_seconds=translation_seconds,
                stage="erro",
            )
            raise

        translation_seconds = self.clock() - translation_started_at
        self.translation_cache.save_translation(result)
        if self._is_latest_request(request_id):
            self.overlay.show_text(result.translated_text)
            self._set_last_translated_text(result.translated_text)
            self._set_diagnostics(
                "runtime traduzido",
                started_at,
                translation_seconds=translation_seconds,
                stage="cache miss",
            )
        return result

    def reprocess_last_text(self) -> TranslationResult | None:
        with self._lock:
            source_text = self._last_source_text

        if source_text is None or not source_text.strip():
            self._set_diagnostic("runtime sem fala atual para reprocessar")
            return None

        self.translation_cache.delete_by_text(source_text)
        return self.process_text(source_text)

    def _start_request(self, text: str) -> int:
        with self._lock:
            self._latest_request_id += 1
            self._last_source_text = text
            return self._latest_request_id

    def _is_latest_request(self, request_id: int) -> bool:
        with self._lock:
            return request_id == self._latest_request_id

    def _set_last_translated_text(self, text: str) -> None:
        with self._lock:
            self._last_translated_text = text

    def _set_diagnostic(self, diagnostic: str) -> None:
        with self._lock:
            self._last_diagnostic = diagnostic

    def _set_diagnostics(
        self,
        diagnostic: str,
        started_at: float,
        *,
        translation_seconds: float | None = None,
        stage: str | None = None,
    ) -> None:
        parts = [f"runtime total {self.clock() - started_at:.2f}s"]
        if translation_seconds is not None:
            parts.append(f"traducao {translation_seconds:.2f}s")
        if stage is not None:
            parts.append(stage)
        with self._lock:
            self._last_diagnostic = diagnostic
            self._last_timing_summary = " | ".join(parts)
