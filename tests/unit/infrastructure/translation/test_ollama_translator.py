import pytest

from live_translator.infrastructure.translation.ollama_client import (
    OllamaInvalidResponseError,
)
from live_translator.infrastructure.translation.ollama_translator import OllamaTranslator


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
