from __future__ import annotations

from dataclasses import dataclass, field
import json
from urllib.request import Request, urlopen

from live_translator.infrastructure.rpgmaker.runtime_bridge_server import (
    RpgMakerRuntimeBridgeServer,
)


@dataclass
class FakeProcessor:
    texts: list[str] = field(default_factory=list)

    def process_text(self, text: str) -> object | None:
        self.texts.append(text)
        return None


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
