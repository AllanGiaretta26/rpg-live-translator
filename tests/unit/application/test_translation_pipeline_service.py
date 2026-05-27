from __future__ import annotations

from dataclasses import dataclass, field

from live_translator.application.translation_pipeline_service import TranslationPipelineService
from live_translator.domain.models import ExtractedText, TranslationResult


@dataclass
class StepClock:
    current: float = 0.0
    step: float = 1.0

    def __call__(self) -> float:
        value = self.current
        self.current += self.step
        return value


@dataclass
class FakeChangeDetector:
    changed: bool = True

    def has_changed(self, image: object) -> bool:
        return self.changed


@dataclass
class FakeHasher:
    value: str = "image-hash"

    def hash_image(self, image: object) -> str:
        return self.value


@dataclass
class FakeImageCache:
    result: TranslationResult | None = None
    saved: list[tuple[str, TranslationResult]] = field(default_factory=list)

    def get_by_hash(self, image_hash: str) -> TranslationResult | None:
        return self.result

    def save_image_result(self, image_hash: str, result: TranslationResult) -> None:
        self.saved.append((image_hash, result))


@dataclass
class FakeTranslationCache:
    result: TranslationResult | None = None
    saved: list[TranslationResult] = field(default_factory=list)

    def get_by_text(self, source_text: str) -> TranslationResult | None:
        return self.result

    def save_translation(self, result: TranslationResult) -> None:
        self.saved.append(result)


@dataclass
class FakeExtractor:
    text: str = "Hello"
    calls: int = 0

    def extract(self, image: object) -> ExtractedText:
        self.calls += 1
        return ExtractedText(self.text)


@dataclass
class FakeTranslator:
    calls: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)

    def translate(self, text: str, context: list[str]) -> TranslationResult:
        self.calls.append((text, tuple(context)))
        return TranslationResult(source_text=text, translated_text=f"pt:{text}")


@dataclass
class FailingTranslator:
    message: str = "translated_text is empty"

    def translate(self, text: str, context: list[str]) -> TranslationResult:
        raise ValueError(self.message)


@dataclass
class FakeOverlay:
    shown: list[str] = field(default_factory=list)
    hidden: int = 0

    def show_text(self, text: str) -> None:
        self.shown.append(text)

    def hide(self) -> None:
        self.hidden += 1


def build_pipeline(**overrides):
    parts = {
        "text_extractor": FakeExtractor(),
        "translator": FakeTranslator(),
        "translation_cache": FakeTranslationCache(),
        "image_cache": FakeImageCache(),
        "image_hasher": FakeHasher(),
        "change_detector": FakeChangeDetector(),
        "overlay": FakeOverlay(),
    }
    parts.update(overrides)
    return TranslationPipelineService(**parts), parts


def test_cache_by_image_avoids_ocr_and_translation():
    cached = TranslationResult(source_text="Hello", translated_text="Ola")
    extractor = FakeExtractor()
    translator = FakeTranslator()
    pipeline, parts = build_pipeline(
        image_cache=FakeImageCache(result=cached),
        text_extractor=extractor,
        translator=translator,
        clock=StepClock(step=0.25),
    )

    pipeline.process_frame(object())

    assert extractor.calls == 0
    assert translator.calls == []
    assert parts["overlay"].shown == ["Ola"]
    assert pipeline.last_diagnostic == "cache imagem"
    assert pipeline.last_timing_summary == "total 0.25s | cache imagem"


def test_cache_by_text_avoids_translation_and_saves_image_cache():
    cached = TranslationResult(source_text="Hello", translated_text="Ola")
    image_cache = FakeImageCache()
    translator = FakeTranslator()
    pipeline, parts = build_pipeline(
        translation_cache=FakeTranslationCache(result=cached),
        image_cache=image_cache,
        translator=translator,
        clock=StepClock(step=1.0),
    )

    pipeline.process_frame(object())

    assert translator.calls == []
    assert image_cache.saved == [("image-hash", cached)]
    assert parts["overlay"].shown == ["Ola"]
    assert pipeline.last_diagnostic == "cache texto"
    assert pipeline.last_timing_summary == "total 3.00s | ocr 1.00s | cache texto"


def test_empty_text_does_not_update_overlay_or_translate():
    translator = FakeTranslator()
    pipeline, parts = build_pipeline(
        text_extractor=FakeExtractor(text="   "),
        translator=translator,
    )

    pipeline.process_frame(object())

    assert translator.calls == []
    assert parts["overlay"].hidden == 0
    assert parts["overlay"].shown == []
    assert pipeline.last_diagnostic == "sem texto"


def test_prompt_like_text_does_not_update_overlay_or_translate():
    translator = FakeTranslator()
    pipeline, parts = build_pipeline(
        text_extractor=FakeExtractor(
            text="Voce e um sistema de OCR e traducao para jogos RPG."
        ),
        translator=translator,
    )

    pipeline.process_frame(object())

    assert translator.calls == []
    assert parts["overlay"].hidden == 0
    assert parts["overlay"].shown == []
    assert pipeline.last_diagnostic == "sem texto"


def test_cache_miss_translates_saves_without_context():
    translator = FakeTranslator()
    translation_cache = FakeTranslationCache()
    image_cache = FakeImageCache()
    extractor = FakeExtractor()
    pipeline, parts = build_pipeline(
        text_extractor=extractor,
        translator=translator,
        translation_cache=translation_cache,
        image_cache=image_cache,
        clock=StepClock(step=1.0),
    )

    for index in range(6):
        extractor.text = f"Line {index}"
        parts["image_hasher"].value = f"hash-{index}"
        pipeline.process_frame(object())

    assert [call[0] for call in translator.calls] == [f"Line {i}" for i in range(6)]
    assert [call[1] for call in translator.calls] == [() for _ in range(6)]
    assert pipeline.context == ()
    assert pipeline.last_diagnostic == "traduzido"
    assert (
        pipeline.last_timing_summary
        == "total 5.00s | ocr 1.00s | traducao 1.00s | cache miss"
    )
    assert len(translation_cache.saved) == 6
    assert len(image_cache.saved) == 6


def test_unchanged_image_records_diagnostic_without_processing():
    extractor = FakeExtractor()
    pipeline, parts = build_pipeline(
        change_detector=FakeChangeDetector(changed=False),
        text_extractor=extractor,
        clock=StepClock(step=0.5),
    )

    pipeline.process_frame(object())

    assert extractor.calls == 0
    assert parts["overlay"].shown == []
    assert pipeline.last_diagnostic == "sem mudanca"
    assert pipeline.last_timing_summary == "total 0.50s | sem mudanca"


def test_translation_failure_records_clear_diagnostic_and_does_not_update_overlay():
    pipeline, parts = build_pipeline(
        translator=FailingTranslator(),
        clock=StepClock(step=1.0),
    )

    try:
        pipeline.process_frame(object())
    except ValueError:
        pass

    assert pipeline.last_diagnostic == "traducao falhou: translated_text is empty"
    assert (
        pipeline.last_timing_summary
        == "total 5.00s | ocr 1.00s | traducao 1.00s | erro"
    )
    assert parts["overlay"].shown == []
