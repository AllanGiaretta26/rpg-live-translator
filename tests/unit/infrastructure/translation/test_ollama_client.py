from __future__ import annotations

import io
import json
from urllib import error

import pytest

from live_translator.infrastructure.translation.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaError,
    OllamaInvalidResponseError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)


def make_http_error(code: int, body: bytes) -> error.HTTPError:
    return error.HTTPError(
        url="http://127.0.0.1:11434/api/generate",
        code=code,
        msg="error",
        hdrs=None,
        fp=io.BytesIO(body),
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


def test_generate_wraps_timeout_inside_urlerror(monkeypatch):
    def fake_urlopen(request, timeout):
        raise error.URLError(TimeoutError("timed out"))

    monkeypatch.setattr(
        "live_translator.infrastructure.translation.ollama_client.request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(OllamaTimeoutError):
        OllamaClient(timeout_seconds=0.01).generate("prompt")


def test_generate_classifies_missing_model_from_http_404(monkeypatch):
    body = json.dumps({"error": 'model "gemma4:e4b" not found'}).encode("utf-8")

    def fake_urlopen(request, timeout):
        raise make_http_error(404, body)

    monkeypatch.setattr(
        "live_translator.infrastructure.translation.ollama_client.request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(OllamaModelNotFoundError) as excinfo:
        OllamaClient(timeout_seconds=0.01).generate("prompt")

    assert 'model "gemma4:e4b" not found' in str(excinfo.value)


def test_generate_reports_http_status_for_server_errors(monkeypatch):
    def fake_urlopen(request, timeout):
        raise make_http_error(500, b"not-json")

    monkeypatch.setattr(
        "live_translator.infrastructure.translation.ollama_client.request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(OllamaError) as excinfo:
        OllamaClient(timeout_seconds=0.01).generate("prompt")

    assert not isinstance(excinfo.value, OllamaConnectionError)
    assert "HTTP 500" in str(excinfo.value)
