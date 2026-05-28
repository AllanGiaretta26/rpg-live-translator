from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from live_translator.application.rpg_maker_runtime_service import RpgMakerRuntimeService
from live_translator.domain.models import OperationMode, TranslationResult


@dataclass
class FakeModeSettings:
    mode: OperationMode = OperationMode.RPG_MAKER_MV_MZ

    def get_active_mode(self) -> OperationMode:
        return self.mode


@dataclass
class FakeCache:
    result: TranslationResult | None = None
    results: dict[str, TranslationResult] = field(default_factory=dict)
    saved: list[TranslationResult] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    def get_by_text(self, source_text: str) -> TranslationResult | None:
        if source_text in self.results:
            return self.results[source_text]
        return self.result

    def save_translation(self, result: TranslationResult) -> None:
        self.saved.append(result)

    def delete_by_text(self, source_text: str) -> bool:
        self.deleted.append(source_text)
        return self.results.pop(source_text, None) is not None


@dataclass
class FakeTranslator:
    calls: list[str] = field(default_factory=list)

    def translate(self, text: str, context: Sequence[str]) -> TranslationResult:
        self.calls.append(text)
        return TranslationResult(source_text=text, translated_text=f"pt:{text}")


@dataclass
class ReentrantTranslator:
    service: RpgMakerRuntimeService | None = None
    calls: list[str] = field(default_factory=list)

    def translate(self, text: str, context: Sequence[str]) -> TranslationResult:
        self.calls.append(text)
        if text == "Old" and self.service is not None:
            self.service.process_text("New")
        return TranslationResult(source_text=text, translated_text=f"pt:{text}")


@dataclass
class FakeOverlay:
    shown: list[str] = field(default_factory=list)

    def show_text(self, text: str) -> None:
        self.shown.append(text)

    def hide(self) -> None:
        return


@dataclass
class StepClock:
    current: float = 0.0
    step: float = 1.0

    def __call__(self) -> float:
        value = self.current
        self.current += self.step
        return value


def test_runtime_text_ignored_outside_rpg_maker_mode():
    cache = FakeCache()
    translator = FakeTranslator()
    overlay = FakeOverlay()
    service = RpgMakerRuntimeService(
        mode_settings=FakeModeSettings(OperationMode.UNIVERSAL),
        translation_cache=cache,
        translator=translator,
        overlay=overlay,
    )

    result = service.process_text("Hello")

    assert result is None
    assert translator.calls == []
    assert overlay.shown == []
    assert service.last_diagnostic == "ignorado: modo universal"


def test_runtime_text_uses_cache_and_updates_overlay():
    cached = TranslationResult(source_text="Hello", translated_text="Ola")
    cache = FakeCache(result=cached)
    translator = FakeTranslator()
    overlay = FakeOverlay()
    service = RpgMakerRuntimeService(
        mode_settings=FakeModeSettings(),
        translation_cache=cache,
        translator=translator,
        overlay=overlay,
        clock=StepClock(step=0.5),
    )

    result = service.process_text("  Hello  ")

    assert result == cached
    assert translator.calls == []
    assert overlay.shown == ["Ola"]
    assert service.last_source_text == "Hello"
    assert service.last_diagnostic == "runtime cache texto"
    assert service.last_timing_summary == "runtime total 0.50s"


def test_runtime_text_ignores_contaminated_cache_and_retranslates():
    cached = TranslationResult(
        source_text="Hello",
        translated_text=(
            "Ola\n"
            "Preserve nomes proprios. Nao explique.\n"
            "Responda apenas JSON valido."
        ),
    )
    cache = FakeCache(result=cached)
    translator = FakeTranslator()
    overlay = FakeOverlay()
    service = RpgMakerRuntimeService(
        mode_settings=FakeModeSettings(),
        translation_cache=cache,
        translator=translator,
        overlay=overlay,
    )

    result = service.process_text("Hello")

    assert result is not None
    assert result.translated_text == "pt:Hello"
    assert translator.calls == ["Hello"]
    assert cache.saved == [result]
    assert overlay.shown == ["pt:Hello"]


def test_runtime_text_translates_cache_miss_and_updates_overlay():
    cache = FakeCache()
    translator = FakeTranslator()
    overlay = FakeOverlay()
    service = RpgMakerRuntimeService(
        mode_settings=FakeModeSettings(),
        translation_cache=cache,
        translator=translator,
        overlay=overlay,
        clock=StepClock(step=1.0),
    )

    result = service.process_text("Hello")

    assert result is not None
    assert result.translated_text == "pt:Hello"
    assert translator.calls == ["Hello"]
    assert cache.saved == [result]
    assert overlay.shown == ["pt:Hello"]
    assert service.last_diagnostic == "runtime traduzido"
    assert service.last_timing_summary == (
        "runtime total 3.00s | traducao 1.00s | cache miss"
    )


def test_stale_runtime_translation_does_not_overwrite_newer_overlay():
    cache = FakeCache(
        results={
            "New": TranslationResult(source_text="New", translated_text="pt:New"),
        }
    )
    translator = ReentrantTranslator()
    overlay = FakeOverlay()
    service = RpgMakerRuntimeService(
        mode_settings=FakeModeSettings(),
        translation_cache=cache,
        translator=translator,
        overlay=overlay,
    )
    translator.service = service

    result = service.process_text("Old")

    assert result is not None
    assert result.translated_text == "pt:Old"
    assert translator.calls == ["Old"]
    assert overlay.shown == ["pt:New"]
    assert service.last_source_text == "New"


def test_reprocess_last_text_deletes_cache_and_translates_again():
    cache = FakeCache(
        results={
            "Hello": TranslationResult(source_text="Hello", translated_text="Ola"),
        }
    )
    translator = FakeTranslator()
    overlay = FakeOverlay()
    service = RpgMakerRuntimeService(
        mode_settings=FakeModeSettings(),
        translation_cache=cache,
        translator=translator,
        overlay=overlay,
    )
    service.process_text("Hello")

    result = service.reprocess_last_text()

    assert result is not None
    assert result.translated_text == "pt:Hello"
    assert cache.deleted == ["Hello"]
    assert translator.calls == ["Hello"]
    assert overlay.shown == ["Ola", "pt:Hello"]


def test_reprocess_last_text_without_source_updates_diagnostic():
    service = RpgMakerRuntimeService(
        mode_settings=FakeModeSettings(),
        translation_cache=FakeCache(),
        translator=FakeTranslator(),
        overlay=FakeOverlay(),
    )

    result = service.reprocess_last_text()

    assert result is None
    assert service.last_diagnostic == "runtime sem fala atual para reprocessar"
