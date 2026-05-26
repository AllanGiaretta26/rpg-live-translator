from __future__ import annotations

from dataclasses import dataclass, field

from app.bootstrap import bootstrap
from config.settings import AppSettings


@dataclass
class FakeOverlay:
    messages: list[str] = field(default_factory=list)

    def show_text(self, text: str) -> None:
        self.messages.append(text)

    def hide(self) -> None:
        return


class FakeUi:
    def __init__(
        self,
        overlay: FakeOverlay,
        capture_loop: object,
        profile_settings: object,
    ) -> None:
        self.overlay = overlay
        self.capture_loop = capture_loop
        self.profile_settings = profile_settings
        self.ran = False

    def run(self) -> int:
        self.ran = True
        return 0


def test_bootstrap_wires_dependencies_and_starts(tmp_path):
    overlay = FakeOverlay()
    ui_instances: list[FakeUi] = []

    def _overlay_factory() -> FakeOverlay:
        return overlay

    def _ui_factory(
        value: FakeOverlay,
        capture_loop: object,
        profile_settings: object,
    ) -> FakeUi:
        instance = FakeUi(value, capture_loop, profile_settings)
        ui_instances.append(instance)
        return instance

    runtime = bootstrap(
        settings=AppSettings(
            database_path=tmp_path / "app.sqlite3",
            ollama_base_url="http://127.0.0.1:9",
            ollama_timeout_seconds=0.01,
        ),
        overlay_factory=_overlay_factory,
        ui_factory=_ui_factory,
    )

    exit_code = runtime.start()

    assert exit_code == 0
    assert ui_instances[0].ran is True
    assert runtime.capture_loop is ui_instances[0].capture_loop
    assert runtime.profile_settings_service is ui_instances[0].profile_settings
    assert any("Ollama indisponivel" in message for message in overlay.messages)
    with runtime.database.open() as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'translations'"
        ).fetchone()
    assert tables is not None
