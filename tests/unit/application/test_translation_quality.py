from live_translator.application.translation_quality import (
    looks_like_invalid_translation,
    looks_like_overlong_description,
    looks_like_overlong_name_or_term,
    missing_rpg_maker_escape_codes,
    missing_percent_placeholders,
    restore_missing_leading_rpg_maker_escape_codes,
)
from live_translator.domain.models import RpgMakerTextType


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


def test_invalid_translation_includes_missing_rpg_maker_escape_codes():
    assert looks_like_invalid_translation(r"\N[1] found an item.", "[1] achou item.")


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
