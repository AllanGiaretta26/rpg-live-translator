import pytest

from live_translator.infrastructure.translation.ollama_client import (
    OllamaInvalidResponseError,
)
from live_translator.infrastructure.translation.ollama_translator import (
    OllamaTranslator,
)
from live_translator.domain.models import RpgMakerTextType


class FakeClient:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload
        self.prompt = ""
        self.prompts: list[str] = []

    def generate(self, prompt: str):
        self.prompt = prompt
        self.prompts.append(prompt)
        return self.payload


class SequenceClient:
    def __init__(self, payloads: list[dict[str, str]]) -> None:
        self.payloads = payloads
        self.prompts: list[str] = []

    def generate(self, prompt: str):
        self.prompts.append(prompt)
        return self.payloads.pop(0)


def test_translator_returns_translation_result():
    client = FakeClient({"translated_text": "Ola mundo"})
    translator = OllamaTranslator(client)

    result = translator.translate("Hello world", [])

    assert result.source_text == "Hello world"
    assert result.translated_text == "Ola mundo"


def test_translator_rejects_blank_translated_text():
    translator = OllamaTranslator(FakeClient({"translated_text": "   "}))

    with pytest.raises(OllamaInvalidResponseError, match="translated_text is empty"):
        translator.translate("Hello world", [])


def test_translator_rejects_response_that_includes_context_lines():
    translator = OllamaTranslator(
        FakeClient(
            {
                "translated_text": (
                    "Mas a gente deveria ficar aqui.\n"
                    "Eu sei, e.\n"
                    "Agora ela vai falar sobre seguranca.\n"
                    "A festa de hoje e especial, certo?"
                )
            }
        )
    )

    with pytest.raises(
        OllamaInvalidResponseError,
        match="translated_text appears to include context",
    ):
        translator.translate("S-Still... today's festival is special, right?", [])


def test_translator_retries_when_response_includes_prompt_instructions():
    client = SequenceClient(
        [
            {
                "translated_text": (
                    "Era uma vez,\n"
                    "Preserve nomes proprios. Nao explique.\n"
                    "Traduza todo o texto de entrada, incluindo todas as linhas."
                )
            },
            {"translated_text": "Era uma vez,"},
        ]
    )
    translator = OllamaTranslator(client)

    result = translator.translate("Once upon a time,", [])

    assert result.translated_text == "Era uma vez,"
    assert len(client.prompts) == 2


def test_translator_rejects_prompt_leak_after_retry():
    translator = OllamaTranslator(
        FakeClient(
            {
                "translated_text": (
                    "Era uma vez,\n"
                    'Responda apenas JSON valido no formato: {"translated_text": "..."}'
                )
            }
        )
    )

    with pytest.raises(
        OllamaInvalidResponseError,
        match="translated_text appears to include prompt instructions",
    ):
        translator.translate("Once upon a time,", [])


def test_translator_retries_when_translation_drops_rpg_maker_escape_code():
    client = SequenceClient(
        [
            {"translated_text": "[1] encontrou um item."},
            {"translated_text": r"\N[1] encontrou um item."},
        ]
    )
    translator = OllamaTranslator(client)

    result = translator.translate(r"\N[1] found an item.", [])

    assert result.translated_text == r"\N[1] encontrou um item."
    assert len(client.prompts) == 2


def test_translator_rejects_missing_rpg_maker_escape_code_after_retry():
    translator = OllamaTranslator(
        FakeClient({"translated_text": "[1] encontrou um item."})
    )

    with pytest.raises(
        OllamaInvalidResponseError,
        match="translated_text drops RPG Maker escape codes",
    ):
        translator.translate(r"\N[1] found an item.", [])


def test_translator_rejects_missing_percent_placeholder_after_retry():
    translator = OllamaTranslator(FakeClient({"translated_text": "%1 ataca!"}))

    with pytest.raises(
        OllamaInvalidResponseError,
        match="translated_text drops RPG Maker placeholders",
    ):
        translator.translate(
            "%1 attacks %2!",
            [],
            text_type=RpgMakerTextType.SKILL_MESSAGE,
        )


def test_translator_uses_text_type_profile_in_prompt():
    client = FakeClient({"translated_text": "Espada"})
    translator = OllamaTranslator(client)

    result = translator.translate(
        "Iron Sword",
        [],
        text_type=RpgMakerTextType.WEAPON_NAME,
    )

    assert result.translated_text == "Espada"
    assert "Perfil do texto: nome de jogo" in client.prompt
