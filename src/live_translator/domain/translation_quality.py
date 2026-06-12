from __future__ import annotations

from collections import Counter
import re
import textwrap

from live_translator.domain.models import RpgMakerTextType


RPG_MAKER_DESCRIPTION_LINE_LIMIT = 52
RPG_MAKER_DESCRIPTION_MAX_LINES = 2


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
    # Frases distintivas das diretrizes de estilo do prompt principal
    # (_STYLE_GUIDELINES em infrastructure/translation/prompt_builder.py).
    "idioma destino",
    "traducao literal",
    "tradução literal",
    "localizados profissionalmente",
)


def looks_like_prompt_leak(translated_text: str) -> bool:
    normalized = translated_text.casefold()
    return any(marker in normalized for marker in _PROMPT_LEAK_MARKERS)


# Texto extraido por OCR que na verdade e eco do prompt de visao ou texto do
# proprio overlay do tradutor — nunca deve ser tratado como fala do jogo.
# Compartilhado pelo pipeline universal e pelo extrator de visao.
_NON_GAME_TEXT_MARKERS = (
    "voce e um sistema",
    "você é um sistema",
    "sistema de ocr",
    "ocr e traducao",
    "ocr e tradução",
    "traducao para jogos rpg",
    "tradução para jogos rpg",
    "responda apenas json",
    "source_text",
    "translated_text",
    "live translator",
    "aguardando texto",
)


def looks_like_non_game_text(text: str) -> bool:
    normalized = text.casefold()
    return any(marker in normalized for marker in _NON_GAME_TEXT_MARKERS)


_RPG_MAKER_ESCAPE_PATTERN = re.compile(r"\\[A-Za-z]+(?:\[\d+\])?|\\[{}$!.|^<>#\\]")
_RPG_MAKER_PERCENT_PLACEHOLDER_PATTERN = re.compile(r"%\d+")
_RPG_MAKER_LEADING_ESCAPE_SEQUENCE_PATTERN = re.compile(
    r"^(?P<prefix>(?:\\[{}$!.|^<>#\\])+)(?P<rest>.*)$",
    flags=re.DOTALL,
)
_RPG_MAKER_TOKEN_PATTERN = re.compile(r"%\d+|\\[A-Za-z]+(?:\[\d+\])?|\\[{}$!.|^<>#\\]")
_UNEXPECTED_LEADING_VISUAL_MARKERS = ("€", "¥", "￥")

