from infrastructure.translation.prompt_builder import (
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
    assert "translated_text" in prompt
    assert "source_text" not in prompt
