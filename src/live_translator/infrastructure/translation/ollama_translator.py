from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from live_translator.domain.interfaces import Translator
from live_translator.domain.models import RpgMakerTextType, TranslationResult
from live_translator.application.translation_quality import (
    looks_like_overlong_description,
    looks_like_overlong_name_or_term,
    looks_like_context_leak,
    looks_like_prompt_leak,
    missing_rpg_maker_escape_codes,
    missing_percent_placeholders,
    restore_missing_leading_rpg_maker_escape_codes,
)

from .ollama_client import OllamaClient, OllamaInvalidResponseError
from .prompt_builder import (
    build_compact_description_prompt,
    build_translation_prompt,
    build_translation_retry_prompt,
)


_DESCRIPTION_TYPES = frozenset(
    {
        RpgMakerTextType.ITEM_DESCRIPTION,
        RpgMakerTextType.SKILL_DESCRIPTION,
        RpgMakerTextType.WEAPON_DESCRIPTION,
        RpgMakerTextType.ARMOR_DESCRIPTION,
    }
)


@dataclass(frozen=True, slots=True)
class OllamaTranslator(Translator):
    client: OllamaClient
    source_language: str = "auto"
    target_language: str = "pt-BR"

    def translate(
        self,
        text: str,
        context: Sequence[str],
        *,
        text_type: RpgMakerTextType | None = None,
    ) -> TranslationResult:
        prompts = [
            build_translation_prompt(
                text,
                context,
                self.target_language,
                text_type=text_type,
            ),
            build_translation_retry_prompt(
                text,
                self.target_language,
                text_type=text_type,
            ),
        ]
        if text_type in _DESCRIPTION_TYPES:
            prompts.append(build_compact_description_prompt(text, self.target_language))

        last_error: OllamaInvalidResponseError | None = None
        for prompt in prompts:
            payload = self.client.generate(prompt)
            try:
                translated_text = self._validated_translated_text(
                    text,
                    payload,
                    text_type=text_type,
                )
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
        *,
        text_type: RpgMakerTextType | None,
    ) -> str:
        translated_text = payload.get("translated_text")
        if not isinstance(translated_text, str):
            raise OllamaInvalidResponseError("translated_text missing from response")

        translated_text = translated_text.strip()
        if not translated_text:
            raise OllamaInvalidResponseError("translated_text is empty")
        translated_text = restore_missing_leading_rpg_maker_escape_codes(
            source_text,
            translated_text,
        )
        if looks_like_context_leak(source_text, translated_text):
            raise OllamaInvalidResponseError(
                "translated_text appears to include context"
            )
        if looks_like_prompt_leak(translated_text):
            raise OllamaInvalidResponseError(
                "translated_text appears to include prompt instructions"
            )
        if missing_rpg_maker_escape_codes(source_text, translated_text):
            raise OllamaInvalidResponseError(
                "translated_text drops RPG Maker escape codes"
            )
        if missing_percent_placeholders(source_text, translated_text):
            raise OllamaInvalidResponseError(
                "translated_text drops RPG Maker placeholders"
            )
        if looks_like_overlong_name_or_term(translated_text, text_type):
            raise OllamaInvalidResponseError("translated_text is too long for a name")
        if looks_like_overlong_description(source_text, translated_text, text_type):
            raise OllamaInvalidResponseError(
                "translated_text is too long for a description"
            )
        return translated_text
