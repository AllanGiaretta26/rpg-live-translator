from __future__ import annotations

from collections import Counter
import re

from live_translator.domain.models import RpgMakerTextType


def _non_empty_line_count(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def looks_like_context_leak(source_text: str, translated_text: str) -> bool:
    source_lines = _non_empty_line_count(source_text)
    translated_lines = _non_empty_line_count(translated_text)
    if source_lines == 0:
        return False
    if source_lines <= 2 and translated_lines > 3:
        return True
    return translated_lines > source_lines + 3


_PROMPT_LEAK_MARKERS = (
    "preserve nomes proprios",
    "preserve nomes próprios",
    "preserve proper names",
    "nao explique",
    "não explique",
    "traduza todo o texto",
    "texto de entrada",
    "responda apenas json",
    "json valido",
    "json válido",
    "translated_text",
    "text_to_translate",
    "nao resuma",
    "não resuma",
    "nao omita",
    "não omita",
    "incluindo todas as linhas",
)


def looks_like_prompt_leak(translated_text: str) -> bool:
    normalized = translated_text.casefold()
    return any(marker in normalized for marker in _PROMPT_LEAK_MARKERS)


_RPG_MAKER_ESCAPE_PATTERN = re.compile(r"\\[A-Za-z]+(?:\[\d+\])?|\\[{}$!.|^<>\\]")
_RPG_MAKER_PERCENT_PLACEHOLDER_PATTERN = re.compile(r"%\d+")

_NAME_OR_TERM_TYPES = frozenset(
    {
        RpgMakerTextType.ITEM_NAME,
        RpgMakerTextType.SKILL_NAME,
        RpgMakerTextType.WEAPON_NAME,
        RpgMakerTextType.ARMOR_NAME,
        RpgMakerTextType.STATE_NAME,
        RpgMakerTextType.CLASS_NAME,
        RpgMakerTextType.ENEMY_NAME,
        RpgMakerTextType.ACTOR_NAME,
        RpgMakerTextType.SYSTEM_TERM,
    }
)
_DESCRIPTION_TYPES = frozenset(
    {
        RpgMakerTextType.ITEM_DESCRIPTION,
        RpgMakerTextType.SKILL_DESCRIPTION,
        RpgMakerTextType.WEAPON_DESCRIPTION,
        RpgMakerTextType.ARMOR_DESCRIPTION,
    }
)
_BATTLE_MESSAGE_TYPES = frozenset(
    {
        RpgMakerTextType.SKILL_MESSAGE,
        RpgMakerTextType.STATE_MESSAGE,
        RpgMakerTextType.TROOP_MESSAGE,
        RpgMakerTextType.TROOP_CHOICE,
        RpgMakerTextType.TROOP_SCROLLING_TEXT,
        RpgMakerTextType.TROOP_SPEAKER,
    }
)


def missing_rpg_maker_escape_codes(source_text: str, translated_text: str) -> bool:
    source_codes = Counter(_RPG_MAKER_ESCAPE_PATTERN.findall(source_text))
    if not source_codes:
        return False

    translated_codes = Counter(_RPG_MAKER_ESCAPE_PATTERN.findall(translated_text))
    return any(translated_codes[code] < count for code, count in source_codes.items())


def missing_percent_placeholders(source_text: str, translated_text: str) -> bool:
    source_codes = Counter(_RPG_MAKER_PERCENT_PLACEHOLDER_PATTERN.findall(source_text))
    if not source_codes:
        return False

    translated_codes = Counter(
        _RPG_MAKER_PERCENT_PLACEHOLDER_PATTERN.findall(translated_text)
    )
    return any(translated_codes[code] < count for code, count in source_codes.items())


def looks_like_overlong_name_or_term(
    translated_text: str,
    text_type: RpgMakerTextType | None,
) -> bool:
    if text_type not in _NAME_OR_TERM_TYPES:
        return False

    normalized = " ".join(translated_text.split())
    if not normalized:
        return False

    word_count = len(re.findall(r"\w+", normalized, flags=re.UNICODE))
    if word_count > 6:
        return True
    if word_count > 4 and re.search(r"[.!?;:]", normalized):
        return True
    return "\n" in translated_text.strip()


def looks_like_overlong_description(
    source_text: str,
    translated_text: str,
    text_type: RpgMakerTextType | None,
) -> bool:
    if text_type not in _DESCRIPTION_TYPES:
        return False

    source_length = len(source_text.strip())
    translated_length = len(translated_text.strip())
    if source_length <= 0:
        return False
    return translated_length > max(source_length * 3, source_length + 120)


def looks_like_invalid_translation(
    source_text: str,
    translated_text: str,
    *,
    text_type: RpgMakerTextType | None = None,
) -> bool:
    return (
        looks_like_context_leak(
            source_text,
            translated_text,
        )
        or looks_like_prompt_leak(translated_text)
        or missing_rpg_maker_escape_codes(source_text, translated_text)
        or missing_percent_placeholders(source_text, translated_text)
        or looks_like_overlong_name_or_term(translated_text, text_type)
        or looks_like_overlong_description(source_text, translated_text, text_type)
    )
