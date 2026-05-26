from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from live_translator.domain.interfaces import Translator
from live_translator.domain.models import TranslationResult

from .ollama_client import OllamaClient, OllamaInvalidResponseError
from .prompt_builder import build_translation_prompt


@dataclass(frozen=True, slots=True)
class OllamaTranslator(Translator):
    client: OllamaClient
    source_language: str = "auto"
    target_language: str = "pt-BR"

    def translate(self, text: str, context: Sequence[str]) -> TranslationResult:
        payload = self.client.generate(
            build_translation_prompt(text, context, self.target_language)
        )
        translated_text = payload.get("translated_text")
        if not isinstance(translated_text, str):
            raise OllamaInvalidResponseError("translated_text missing from response")
        return TranslationResult(
            source_text=text,
            translated_text=translated_text,
            source_lang=self.source_language,
            target_lang=self.target_language,
        )
