from live_translator.infrastructure.translation.prompt_builder import (
    build_translation_prompt,
    build_vision_translation_prompt,
)


def test_vision_prompt_requires_expected_json_only():
    prompt = build_vision_translation_prompt("pt-BR")

    assert "Responda apenas JSON valido" in prompt
    assert "source_text" in prompt
    assert "translated_text" in prompt
    assert '{"source_text": "", "translated_text": ""}' in prompt
    assert "overlay" in prompt


def test_translation_prompt_includes_text_context_and_expected_json():
    prompt = build_translation_prompt("Hello", ["Before"], "pt-BR")

    assert "Hello" in prompt
    assert "Before" in prompt
    assert "<context_only_do_not_translate>" in prompt
    assert "<text_to_translate>" in prompt
    assert "translated_text" in prompt
    assert "source_text" not in prompt


def test_translation_prompt_omits_context_block_when_context_is_empty():
    prompt = build_translation_prompt("Hello", [], "pt-BR")

    assert "<context_only_do_not_translate>" not in prompt
    assert "Use o contexto apenas" not in prompt


def test_translation_prompt_requires_complete_translation_without_summary():
    prompt = build_translation_prompt("Line one.\nLine two.", [], "pt-BR")

    assert "Traduza todo o texto" in prompt
    assert "Nao resuma" in prompt
    assert "Nao omita frases" in prompt


def test_translation_prompt_forbids_translating_context():
    prompt = build_translation_prompt("Current line", ["Previous line"], "pt-BR")

    assert "Nao traduza, copie ou inclua nenhuma linha do contexto" in prompt
    assert "Traduza apenas o texto dentro de <text_to_translate>" in prompt
    assert "Nao inclua falas anteriores" in prompt
