from __future__ import annotations

from infrastructure.translation.ollama_vision_text_extractor import (
    OllamaVisionTextExtractor,
)


class FakeClient:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload

    def encode_image(self, image: object) -> str:
        return "encoded"

    def generate(self, prompt: str, *, images: list[str] | None = None):
        return self.payload


def test_vision_extractor_returns_empty_text_for_prompt_echo():
    extractor = OllamaVisionTextExtractor(
        FakeClient({"source_text": "Voce e um sistema de OCR e traducao para jogos RPG."})
    )

    assert extractor.extract(object()).text == ""


def test_vision_extractor_returns_source_text():
    extractor = OllamaVisionTextExtractor(
        FakeClient({"source_text": "Welcome back, hero."})
    )

    assert extractor.extract(object()).text == "Welcome back, hero."
