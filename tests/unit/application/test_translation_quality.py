from live_translator.application.translation_quality import (
    looks_like_invalid_translation,
    looks_like_overlong_description,
    looks_like_overlong_name_or_term,
    missing_rpg_maker_escape_codes,
    missing_percent_placeholders,
)
from live_translator.domain.models import RpgMakerTextType


def test_missing_rpg_maker_escape_codes_detects_dropped_actor_placeholder():
    assert missing_rpg_maker_escape_codes(r"\N[1] found an item.", "[1] achou item.")


def test_missing_rpg_maker_escape_codes_accepts_preserved_codes():
    assert not missing_rpg_maker_escape_codes(
        r"\N[1] found \I[64].",
        r"\N[1] encontrou \I[64].",
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


def test_overlong_description_rejects_much_longer_ui_text():
    assert looks_like_overlong_description(
        "Restores HP.",
        "Restaura uma enorme quantidade de pontos de vida e tambem explica "
        "detalhadamente como o jogador deve usar este item dentro do menu do jogo.",
        RpgMakerTextType.ITEM_DESCRIPTION,
    )
