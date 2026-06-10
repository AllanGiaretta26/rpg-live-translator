from __future__ import annotations

from dataclasses import dataclass
import base64
import json
from typing import Any
from urllib import error, request


class OllamaError(RuntimeError):
    """Base error for Ollama client failures."""


class OllamaConnectionError(OllamaError):
    """Raised when Ollama cannot be reached."""


class OllamaTimeoutError(OllamaError):
    """Raised when Ollama request times out."""


class OllamaInvalidResponseError(OllamaError):
    """Raised when Ollama returns invalid JSON or unexpected structure."""


class OllamaModelNotFoundError(OllamaError):
    """Raised when the configured model is not installed on the Ollama server."""


@dataclass(frozen=True, slots=True)
class OllamaClient:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "gemma4:e4b"
    timeout_seconds: float = 10.0

    def is_available(self) -> bool:
        try:
            self._request_json("/api/tags", {"method": "GET"})
        except OllamaError:
            return False
        return True

    def generate(
        self,
        prompt: str,
        *,
        images: list[str] | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
        }
        if images:
            payload["images"] = images

        response = self._request_json(
            "/api/generate",
            {
                "method": "POST",
                "data": json.dumps(payload).encode("utf-8"),
                "headers": {"Content-Type": "application/json"},
            },
        )
        raw_text = response.get("response")
        if not isinstance(raw_text, str):
            raise OllamaInvalidResponseError("Ollama response missing text payload")
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise OllamaInvalidResponseError("Ollama returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise OllamaInvalidResponseError("Ollama JSON payload must be an object")
        return parsed

    def encode_image(self, image: object) -> str:
        if hasattr(image, "save"):
            from io import BytesIO

            buffer = BytesIO()
            image.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")
        raise TypeError("image must expose save() for Ollama vision requests")

    def _request_json(self, path: str, options: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        req = request.Request(url, **options)
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except TimeoutError as exc:
            raise OllamaTimeoutError("Ollama request timed out") from exc
        except error.HTTPError as exc:
            # HTTPError e subclasse de URLError: tratar antes, senao um 404 de
            # modelo nao instalado viraria "Ollama is unavailable".
            raise self._classify_http_error(exc) from exc
        except error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise OllamaTimeoutError("Ollama request timed out") from exc
            raise OllamaConnectionError("Ollama is unavailable") from exc

        try:
            parsed = json.loads(body or "{}")
        except json.JSONDecodeError as exc:
            raise OllamaInvalidResponseError("Ollama HTTP response is invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise OllamaInvalidResponseError("Ollama HTTP response must be an object")
        return parsed

    @staticmethod
    def _classify_http_error(exc: error.HTTPError) -> OllamaError:
        detail = ""
        try:
            parsed = json.loads(exc.read().decode("utf-8", errors="replace"))
            if isinstance(parsed, dict) and isinstance(parsed.get("error"), str):
                detail = parsed["error"]
        except (OSError, ValueError, AttributeError):
            detail = ""

        if exc.code == 404:
            message = "Ollama model not found (install it with 'ollama pull')"
            if detail:
                message = f"{message}: {detail}"
            return OllamaModelNotFoundError(message)

        message = f"Ollama returned HTTP {exc.code}"
        if detail:
            message = f"{message}: {detail}"
        return OllamaError(message)
