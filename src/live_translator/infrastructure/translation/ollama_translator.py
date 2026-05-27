from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from live_translator.domain.interfaces import Translator
from live_translator.domain.models import TranslationResult

from .ollama_client import OllamaClient, OllamaInvalidResponseError
from .prompt_builder import build_translation_prompt


def _non_empty_line_count(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def _looks_like_context_leak(source_text: str, translated_text: str) -> bool:
    source_lines = _non_empty_line_count(source_text)
    translated_lines = _non_empty_line_count(translated_text)
    if source_lines == 0:
        return False
    if source_lines <= 2 and translated_lines > 3:
        return True
    return translated_lines > source_lines + 3


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
        translated_text = translated_text.strip()
        if not translated_text:
            raise OllamaInvalidResponseError("translated_text is empty")
        if _looks_like_context_leak(text, translated_text):
            raise OllamaInvalidResponseError(
                "translated_text appears to include context"
            )
        return TranslationResult(
            source_text=text,
            translated_text=translated_text,
            source_lang=self.source_language,
            target_lang=self.target_language,
        )
