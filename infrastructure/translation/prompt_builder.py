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
    context_text = "\n".join(context[-5:])
    return (
        "Voce e um tradutor de dialogos de RPG para portugues brasileiro.\n"
        f"Idioma destino: {target_language}.\n"
        f"Contexto recente:\n{context_text}\n"
        f"Texto para traduzir:\n{text}\n"
        "Preserve nomes proprios. Nao explique.\n"
        'Responda apenas JSON valido no formato: {"translated_text": "..."}'
    )
