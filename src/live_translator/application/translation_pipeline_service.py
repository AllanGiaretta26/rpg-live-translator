from __future__ import annotations

from dataclasses import dataclass, field
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
    _context: list[str] = field(default_factory=list, init=False, repr=False)

    @property
    def context(self) -> tuple[str, ...]:
        return tuple(self._context)

    def process_frame(self, image: object) -> None:
        if not self.change_detector.has_changed(image):
            return

        image_hash = self.image_hasher.hash_image(image)
        cached_by_image = self.image_cache.get_by_hash(image_hash)
        if cached_by_image is not None:
            self.overlay.show_text(cached_by_image.translated_text)
            return

        extracted = self.text_extractor.extract(image)
        normalized_text = self.text_normalizer.normalize(extracted.text)
        if not normalized_text or _looks_like_non_game_text(normalized_text):
            return

        cached_by_text = self.translation_cache.get_by_text(normalized_text)
        if cached_by_text is not None:
            self.image_cache.save_image_result(image_hash, cached_by_text)
            self.overlay.show_text(cached_by_text.translated_text)
            return

        result = self.translator.translate(normalized_text, self._context)
        self.translation_cache.save_translation(result)
        self.image_cache.save_image_result(image_hash, result)
        self._context.append(normalized_text)
        self._context = self._context[-5:]
        self.overlay.show_text(result.translated_text)
