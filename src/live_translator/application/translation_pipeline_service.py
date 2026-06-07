from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Callable
import unicodedata

from live_translator.domain.interfaces import (
    ImageCache,
    ImageChangeDetector,
    ImageHasher,
    OverlayRenderer,
    TextExtractor,
    TextNormalizer,
    TranslationCache,
    Translator,
)


Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class DefaultTextNormalizer(TextNormalizer):
    def normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text).strip()
        return " ".join(normalized.split())


_NON_GAME_TEXT_MARKERS = (
    "voce e um sistema",
    "você é um sistema",
    "sistema de ocr",
    "ocr e traducao",
    "ocr e tradução",
    "traducao para jogos rpg",
    "tradução para jogos rpg",
    "responda apenas json",
    "source_text",
    "translated_text",
    "live translator",
    "aguardando texto",
)


def _looks_like_non_game_text(text: str) -> bool:
    normalized = text.casefold()
    return any(marker in normalized for marker in _NON_GAME_TEXT_MARKERS)


@dataclass(slots=True)
class TranslationPipelineService:
    text_extractor: TextExtractor
    translator: Translator
    translation_cache: TranslationCache
    image_cache: ImageCache
    image_hasher: ImageHasher
    change_detector: ImageChangeDetector
    overlay: OverlayRenderer
    text_normalizer: TextNormalizer = field(default_factory=DefaultTextNormalizer)
    clock: Clock = monotonic
    # Recent context is intentionally kept empty: the pipeline never feeds prior
    # lines back to the translator, to avoid leaking earlier dialogue into the
    # current translation. The property is exposed so tests can guard that the
    # context never accumulates (see translate(..., []) below).
    _context: list[str] = field(default_factory=list, init=False, repr=False)
    _last_diagnostic: str | None = field(default=None, init=False, repr=False)
    _last_timing_summary: str | None = field(default=None, init=False, repr=False)
    _diagnostic_lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @property
    def context(self) -> tuple[str, ...]:
        return tuple(self._context)

    @property
    def last_diagnostic(self) -> str | None:
        with self._diagnostic_lock:
            return self._last_diagnostic

    @property
    def last_timing_summary(self) -> str | None:
        with self._diagnostic_lock:
            return self._last_timing_summary

    def process_frame(self, image: object) -> None:
        started_at = self.clock()
        ocr_seconds: float | None = None
        translation_seconds: float | None = None
        try:
            if not self.change_detector.has_changed(image):
                self._set_diagnostic("sem mudanca")
                self._set_timing_summary(started_at, stage="sem mudanca")
                return

            image_hash = self.image_hasher.hash_image(image)
            cached_by_image = self.image_cache.get_by_hash(image_hash)
            if cached_by_image is not None:
                self._set_diagnostic("cache imagem")
                self._set_timing_summary(started_at, stage="cache imagem")
                self.overlay.show_text(cached_by_image.translated_text)
                return

            ocr_started_at = self.clock()
            extracted = self.text_extractor.extract(image)
            ocr_seconds = self.clock() - ocr_started_at
            normalized_text = self.text_normalizer.normalize(extracted.text)
            if not normalized_text or _looks_like_non_game_text(normalized_text):
                self._set_diagnostic("sem texto")
                self._set_timing_summary(
                    started_at,
                    ocr_seconds=ocr_seconds,
                    stage="sem texto",
                )
                return

            cached_by_text = self.translation_cache.get_by_text(normalized_text)
            if cached_by_text is not None:
                self._set_diagnostic("cache texto")
                self._set_timing_summary(
                    started_at,
                    ocr_seconds=ocr_seconds,
                    stage="cache texto",
                )
                self.image_cache.save_image_result(image_hash, cached_by_text)
                self.overlay.show_text(cached_by_text.translated_text)
                return

            self._set_diagnostic("traduzindo")
            translation_started_at = self.clock()
            try:
                result = self.translator.translate(normalized_text, [])
            except Exception as error:
                translation_seconds = self.clock() - translation_started_at
                self._set_diagnostic(f"traducao falhou: {error}")
                raise
            translation_seconds = self.clock() - translation_started_at
            self.translation_cache.save_translation(result)
            self.image_cache.save_image_result(image_hash, result)
            self._set_timing_summary(
                started_at,
                ocr_seconds=ocr_seconds,
                translation_seconds=translation_seconds,
                stage="cache miss",
            )
            self._set_diagnostic("traduzido")
            self.overlay.show_text(result.translated_text)
        except Exception as error:
            current_diagnostic = self.last_diagnostic
            if current_diagnostic is None or not current_diagnostic.startswith(
                "traducao falhou:"
            ):
                self._set_diagnostic(f"erro: {error}")
            self._set_timing_summary(
                started_at,
                ocr_seconds=ocr_seconds,
                translation_seconds=translation_seconds,
                stage="erro",
            )
            raise

    def _set_diagnostic(self, diagnostic: str) -> None:
        with self._diagnostic_lock:
            self._last_diagnostic = diagnostic

    def _set_timing_summary(
        self,
        started_at: float,
        *,
        ocr_seconds: float | None = None,
        translation_seconds: float | None = None,
        stage: str,
    ) -> None:
        parts = [f"total {self.clock() - started_at:.2f}s"]
        if ocr_seconds is not None:
            parts.append(f"ocr {ocr_seconds:.2f}s")
        if translation_seconds is not None:
            parts.append(f"traducao {translation_seconds:.2f}s")
        parts.append(stage)
        with self._diagnostic_lock:
            self._last_timing_summary = " | ".join(parts)
