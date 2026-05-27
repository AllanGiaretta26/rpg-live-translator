from __future__ import annotations

from collections.abc import Sequence


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
        "Voce e um tradutor de dialogos de RPG para portugues brasileiro.\n"
        f"Idioma destino: {target_language}.\n"
        f"{context_section}"
        f"<text_to_translate>\n{text}\n"
        "</text_to_translate>\n"
        "Preserve nomes proprios. Nao explique.\n"
        "Traduza apenas o texto dentro de <text_to_translate>.\n"
        "Traduza todo o texto atual, incluindo todas as linhas e frases.\n"
        "Nao resuma. Nao omita frases. Nao traduza apenas o trecho mais recente.\n"
        "Nao inclua falas anteriores. Nao inclua o contexto recente.\n"
        'Responda apenas JSON valido no formato: {"translated_text": "..."}'
    )
