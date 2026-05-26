from __future__ import annotations

from dataclasses import dataclass

from live_translator.domain.interfaces import TextExtractor
from live_translator.domain.models import ExtractedText

from .ollama_client import OllamaClient, OllamaInvalidResponseError
from .prompt_builder import build_vision_translation_prompt


_PROMPT_ECHO_MARKERS = (
    "sistema de ocr",
    "traducao para jogos rpg",
    "tradução para jogos rpg",
    "responda apenas json",
    "source_text",
    "translated_text",
)


def _looks_like_prompt_echo(text: str) -> bool:
    normalized = text.casefold()
    return any(marker in normalized for marker in _PROMPT_ECHO_MARKERS)


@dataclass(frozen=True, slots=True)
class OllamaVisionTextExtractor(TextExtractor):
    client: OllamaClient
    target_language: str = "pt-BR"

    def extract(self, image: object) -> ExtractedText:
        payload = self.client.generate(
            build_vision_translation_prompt(self.target_language),
            images=[self.client.encode_image(image)],
        )
        source_text = payload.get("source_text")
        if not isinstance(source_text, str):
            raise OllamaInvalidResponseError("source_text missing from vision response")
        if _looks_like_prompt_echo(source_text):
            return ExtractedText(text="")
        return ExtractedText(text=source_text)
