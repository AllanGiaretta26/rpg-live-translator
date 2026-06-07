from __future__ import annotations

from dataclasses import dataclass, field
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from live_translator.infrastructure.rpgmaker import runtime_bridge_server
from live_translator.infrastructure.rpgmaker.runtime_bridge_server import (
    RpgMakerRuntimeBridgeServer,
)


@dataclass
class FakeProcessor:
    texts: list[str] = field(default_factory=list)

    def process_text(self, text: str) -> object | None:
        self.texts.append(text)
        return None


@dataclass
class FailingProcessor:
    def process_text(self, text: str) -> object | None:
        raise RuntimeError("boom")


def _post(endpoint: str, data: bytes) -> tuple[int, dict]:
    request = Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2.0) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def test_runtime_bridge_accepts_posted_text():
    processor = FakeProcessor()
    server = RpgMakerRuntimeBridgeServer(
        host="127.0.0.1",
        port=0,
        processor=processor,
    )
    try:
        assert server.start() is True
        request = Request(
            server.endpoint,
            data=json.dumps({"text": "Hello"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=2.0) as response:
            body = json.loads(response.read().decode("utf-8"))

        assert body == {"ok": True}
        assert processor.texts == ["Hello"]
    finally:
        server.stop()


def test_runtime_bridge_rejects_oversized_body(monkeypatch):
    monkeypatch.setattr(runtime_bridge_server, "MAX_REQUEST_BODY_BYTES", 5)
    processor = FakeProcessor()
    server = RpgMakerRuntimeBridgeServer(host="127.0.0.1", port=0, processor=processor)
    try:
        assert server.start() is True
        status, body = _post(server.endpoint, b"x" * 64)

        assert status == 413
        assert body["ok"] is False
        assert processor.texts == []
    finally:
        server.stop()


def test_runtime_bridge_rejects_malformed_json():
    processor = FakeProcessor()
    server = RpgMakerRuntimeBridgeServer(host="127.0.0.1", port=0, processor=processor)
    try:
        assert server.start() is True
        status, body = _post(server.endpoint, b"not json")

        assert status == 400
        assert body["ok"] is False
        assert processor.texts == []
    finally:
        server.stop()


def test_runtime_bridge_returns_500_on_processor_error():
    server = RpgMakerRuntimeBridgeServer(
        host="127.0.0.1", port=0, processor=FailingProcessor()
    )
    try:
        assert server.start() is True
        status, body = _post(
            server.endpoint, json.dumps({"text": "Hello"}).encode("utf-8")
        )

        assert status == 500
        assert body["ok"] is False
    finally:
        server.stop()
