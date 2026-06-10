"""Garante que o bootstrap completo roda sem desktop nem Ollama.

Bloqueia os imports de PySide6/mss para simular um ambiente headless (CI) e
verifica que os fallbacks de console assumem e o app sobe e encerra limpo.
"""

from __future__ import annotations

import sys

import pytest

from live_translator.app.bootstrap import ConsoleOverlay, ConsoleUiApp, bootstrap
from live_translator.config.settings import AppSettings

_BLOCKED_TOP_LEVEL = ("PySide6", "mss")


class _DesktopImportBlocker:
    def find_spec(self, fullname: str, path=None, target=None):
        if fullname.split(".", 1)[0] in _BLOCKED_TOP_LEVEL:
            raise ImportError(f"{fullname} bloqueado pelo teste headless")
        return None


@pytest.fixture
def headless_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name.split(".", 1)[0] in _BLOCKED_TOP_LEVEL or name.startswith(
            "live_translator.ui"
        ):
            monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(sys, "meta_path", [_DesktopImportBlocker(), *sys.meta_path])


def test_bootstrap_runs_headless_with_console_fallbacks(
    tmp_path, headless_environment
) -> None:
    runtime = bootstrap(
        settings=AppSettings(
            database_path=tmp_path / "app.sqlite3",
            capture_preview_path=tmp_path / "preview.png",
            ollama_base_url="http://127.0.0.1:9",
            ollama_timeout_seconds=0.01,
            rpg_maker_bridge_enabled=False,
        )
    )

    assert isinstance(runtime.overlay, ConsoleOverlay)
    assert isinstance(runtime.ui, ConsoleUiApp)
    assert runtime.start() == 0
