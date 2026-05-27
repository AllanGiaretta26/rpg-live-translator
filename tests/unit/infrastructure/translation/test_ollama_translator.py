import pytest

from live_translator.infrastructure.translation.ollama_client import (
    OllamaInvalidResponseError,
)
from live_translator.infrastructure.translation.ollama_translator import OllamaTranslator


class FakeClient:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload
        self.prompt = ""

    def generate(self, prompt: str):
        self.prompt = prompt
        return self.payload


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
