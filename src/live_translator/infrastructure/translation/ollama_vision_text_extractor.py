from __future__ import annotations

from dataclasses import dataclass

from live_translator.domain.interfaces import TextExtractor
from live_translator.domain.models import ExtractedText
from live_translator.domain.translation_quality import looks_like_non_game_text

from .ollama_client import OllamaClient, OllamaInvalidResponseError
from .prompt_builder import build_vision_ocr_prompt


@dataclass(frozen=True, slots=True)
class OllamaVisionTextExtractor(TextExtractor):
    client: OllamaClient

    def extract(self, image: object) -> ExtractedText:
        payload = self.client.generate(
            build_vision_ocr_prompt(),
            images=[self.client.encode_image(image)],
        )
        source_text = payload.get("source_text")
        if not isinstance(source_text, str):
            raise OllamaInvalidResponseError("source_text missing from vision response")
        if looks_like_non_game_text(source_text):
            return ExtractedText(text="")
        return ExtractedText(text=source_text)
