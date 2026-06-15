from live_translator.domain.translation_quality import (
    adds_unexpected_leading_visual_marker,
    invalid_translation_reason,
    looks_like_invalid_translation,
    looks_like_overlong_description,
    looks_like_overlong_name_or_term,
    looks_like_prompt_leak,
    missing_rpg_maker_escape_codes,
    missing_percent_placeholders,
    restore_missing_leading_rpg_maker_escape_codes,
    should_bypass_rpg_maker_translation,
)
from live_translator.domain.models import RpgMakerTextType


def test_prompt_leak_detects_style_guideline_echo():
    # Frases das diretrizes de estilo (_STYLE_GUIDELINES no prompt_builder)
    # ecoadas na resposta devem ser rejeitadas como vazamento de prompt.
    assert looks_like_prompt_leak("Era uma vez.\nEvite traducao literal.")
    assert looks_like_prompt_leak("Idioma destino: pt-BR.\nEra uma vez.")
    assert looks_like_prompt_leak("Como em jogos localizados profissionalmente.")


def test_prompt_leak_accepts_normal_dialogue():
    assert not looks_like_prompt_leak("Voce esta atrasado de novo, heroi.")


def test_invalid_translation_reason_names_the_rejecting_rule():
    assert (
        invalid_translation_reason(
            "Take this.",
            "Leve isto. Preserve nomes proprios. Nao explique.",
        )
        == "prompt_leak"
    )
    assert (
        invalid_translation_reason(r"\N[1], wait!", "Espere!") == "missing_escape_codes"
    )
    assert (
        invalid_translation_reason(
            "Sword",
            "Uma espada muito poderosa forjada pelos antigos",
            text_type=RpgMakerTextType.ITEM_NAME,
        )
        == "overlong_name_or_term"
    )


def test_invalid_translation_reason_is_none_for_valid_translation():
    assert (
        invalid_translation_reason(r"\N[1] found an item.", r"\N[1] achou um item.")
        is None
    )


def test_missing_rpg_maker_escape_codes_detects_dropped_actor_placeholder():
    assert missing_rpg_maker_escape_codes(r"\N[1] found an item.", "[1] achou item.")


def test_missing_rpg_maker_escape_codes_accepts_preserved_codes():
    assert not missing_rpg_maker_escape_codes(
        r"\N[1] found \I[64].",
        r"\N[1] encontrou \I[64].",
    )


def test_restore_missing_leading_rpg_maker_escape_codes_reapplies_text_prefix():
    assert (
        restore_missing_leading_rpg_maker_escape_codes(
            r"\{\{Once upon a time,",
            "Era uma vez,",
        )
        == r"\{\{Era uma vez,"
    )


def test_restore_missing_leading_rpg_maker_escape_codes_reapplies_each_line_prefix():
    assert (
        restore_missing_leading_rpg_maker_escape_codes(
            r"\#Menu Unlocked" "\n" r"\#The Menu screen is now accessible.",
            "Menu desbloqueado\nA tela de menu agora esta acessivel.",
        )
        == r"\#Menu desbloqueado"
        "\n"
        r"\#A tela de menu agora esta acessivel."
    )


def test_invalid_translation_includes_missing_rpg_maker_escape_codes():
    assert looks_like_invalid_translation(r"\N[1] found an item.", "[1] achou item.")


def test_punctuation_only_rpg_maker_text_bypasses_translation():
    assert should_bypass_rpg_maker_translation("...")
    assert should_bypass_rpg_maker_translation(r"\#...")
    assert not should_bypass_rpg_maker_translation(
        r"\#The Empire manipulated countries and laws."
    )


def test_invalid_translation_rejects_expanded_punctuation_only_text():
    assert looks_like_invalid_translation(
        "...",
        "Eu nao sei quem voce e, mas me pediram para falar.",
        text_type=RpgMakerTextType.MESSAGE,
    )


def test_invalid_translation_rejects_added_leading_visual_marker():
    assert adds_unexpected_leading_visual_marker(
        r"\#The Empire manipulated countries and laws.",
        r"\#€O Imperio manipulava paises e leis.",
    )
    assert looks_like_invalid_translation(
        r"\#The Empire manipulated countries and laws.",
        r"\#€O Imperio manipulava paises e leis.",
        text_type=RpgMakerTextType.MESSAGE,
    )


def test_visual_marker_allows_extra_translated_lines_without_marker():
    # Uma tradução que quebra uma única linha de origem em várias linhas não
    # deve ser rejeitada só porque as linhas extras não têm contraparte.
    assert not adds_unexpected_leading_visual_marker(
        "The Empire manipulated countries and laws over many years.",
        "O Imperio manipulava\npaises e leis\nao longo de muitos anos.",
    )


def test_visual_marker_still_detected_on_aligned_line():
    assert adds_unexpected_leading_visual_marker(
        "Line one\nLine two",
        "Linha um\n€Linha dois",
    )


def test_missing_percent_placeholders_detects_removed_battle_placeholder():
    assert missing_percent_placeholders("%1 attacks %2!", "Ataca!")


def test_invalid_translation_includes_missing_percent_placeholders():
    assert looks_like_invalid_translation(
        "%1 attacks %2!",
        "%1 ataca!",
        text_type=RpgMakerTextType.STATE_MESSAGE,
    )


def test_overlong_name_or_term_rejects_sentence_like_name_translation():
    assert looks_like_overlong_name_or_term(
        "Uma pocao que restaura pontos de vida.",
        RpgMakerTextType.ITEM_NAME,
    )


def test_overlong_name_or_term_does_not_reject_system_battle_message():
    assert not looks_like_overlong_name_or_term(
        "%1 recebeu %2 de dano!",
        RpgMakerTextType.SYSTEM_TERM,
    )


def test_overlong_description_rejects_much_longer_ui_text():
    assert looks_like_overlong_description(
        "Restores HP.",
        "Restaura uma enorme quantidade de pontos de vida e tambem explica "
        "detalhadamente como o jogador deve usar este item dentro do menu do jogo.",
        RpgMakerTextType.ITEM_DESCRIPTION,
    )


def test_overlong_description_accepts_compact_two_line_ui_text():
    assert not looks_like_overlong_description(
        "Hits all enemies with a fast piercing strike.",
        "Atinge todos os inimigos com um golpe rapido e perfurante.",
        RpgMakerTextType.SKILL_DESCRIPTION,
    )


def test_overlong_description_rejects_text_that_needs_extra_help_lines():
    assert looks_like_overlong_description(
        "Hits all enemies with a fast piercing strike.",
        "Uma habilidade que atravessa todos os inimigos em um flash e inflige "
        "dano magico continuo por varios turnos enquanto tambem reduz a defesa "
        "e a resistencia elemental de cada alvo atingido.",
        RpgMakerTextType.SKILL_DESCRIPTION,
    )
