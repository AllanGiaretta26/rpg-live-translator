from __future__ import annotations

import json
from urllib import error

import pytest

from live_translator.infrastructure.translation.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaInvalidResponseError,
    OllamaTimeoutError,
)


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload


def test_generate_parses_nested_json_response(monkeypatch):
    def fake_urlopen(request, timeout):
        return FakeResponse({"response": '{"translated_text": "Ola"}'})

    monkeypatch.setattr(
        "live_translator.infrastructure.translation.ollama_client.request.urlopen",
        fake_urlopen,
    )

    payload = OllamaClient(timeout_seconds=1).generate("prompt")

    assert payload == {"translated_text": "Ola"}


def test_generate_rejects_invalid_nested_json(monkeypatch):
    def fake_urlopen(request, timeout):
        return FakeResponse({"response": "not-json"})

    monkeypatch.setattr(
        "live_translator.infrastructure.translation.ollama_client.request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(OllamaInvalidResponseError):
        OllamaClient(timeout_seconds=1).generate("prompt")


def test_generate_wraps_timeout(monkeypatch):
    def fake_urlopen(request, timeout):
        raise TimeoutError("slow")

    monkeypatch.setattr(
        "live_translator.infrastructure.translation.ollama_client.request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(OllamaTimeoutError):
        OllamaClient(timeout_seconds=0.01).generate("prompt")


def test_generate_wraps_connection_error(monkeypatch):
    def fake_urlopen(request, timeout):
        raise error.URLError("down")

    monkeypatch.setattr(
        "live_translator.infrastructure.translation.ollama_client.request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(OllamaConnectionError):
        OllamaClient(timeout_seconds=0.01).generate("prompt")
