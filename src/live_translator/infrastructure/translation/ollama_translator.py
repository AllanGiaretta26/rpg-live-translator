from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import re

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
_MASKABLE_RPG_MAKER_TOKEN_PATTERN = re.compile(
    r"%\d+|\\[A-Za-z]+(?:\[\d+\])?|\\[{}$!.|^<>#\\]"
)


@dataclass(frozen=True, slots=True)
class _MaskedRpgMakerText:
    text: str
    replacements: tuple[tuple[str, str], ...]

    def restore(self, text: str) -> str:
        restored = text
        for marker, original in self.replacements:
            restored = restored.replace(marker, original)
        return restored


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
        masked_text = _mask_rpg_maker_tokens(text)
        prompts = [
            build_translation_prompt(
                masked_text.text,
                context,
                self.target_language,
                text_type=text_type,
            ),
            build_translation_retry_prompt(
                masked_text.text,
                self.target_language,
                text_type=text_type,
            ),
        ]
        if text_type in _DESCRIPTION_TYPES:
            prompts.append(
                build_compact_description_prompt(
                    masked_text.text,
                    self.target_language,
                )
            )

        last_error: OllamaInvalidResponseError | None = None
        for prompt in prompts:
            payload = self.client.generate(prompt)
            try:
                translated_text = self._validated_translated_text(
                    text,
                    payload,
                    text_type=text_type,
                    masked_text=masked_text,
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
        masked_text: _MaskedRpgMakerText,
    ) -> str:
        translated_text = payload.get("translated_text")
        if not isinstance(translated_text, str):
            raise OllamaInvalidResponseError("translated_text missing from response")

        translated_text = translated_text.strip()
        if not translated_text:
            raise OllamaInvalidResponseError("translated_text is empty")
        translated_text = masked_text.restore(translated_text)
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


def _mask_rpg_maker_tokens(text: str) -> _MaskedRpgMakerText:
    replacements: list[tuple[str, str]] = []

    def _replace(match: re.Match[str]) -> str:
        marker = f"__LT_RPG_TOKEN_{len(replacements)}__"
        replacements.append((marker, match.group(0)))
        return marker

    masked_text = _MASKABLE_RPG_MAKER_TOKEN_PATTERN.sub(_replace, text)
    return _MaskedRpgMakerText(masked_text, tuple(replacements))
