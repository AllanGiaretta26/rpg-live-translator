from live_translator.infrastructure.translation.prompt_builder import (
    build_compact_description_prompt,
    build_translation_prompt,
    build_vision_ocr_prompt,
)
from live_translator.domain.models import RpgMakerTextType


def test_vision_prompt_is_ocr_only():
    prompt = build_vision_ocr_prompt()

    assert "Responda apenas JSON valido" in prompt
    assert "source_text" in prompt
    # OCR-only: a traducao acontece em chamada separada; pedir translated_text
    # aqui gastava tokens por frame e degradava a transcricao.
    assert "translated_text" not in prompt
    assert "sem traduzir" in prompt
    assert '{"source_text": ""}' in prompt
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


def test_translation_prompt_includes_style_guidelines():
    prompt = build_translation_prompt("Hello", [], "pt-BR")

    assert "Traduza com naturalidade" in prompt
    assert "evite traducao literal palavra por palavra" in prompt
    assert "Mantenha o tom da cena" in prompt
    assert "HP, MP, TP e EXP" in prompt


def test_translation_prompt_puts_text_to_translate_after_instructions():
    prompt = build_translation_prompt("Hello", ["Before"], "pt-BR")

    # Texto por ultimo: modelos locais seguem melhor regras que antecedem o
    # payload; apenas a linha de formato JSON fecha o prompt. A ancora inclui
    # o payload porque a tag tambem e citada nas instrucoes.
    text_block_at = prompt.index("<text_to_translate>\nHello")
    assert text_block_at > prompt.index("Preserve exatamente codigos RPG Maker")
    assert text_block_at > prompt.index("<context_only_do_not_translate>")


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
    assert "__LT_RPG_TOKEN_0__" in prompt


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
    assert "ate duas linhas curtas" in prompt
    assert "Compacte como descricao de UI" in prompt
    assert "Nao resuma" not in prompt


def test_compact_description_prompt_preserves_ui_tokens():
    prompt = build_compact_description_prompt(
        "Restores 20% HP and TP.",
        "pt-BR",
    )

    assert "ate 2 linhas curtas" in prompt
    # Orcamento derivado dos limites de descricao do domain (52 x 2 - 9).
    assert "95 caracteres" in prompt
    assert "Dano sombrio em todos" in prompt
    assert "__LT_RPG_TOKEN_0__" in prompt
    assert "HP" in prompt
    assert "TP" in prompt
    assert "%1" in prompt
    assert r"\N[1]" in prompt


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
