from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from live_translator.domain.interfaces import Translator
from live_translator.domain.models import TranslationResult
from live_translator.application.translation_quality import (
    looks_like_context_leak,
    looks_like_prompt_leak,
)

from .ollama_client import OllamaClient, OllamaInvalidResponseError
from .prompt_builder import build_translation_prompt, build_translation_retry_prompt


@dataclass(frozen=True, slots=True)
class OllamaTranslator(Translator):
    client: OllamaClient
    source_language: str = "auto"
    target_language: str = "pt-BR"

    def translate(self, text: str, context: Sequence[str]) -> TranslationResult:
        prompts = (
            build_translation_prompt(text, context, self.target_language),
            build_translation_retry_prompt(text, self.target_language),
        )
        last_error: OllamaInvalidResponseError | None = None
        for prompt in prompts:
            payload = self.client.generate(prompt)
            try:
                translated_text = self._validated_translated_text(text, payload)
            except OllamaInvalidResponseError as error:
                last_error = error
                continue

            return TranslationResult(
                source_text=text,
                translated_text=translated_text,
                source_lang=self.source_language,
                target_lang=self.target_language,
            )

        if last_error is not None:
            raise last_error
        raise OllamaInvalidResponseError("translated_text missing from response")

    def _validated_translated_text(
        self,
        source_text: str,
        payload: dict[str, object],
    ) -> str:
        translated_text = payload.get("translated_text")
        if not isinstance(translated_text, str):
            raise OllamaInvalidResponseError("translated_text missing from response")

        translated_text = translated_text.strip()
        if not translated_text:
            raise OllamaInvalidResponseError("translated_text is empty")
        if looks_like_context_leak(source_text, translated_text):
            raise OllamaInvalidResponseError(
                "translated_text appears to include context"
            )
        if looks_like_prompt_leak(translated_text):
            raise OllamaInvalidResponseError(
                "translated_text appears to include prompt instructions"
            )
        return translated_text
