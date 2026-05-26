from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from live_translator.domain.models import GameProfile


class TickableCaptureLoop(Protocol):
    @property
    def is_paused(self) -> bool: ...

    @property
    def is_busy(self) -> bool: ...

    @property
    def last_error_message(self) -> str | None: ...

    def resume(self) -> None: ...

    def pause(self) -> None: ...

    def tick(self) -> bool: ...


class ProfileSettings(Protocol):
    def get_active_profile(self) -> GameProfile | None: ...

    def save_profile(
        self,
        *,
        name: str,
        window_title: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> GameProfile: ...


class CapturePreview(Protocol):
    def capture_preview(
        self,
        *,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Path: ...


class PipelineDiagnostics(Protocol):
    @property
    def last_diagnostic(self) -> str | None: ...


@dataclass(frozen=True, slots=True)
class QtUiSettings:
    capture_interval_ms: int = 500


class QtUiApp:
    def __init__(
        self,
        overlay: object,
        capture_loop: TickableCaptureLoop,
        profile_settings: ProfileSettings,
        capture_preview: CapturePreview,
        pipeline_diagnostics: PipelineDiagnostics,
        settings: QtUiSettings,
    ) -> None:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        self._overlay = overlay
        self._capture_loop = capture_loop
        self._profile_settings = profile_settings
        self._capture_preview = capture_preview
        self._pipeline_diagnostics = pipeline_diagnostics
        self._timer = QTimer()
        self._timer.setInterval(settings.capture_interval_ms)
        self._timer.timeout.connect(self._tick_capture_loop)
        self._app = QApplication.instance() or getattr(overlay, "app")
        self._window = SettingsWindow(
            capture_loop,
            profile_settings,
            capture_preview,
            pipeline_diagnostics,
        )

    def run(self) -> int:
        self._capture_loop.resume()
        self._timer.start()
        self._window.show()
        return int(self._app.exec())

    def _tick_capture_loop(self) -> None:
        self._capture_loop.tick()
        self._window.refresh_capture_status()
        self._window.refresh_pipeline_status()


class SettingsWindow:
    def __init__(
        self,
        capture_loop: TickableCaptureLoop,
        profile_settings: ProfileSettings,
        capture_preview: CapturePreview,
        pipeline_diagnostics: PipelineDiagnostics,
    ) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QPushButton,
            QSpinBox,
            QVBoxLayout,
            QWidget,
        )

        self._capture_loop = capture_loop
        self._profile_settings = profile_settings
        self._capture_preview = capture_preview
        self._pipeline_diagnostics = pipeline_diagnostics
        self._widget = QWidget()
        self._widget.setWindowTitle("RPG Live Translator")
        self._widget.setMinimumWidth(420)

        self._capture_status = QLabel("Rodando")
        self._pipeline_status = QLabel("Pipeline: aguardando")
        self._status = QLabel("")
        self._name = QLineEdit()
        self._window_title = QLineEdit()
        self._x = self._spinbox(-10000, 10000)
        self._y = self._spinbox(-10000, 10000)
        self._width = self._spinbox(1, 10000)
        self._height = self._spinbox(1, 10000)
        self._preview = QLabel("Sem preview")
        self._preview.setMinimumHeight(150)
        self._preview.setStyleSheet(
            "border: 1px solid #555; background: #111; color: #ddd;"
        )
        self._preview.setScaledContents(False)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form = QFormLayout()
        form.addRow("Perfil", self._name)
        form.addRow("Titulo da janela", self._window_title)
        form.addRow("X", self._x)
        form.addRow("Y", self._y)
        form.addRow("Largura", self._width)
        form.addRow("Altura", self._height)

        self._save = QPushButton("Salvar perfil")
        self._test_capture = QPushButton("Testar captura")
        self._pause = QPushButton("Pausar")
        self._resume = QPushButton("Retomar")
        self._quit = QPushButton("Fechar")

        buttons = QHBoxLayout()
        buttons.addWidget(self._save)
        buttons.addWidget(self._test_capture)
        buttons.addWidget(self._pause)
        buttons.addWidget(self._resume)
        buttons.addWidget(self._quit)

        layout = QVBoxLayout()
        layout.addWidget(self._capture_status)
        layout.addWidget(self._pipeline_status)
        layout.addWidget(self._status)
        layout.addLayout(form)
        layout.addWidget(self._preview)
        layout.addLayout(buttons)
        self._widget.setLayout(layout)

        self._save.clicked.connect(self._save_profile)
        self._test_capture.clicked.connect(self._capture_preview_image)
        self._pause.clicked.connect(self._pause_loop)
        self._resume.clicked.connect(self._resume_loop)
        self._quit.clicked.connect(self._widget.close)
        self._widget.closeEvent = self._close_event

        self._load_active_profile()

    def show(self) -> None:
        self._widget.show()

    def refresh_capture_status(self) -> None:
        error_message = self._capture_loop.last_error_message
        if error_message:
            self._capture_status.setText(f"Erro: {error_message}")
        elif self._capture_loop.is_paused:
            self._capture_status.setText("Pausado")
        elif self._capture_loop.is_busy:
            self._capture_status.setText("Capturando")
        else:
            self._capture_status.setText("Rodando")

    def refresh_pipeline_status(self) -> None:
        diagnostic = self._pipeline_diagnostics.last_diagnostic
        if diagnostic:
            self._pipeline_status.setText(f"Pipeline: {diagnostic}")
        else:
            self._pipeline_status.setText("Pipeline: aguardando")

    def _spinbox(self, minimum: int, maximum: int):
        from PySide6.QtWidgets import QSpinBox

        spinbox = QSpinBox()
        spinbox.setRange(minimum, maximum)
        return spinbox

    def _capture_preview_image(self) -> None:
        try:
            path = self._capture_preview.capture_preview(
                x=self._x.value(),
                y=self._y.value(),
                width=self._width.value(),
                height=self._height.value(),
            )
        except Exception as error:
            self._status.setText(f"Falha no preview: {error}")
            return

        self._show_preview(path)
        self._status.setText(f"Preview salvo: {path}")

    def _show_preview(self, path: Path) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._preview.setText(f"Preview salvo, mas nao foi possivel abrir: {path}")
            return

        scaled = pixmap.scaled(
            390,
            150,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setPixmap(scaled)

    def _load_active_profile(self) -> None:
        profile = self._profile_settings.get_active_profile()
        if profile is None:
            self._name.setText("Default Lower Screen")
            self._window_title.setText("Manual Region")
            self._x.setValue(256)
            self._y.setValue(950)
            self._width.setValue(2048)
            self._height.setValue(360)
            self._status.setText("Sem perfil salvo. Ajuste a regiao e salve.")
            return

        self._name.setText(profile.name)
        self._window_title.setText(profile.window_title)
        self._x.setValue(profile.text_region.x)
        self._y.setValue(profile.text_region.y)
        self._width.setValue(profile.text_region.width)
        self._height.setValue(profile.text_region.height)

    def _save_profile(self) -> None:
        try:
            profile = self._profile_settings.save_profile(
                name=self._name.text(),
                window_title=self._window_title.text(),
                x=self._x.value(),
                y=self._y.value(),
                width=self._width.value(),
                height=self._height.value(),
            )
        except ValueError as error:
            self._status.setText(f"Perfil invalido: {error}")
            return

        self._status.setText(
            "Perfil salvo: "
            f"x={profile.text_region.x} y={profile.text_region.y} "
            f"{profile.text_region.width}x{profile.text_region.height}"
        )

    def _pause_loop(self) -> None:
        self._capture_loop.pause()
        self.refresh_capture_status()

    def _resume_loop(self) -> None:
        self._capture_loop.resume()
        self.refresh_capture_status()

    def _close_event(self, event) -> None:
        from PySide6.QtWidgets import QApplication

        self._capture_loop.pause()
        QApplication.quit()
        event.accept()
