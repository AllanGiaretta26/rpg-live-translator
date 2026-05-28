from __future__ import annotations


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


def looks_like_invalid_translation(source_text: str, translated_text: str) -> bool:
    return looks_like_context_leak(
        source_text,
        translated_text,
    ) or looks_like_prompt_leak(translated_text)
