from __future__ import annotations

from dataclasses import dataclass, field

from live_translator.app.bootstrap import bootstrap
from live_translator.config.settings import AppSettings


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
        capture_preview: object,
        pipeline_diagnostics: object,
        overlay_settings: object,
        mode_settings: object,
    ) -> None:
        self.overlay = overlay
        self.capture_loop = capture_loop
        self.profile_settings = profile_settings
        self.capture_preview = capture_preview
        self.pipeline_diagnostics = pipeline_diagnostics
        self.overlay_settings = overlay_settings
        self.mode_settings = mode_settings
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
        capture_preview: object,
        pipeline_diagnostics: object,
        overlay_settings: object,
        mode_settings: object,
    ) -> FakeUi:
        instance = FakeUi(
            value,
            capture_loop,
            profile_settings,
            capture_preview,
            pipeline_diagnostics,
            overlay_settings,
            mode_settings,
        )
        ui_instances.append(instance)
        return instance

    runtime = bootstrap(
        settings=AppSettings(
            database_path=tmp_path / "app.sqlite3",
            capture_preview_path=tmp_path / "preview.png",
            ollama_base_url="http://127.0.0.1:9",
            ollama_timeout_seconds=0.01,
            rpg_maker_bridge_enabled=False,
        ),
        overlay_factory=_overlay_factory,
        ui_factory=_ui_factory,
    )

    exit_code = runtime.start()

    assert exit_code == 0
    assert ui_instances[0].ran is True
    assert runtime.capture_loop is ui_instances[0].capture_loop
    assert runtime.profile_settings_service is ui_instances[0].profile_settings
    assert runtime.capture_preview_service is ui_instances[0].capture_preview
    assert runtime.pipeline is ui_instances[0].pipeline_diagnostics
    assert runtime.overlay_settings_service is ui_instances[0].overlay_settings
    assert runtime.mode_settings_service is ui_instances[0].mode_settings
    assert runtime.capture_preview_service.preview_path == tmp_path / "preview.png"
    assert any("Ollama indisponivel" in message for message in overlay.messages)
    with runtime.database.open() as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'translations'"
        ).fetchone()
    assert tables is not None
