from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from threading import Thread
from typing import Callable, Protocol

logger = logging.getLogger(__name__)


class RuntimeTextProcessor(Protocol):
    def process_text(self, text: str) -> object | None:
        """Process one text line received from RPG Maker runtime."""


@dataclass(slots=True)
class RpgMakerRuntimeBridgeServer:
    host: str
    port: int
    processor: RuntimeTextProcessor
    _server: ThreadingHTTPServer | None = field(default=None, init=False, repr=False)
    _thread: Thread | None = field(default=None, init=False, repr=False)
    _last_error: str | None = field(default=None, init=False, repr=False)

    @property
    def endpoint(self) -> str:
        port = self.port
        if self._server is not None:
            port = int(self._server.server_address[1])
        return f"http://{self.host}:{port}/rpgmaker/text"

    @property
    def is_running(self) -> bool:
        return self._server is not None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def start(self) -> bool:
        if self._server is not None:
            return True

        handler = self._make_handler(self.processor)
        try:
            self._server = ThreadingHTTPServer((self.host, self.port), handler)
        except OSError as error:
            self._last_error = str(error) or error.__class__.__name__
            logger.exception("failed to start RPG Maker bridge server")
            return False

        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._last_error = None
        return True

    def stop(self) -> None:
        if self._server is None:
            return

        server = self._server
        self._server = None
        server.shutdown()
        server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _make_handler(
        self,
        processor: RuntimeTextProcessor,
    ) -> Callable[..., BaseHTTPRequestHandler]:
        class Handler(BaseHTTPRequestHandler):
            def do_OPTIONS(self) -> None:
                self._send_empty(204)

            def do_POST(self) -> None:
                if self.path != "/rpgmaker/text":
                    self._send_json(404, {"ok": False, "error": "not found"})
                    return

                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length)
                    payload = json.loads(body.decode("utf-8"))
                    text = payload.get("text", "")
                    if not isinstance(text, str):
                        raise ValueError("text must be a string")
                    processor.process_text(text)
                except Exception as error:
                    self._send_json(400, {"ok": False, "error": str(error)})
                    return

                self._send_json(200, {"ok": True})

            def log_message(self, format: str, *args: object) -> None:
                logger.debug("RPG Maker bridge: " + format, *args)

            def _send_empty(self, status: int) -> None:
                self.send_response(status)
                self._send_cors_headers()
                self.end_headers()

            def _send_json(self, status: int, payload: dict[str, object]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_cors_headers(self) -> None:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "content-type")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

        return Handler
