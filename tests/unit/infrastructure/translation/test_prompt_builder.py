from live_translator.infrastructure.translation.prompt_builder import (
    build_translation_prompt,
    build_vision_translation_prompt,
)
from live_translator.domain.models import RpgMakerTextType


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


def test_translation_prompt_requires_preserving_rpg_maker_escape_codes():
    prompt = build_translation_prompt(r"\N[1] found \I[64].", [], "pt-BR")

    assert r"\N[1]" in prompt
    assert r"\V[2]" in prompt
    assert "Preserve exatamente codigos RPG Maker" in prompt
    assert "barras invertidas" in prompt


def test_translation_prompt_includes_name_profile_for_catalog_names():
    prompt = build_translation_prompt(
        "Iron Sword",
        [],
        "pt-BR",
        text_type=RpgMakerTextType.WEAPON_NAME,
    )

    assert "Perfil do texto: nome de jogo" in prompt
    assert "sem frase longa" in prompt


def test_translation_prompt_includes_description_fit_profile():
    prompt = build_translation_prompt(
        "Hits all enemies with a fast piercing strike.",
        [],
        "pt-BR",
        text_type=RpgMakerTextType.SKILL_DESCRIPTION,
    )

    assert "descricao de item, skill ou equipamento" in prompt
    assert "janela de ajuda ou batalha" in prompt
    assert "no maximo duas linhas curtas" in prompt


def test_translation_prompt_includes_battle_placeholder_profile():
    prompt = build_translation_prompt(
        "%1 casts %2!",
        [],
        "pt-BR",
        text_type=RpgMakerTextType.SKILL_MESSAGE,
    )

    assert "mensagem de batalha ou estado" in prompt
    assert "%1" in prompt
    assert "%2" in prompt
