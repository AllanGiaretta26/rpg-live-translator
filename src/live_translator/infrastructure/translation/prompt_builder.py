from __future__ import annotations

from collections.abc import Sequence

from live_translator.domain.models import RpgMakerTextType
from live_translator.domain.translation_quality import (
    BATTLE_MESSAGE_TYPES,
    DESCRIPTION_TYPES,
    NAME_OR_TERM_TYPES,
    RPG_MAKER_DESCRIPTION_LINE_LIMIT,
    RPG_MAKER_DESCRIPTION_MAX_LINES,
)


# Orcamento de caracteres da descricao compacta, derivado dos limites usados
# por looks_like_overlong_description (52 x 2 linhas), com margem de ~1 palavra
# para o wrap por palavra inteira nao estourar o numero maximo de linhas.
_COMPACT_DESCRIPTION_MAX_CHARS = (
    RPG_MAKER_DESCRIPTION_LINE_LIMIT * RPG_MAKER_DESCRIPTION_MAX_LINES - 9
)

# Blocos compartilhados pelos prompts de traducao — manter uma definicao unica.
_ESCAPE_CODE_GUARDRAILS = (
    "Preserve exatamente codigos RPG Maker como \\N[1], \\V[2], \\C[3], "
    "\\I[64], \\G, \\\\, \\., \\|, \\!, \\>, \\< e \\^.\n"
    "Preserve exatamente placeholders como %1, %2 e %3.\n"
    "Nao traduza, remova ou altere barras invertidas desses codigos.\n"
)
_TOKEN_AND_SYMBOL_GUARDRAILS = (
    "Preserve exatamente marcadores internos como __LT_RPG_TOKEN_0__.\n"
    "Nao adicione simbolos decorativos ou de moeda como €, ¥ ou ￥ se eles "
    "nao existirem no texto original.\n"
)


def build_vision_translation_prompt(target_language: str = "pt-BR") -> str:
    return (
        "Voce e um sistema de OCR e traducao para jogos RPG.\n"
        "Leia o texto visivel na imagem, ignore elementos decorativos e traduza "
        f"para {target_language}.\n"
        "Leia apenas texto de dialogo, menus ou UI do jogo. Ignore qualquer texto "
        "do proprio overlay do tradutor.\n"
        'Se nao houver texto legivel do jogo, responda exatamente {"source_text": "", '
        '"translated_text": ""}.\n'
        "Preserve nomes proprios. Nao explique.\n"
        'Responda apenas JSON valido no formato: {"source_text": "...", '
        '"translated_text": "..."}'
    )


def build_translation_prompt(
    text: str,
    context: Sequence[str] = (),
    target_language: str = "pt-BR",
    *,
    text_type: RpgMakerTextType | None = None,
) -> str:
    context_text = "\n".join(item for item in context[-5:] if item.strip())
    context_section = ""
    if context_text:
        context_section = (
            "Use o contexto apenas para escolher sentido, pronomes e tom.\n"
            "Nao traduza, copie ou inclua nenhuma linha do contexto na resposta.\n"
            f"<context_only_do_not_translate>\n{context_text}\n"
            "</context_only_do_not_translate>\n"
        )
    return (
        "Voce e um tradutor de dialogos de RPG.\n"
        f"Idioma destino: {target_language}.\n"
        f"{context_section}"
        f"<text_to_translate>\n{text}\n"
        "</text_to_translate>\n"
        "Preserve nomes proprios. Nao explique.\n"
        f"{_ESCAPE_CODE_GUARDRAILS}"
        f"{_TOKEN_AND_SYMBOL_GUARDRAILS}"
        f"{_translation_profile_instructions(text_type)}"
        f"{_translation_completion_instructions(text_type)}"
        'Responda apenas JSON valido no formato: {"translated_text": "..."}'
    )


def build_translation_retry_prompt(
    text: str,
    target_language: str = "pt-BR",
    *,
    text_type: RpgMakerTextType | None = None,
) -> str:
    return (
        f"Traduza para {target_language} somente o texto abaixo.\n"
        "Nao inclua instrucoes, explicacoes, chaves extras ou texto anterior.\n"
        f"{_ESCAPE_CODE_GUARDRAILS}"
        f"{_TOKEN_AND_SYMBOL_GUARDRAILS}"
        f"{_translation_profile_instructions(text_type)}"
        'Responda apenas JSON valido: {"translated_text": "..."}\n'
        f"Texto:\n{text}"
    )


def build_compact_description_prompt(
    text: str,
    target_language: str = "pt-BR",
) -> str:
    return (
        f"Traduza para {target_language} como descricao curta de UI de RPG.\n"
        f"Obrigatorio caber em ate {RPG_MAKER_DESCRIPTION_MAX_LINES} linhas "
        "curtas de janela de ajuda.\n"
        f"Use no maximo {_COMPACT_DESCRIPTION_MAX_CHARS} caracteres no total.\n"
        "Preserve numeros, porcentagens, HP, MP, TP, nomes proprios, placeholders "
        "como %1, %2, %3 e codigos RPG Maker como \\N[1], \\V[2], \\C[3], \\I[64].\n"
        f"{_TOKEN_AND_SYMBOL_GUARDRAILS}"
        "Corte floreios e explicacoes; mantenha apenas efeito, alvo, duracao e "
        "restricoes importantes.\n"
        "Exemplo de estilo: 'Dano sombrio em todos. Chance media de Slip.'\n"
        "Nao escreva frase explicativa longa.\n"
        'Responda apenas JSON valido: {"translated_text": "..."}\n'
        f"Texto:\n{text}"
    )


def _translation_profile_instructions(
    text_type: RpgMakerTextType | None,
) -> str:
    if text_type is None:
        return ""
    if text_type in NAME_OR_TERM_TYPES:
        return (
            "Perfil do texto: nome de jogo. Use traducao curta, natural, sem frase "
            "longa e sem ponto final.\n"
        )
    if text_type in DESCRIPTION_TYPES:
        return (
            "Perfil do texto: descricao de item, skill ou equipamento. Use texto curto, "
            "claro e adequado para UI de RPG. Escreva para caber em janela de ajuda "
            "ou batalha: ate duas linhas curtas, sem explicacao longa.\n"
        )
    if text_type == RpgMakerTextType.SYSTEM_TERM:
        return (
            "Perfil do texto: termo de menu ou sistema. Use um termo curto de UI, nao "
            "uma frase explicativa.\n"
        )
    if text_type in BATTLE_MESSAGE_TYPES:
        return (
            "Perfil do texto: mensagem de batalha ou estado. Preserve %1, %2, %3 e "
            "codigos como \\N[1], \\V[2], \\C[3] e \\I[64] exatamente.\n"
        )
    return (
        "Perfil do texto: dialogo ou evento. Traduza de forma natural, completa e "
        "adequada ao tom da cena.\n"
    )


def _translation_completion_instructions(
    text_type: RpgMakerTextType | None,
) -> str:
    if text_type in DESCRIPTION_TYPES:
        return (
            "Traduza apenas o texto dentro de <text_to_translate>.\n"
            "Compacte como descricao de UI: preserve efeito, alvo, numeros e "
            "placeholders, mas corte floreios e explicacoes.\n"
            "Nao inclua falas anteriores. Nao inclua o contexto recente.\n"
        )
    return (
        "Traduza apenas o texto dentro de <text_to_translate>.\n"
        "Traduza todo o texto atual, incluindo todas as linhas e frases.\n"
        "Nao resuma. Nao omita frases. Nao traduza apenas o trecho mais recente.\n"
        "Nao inclua falas anteriores. Nao inclua o contexto recente.\n"
    )
