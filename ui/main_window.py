from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.models import GameProfile


class TickableCaptureLoop(Protocol):
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


@dataclass(frozen=True, slots=True)
class QtUiSettings:
    capture_interval_ms: int = 500


class QtUiApp:
    def __init__(
        self,
        overlay: object,
        capture_loop: TickableCaptureLoop,
        profile_settings: ProfileSettings,
        settings: QtUiSettings,
    ) -> None:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        self._overlay = overlay
        self._capture_loop = capture_loop
        self._profile_settings = profile_settings
        self._timer = QTimer()
        self._timer.setInterval(settings.capture_interval_ms)
        self._timer.timeout.connect(self._capture_loop.tick)
        self._app = QApplication.instance() or getattr(overlay, "app")
        self._window = SettingsWindow(capture_loop, profile_settings)

    def run(self) -> int:
        self._capture_loop.resume()
        self._timer.start()
        self._window.show()
        return int(self._app.exec())


class SettingsWindow:
    def __init__(
        self,
        capture_loop: TickableCaptureLoop,
        profile_settings: ProfileSettings,
    ) -> None:
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
        self._widget = QWidget()
        self._widget.setWindowTitle("RPG Live Translator")
        self._widget.setMinimumWidth(420)

        self._status = QLabel("Rodando")
        self._name = QLineEdit()
        self._window_title = QLineEdit()
        self._x = self._spinbox(-10000, 10000)
        self._y = self._spinbox(-10000, 10000)
        self._width = self._spinbox(1, 10000)
        self._height = self._spinbox(1, 10000)

        form = QFormLayout()
        form.addRow("Perfil", self._name)
        form.addRow("Titulo da janela", self._window_title)
        form.addRow("X", self._x)
        form.addRow("Y", self._y)
        form.addRow("Largura", self._width)
        form.addRow("Altura", self._height)

        self._save = QPushButton("Salvar perfil")
        self._pause = QPushButton("Pausar")
        self._resume = QPushButton("Retomar")
        self._quit = QPushButton("Fechar")

        buttons = QHBoxLayout()
        buttons.addWidget(self._save)
        buttons.addWidget(self._pause)
        buttons.addWidget(self._resume)
        buttons.addWidget(self._quit)

        layout = QVBoxLayout()
        layout.addWidget(self._status)
        layout.addLayout(form)
        layout.addLayout(buttons)
        self._widget.setLayout(layout)

        self._save.clicked.connect(self._save_profile)
        self._pause.clicked.connect(self._pause_loop)
        self._resume.clicked.connect(self._resume_loop)
        self._quit.clicked.connect(self._widget.close)
        self._widget.closeEvent = self._close_event

        self._load_active_profile()

    def show(self) -> None:
        self._widget.show()

    def _spinbox(self, minimum: int, maximum: int):
        from PySide6.QtWidgets import QSpinBox

        spinbox = QSpinBox()
        spinbox.setRange(minimum, maximum)
        return spinbox

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
        self._status.setText("Pausado")

    def _resume_loop(self) -> None:
        self._capture_loop.resume()
        self._status.setText("Rodando")

    def _close_event(self, event) -> None:
        from PySide6.QtWidgets import QApplication

        self._capture_loop.pause()
        QApplication.quit()
        event.accept()