# Conjuntos compartilhados de tipos de texto MV/MZ. Tambem usados pelo
# prompt_builder e pelo OllamaTranslator — manter uma definicao unica.
NAME_OR_TERM_TYPES = frozenset(
    {
        RpgMakerTextType.ITEM_NAME,
        RpgMakerTextType.SKILL_NAME,
        RpgMakerTextType.WEAPON_NAME,
        RpgMakerTextType.ARMOR_NAME,
        RpgMakerTextType.STATE_NAME,
        RpgMakerTextType.CLASS_NAME,
        RpgMakerTextType.ENEMY_NAME,
        RpgMakerTextType.ACTOR_NAME,
    }
)
DESCRIPTION_TYPES = frozenset(
    {
        RpgMakerTextType.ITEM_DESCRIPTION,
        RpgMakerTextType.SKILL_DESCRIPTION,
        RpgMakerTextType.WEAPON_DESCRIPTION,
        RpgMakerTextType.ARMOR_DESCRIPTION,
    }
)
BATTLE_MESSAGE_TYPES = frozenset(
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


def restore_missing_leading_rpg_maker_escape_codes(
    source_text: str,
    translated_text: str,
) -> str:
    source_lines = source_text.splitlines()
    translated_lines = translated_text.splitlines()
    if source_lines and len(source_lines) == len(translated_lines):
        return "\n".join(
            _restore_missing_leading_rpg_maker_escape_codes_for_line(
                source_line,
                translated_line,
            )
            for source_line, translated_line in zip(
                source_lines,
                translated_lines,
                strict=True,
            )
        )

    return _restore_missing_leading_rpg_maker_escape_codes_for_line(
        source_text,
        translated_text,
    )


def _restore_missing_leading_rpg_maker_escape_codes_for_line(
    source_line: str,
    translated_line: str,
) -> str:
    source_match = _RPG_MAKER_LEADING_ESCAPE_SEQUENCE_PATTERN.match(source_line)
    if source_match is None:
        return translated_line

    source_prefix = source_match.group("prefix")
    translated_match = _RPG_MAKER_LEADING_ESCAPE_SEQUENCE_PATTERN.match(translated_line)
    translated_rest = (
        translated_match.group("rest")
        if translated_match is not None
        else translated_line
    )
    if translated_line.startswith(source_prefix):
        return translated_line
    return f"{source_prefix}{translated_rest.lstrip()}"


def should_bypass_rpg_maker_translation(source_text: str) -> bool:
    visible_text = _RPG_MAKER_TOKEN_PATTERN.sub("", source_text).strip()
    if not visible_text:
        return True
    return not any(character.isalnum() for character in visible_text)


def looks_like_non_translatable_expansion(
    source_text: str,
    translated_text: str,
) -> bool:
    if not should_bypass_rpg_maker_translation(source_text):
        return False
    return translated_text.strip() != source_text.strip()


def adds_unexpected_leading_visual_marker(
    source_text: str,
    translated_text: str,
) -> bool:
    source_lines = source_text.splitlines()
    translated_lines = translated_text.splitlines()
    if not source_lines:
        source_lines = [source_text]
    if not translated_lines:
        translated_lines = [translated_text]

    for index, translated_line in enumerate(translated_lines):
        # Only compare lines that have a matching source line. A translation that
        # legitimately wraps into more lines must not be rejected just because the
        # extra lines have no source counterpart to compare against.
        if index >= len(source_lines):
            break
        source_line = source_lines[index]
        source_rest = _line_without_leading_rpg_maker_escape_codes(source_line)
        translated_rest = _line_without_leading_rpg_maker_escape_codes(translated_line)
        for marker in _UNEXPECTED_LEADING_VISUAL_MARKERS:
            if translated_rest.startswith(marker) and not source_rest.startswith(
                marker
            ):
                return True
    return False


def _line_without_leading_rpg_maker_escape_codes(line: str) -> str:
    match = _RPG_MAKER_LEADING_ESCAPE_SEQUENCE_PATTERN.match(line)
    if match is None:
        return line.lstrip()
    return match.group("rest").lstrip()


def looks_like_overlong_name_or_term(
    translated_text: str,
    text_type: RpgMakerTextType | None,
) -> bool:
    if text_type not in NAME_OR_TERM_TYPES:
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
    if text_type not in DESCRIPTION_TYPES:
        return False

    source_length = len(source_text.strip())
    normalized = " ".join(translated_text.split())
    translated_length = len(normalized)
    if source_length <= 0:
        return False
    if translated_length > max(source_length * 2, source_length + 80):
        return True

    wrapped_lines = textwrap.wrap(
        normalized,
        width=RPG_MAKER_DESCRIPTION_LINE_LIMIT,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if len(wrapped_lines) > RPG_MAKER_DESCRIPTION_MAX_LINES:
        return True

    return any(
        len(word) > RPG_MAKER_DESCRIPTION_LINE_LIMIT
        for word in re.findall(r"\S+", normalized, flags=re.UNICODE)
    )


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
        or looks_like_non_translatable_expansion(source_text, translated_text)
        or looks_like_prompt_leak(translated_text)
        or adds_unexpected_leading_visual_marker(source_text, translated_text)
        or missing_rpg_maker_escape_codes(source_text, translated_text)
        or missing_percent_placeholders(source_text, translated_text)
        or looks_like_overlong_name_or_term(translated_text, text_type)
        or looks_like_overlong_description(source_text, translated_text, text_type)
    )
