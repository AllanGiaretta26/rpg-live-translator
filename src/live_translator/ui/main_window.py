from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from live_translator.domain.models import GameProfile, OverlayPlacement, TextRegion


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


class OverlaySettings(Protocol):
    def get_placement(self) -> OverlayPlacement: ...

    def save_placement(self, placement: OverlayPlacement) -> None: ...


class EditableOverlay(Protocol):
    def apply_placement(self, placement: OverlayPlacement) -> None: ...

    def current_placement(self) -> OverlayPlacement: ...

    def show_calibration_text(self) -> None: ...

    def set_edit_mode(
        self,
        enabled: bool,
        on_changed: Callable[[OverlayPlacement], None] | None = None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class QtUiSettings:
    capture_interval_ms: int = 500


class QtUiApp:
    def __init__(
        self,
        overlay: EditableOverlay,
        capture_loop: TickableCaptureLoop,
        profile_settings: ProfileSettings,
        capture_preview: CapturePreview,
        pipeline_diagnostics: PipelineDiagnostics,
        overlay_settings: OverlaySettings,
        settings: QtUiSettings,
    ) -> None:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        self._overlay = overlay
        self._capture_loop = capture_loop
        self._timer = QTimer()
        self._timer.setInterval(settings.capture_interval_ms)
        self._timer.timeout.connect(self._tick_capture_loop)
        self._app = QApplication.instance() or getattr(overlay, "app")
        self._window = SettingsWindow(
            overlay,
            capture_loop,
            profile_settings,
            capture_preview,
            pipeline_diagnostics,
            overlay_settings,
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
        overlay: EditableOverlay,
        capture_loop: TickableCaptureLoop,
        profile_settings: ProfileSettings,
        capture_preview: CapturePreview,
        pipeline_diagnostics: PipelineDiagnostics,
        overlay_settings: OverlaySettings,
    ) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QDoubleSpinBox,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QPushButton,
            QSpinBox,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )

        self._overlay = overlay
        self._capture_loop = capture_loop
        self._profile_settings = profile_settings
        self._capture_preview = capture_preview
        self._pipeline_diagnostics = pipeline_diagnostics
        self._overlay_settings = overlay_settings
        self._region_selector = None

        self._widget = QWidget()
        self._widget.setWindowTitle("RPG Live Translator")
        self._widget.setMinimumWidth(520)

        self._capture_status = QLabel("Rodando")
        self._pipeline_status = QLabel("Pipeline: aguardando")
        self._status = QLabel("")

        self._name = QLineEdit()
        self._x = self._spinbox(-10000, 10000)
        self._y = self._spinbox(-10000, 10000)
        self._width = self._spinbox(1, 10000)
        self._height = self._spinbox(1, 10000)
        self._preview = QLabel("Nenhuma area capturada")
        self._preview.setMinimumHeight(170)
        self._preview.setStyleSheet(
            "border: 1px solid #555; background: #111; color: #ddd;"
        )
        self._preview.setScaledContents(False)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._overlay_x = self._spinbox(0, 10000)
        self._overlay_y = self._spinbox(0, 10000)
        self._overlay_width = self._spinbox(160, 10000)
        self._overlay_height = self._spinbox(60, 10000)
        self._overlay_font_size = self._spinbox(8, 96)
        self._overlay_opacity = QDoubleSpinBox()
        self._overlay_opacity.setRange(0.1, 1.0)
        self._overlay_opacity.setSingleStep(0.05)
        self._overlay_opacity.setDecimals(2)

        self._select_region = QPushButton("Selecionar area do texto")
        self._preview_capture = QPushButton("Ver preview da area")
        self._save = QPushButton("Salvar area")
        self._show_overlay = QPushButton("Ajustar overlay")
        self._save_overlay = QPushButton("Salvar overlay")
        self._pause = QPushButton("Pausar")
        self._resume = QPushButton("Retomar")
        self._quit = QPushButton("Fechar")

        tabs = QTabWidget()
        tabs.addTab(self._build_capture_tab(QFormLayout, QHBoxLayout, QVBoxLayout), "1. Area do texto")
        tabs.addTab(self._build_overlay_tab(QFormLayout, QHBoxLayout, QVBoxLayout), "2. Overlay")
        tabs.addTab(self._build_run_tab(QGroupBox, QHBoxLayout, QVBoxLayout), "3. Executar")

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addWidget(self._status)
        self._widget.setLayout(layout)

        self._select_region.clicked.connect(self._select_region_on_screen)
        self._preview_capture.clicked.connect(self._capture_preview_image)
        self._save.clicked.connect(self._save_profile)
        self._show_overlay.clicked.connect(self._start_overlay_adjustment)
        self._save_overlay.clicked.connect(self._save_overlay_placement)
        self._pause.clicked.connect(self._pause_loop)
        self._resume.clicked.connect(self._resume_loop)
        self._quit.clicked.connect(self._widget.close)
        self._widget.closeEvent = self._close_event

        self._load_active_profile()
        self._load_overlay_placement()

    def show(self) -> None:
        self._widget.show()

    def refresh_capture_status(self) -> None:
        error_message = self._capture_loop.last_error_message
        if error_message:
            self._capture_status.setText(f"Captura: erro - {error_message}")
        elif self._capture_loop.is_paused:
            self._capture_status.setText("Captura: pausada")
        elif self._capture_loop.is_busy:
            self._capture_status.setText("Captura: processando frame")
        else:
            self._capture_status.setText("Captura: rodando")

    def refresh_pipeline_status(self) -> None:
        diagnostic = self._pipeline_diagnostics.last_diagnostic
        if diagnostic:
            self._pipeline_status.setText(f"Pipeline: {diagnostic}")
        else:
            self._pipeline_status.setText("Pipeline: aguardando")

    def _build_capture_tab(self, form_cls, hbox_cls, vbox_cls):
        tab = vbox_cls()
        form = form_cls()
        form.addRow("Perfil", self._name)
        form.addRow("X", self._x)
        form.addRow("Y", self._y)
        form.addRow("Largura", self._width)
        form.addRow("Altura", self._height)
        buttons = hbox_cls()
        buttons.addWidget(self._select_region)
        buttons.addWidget(self._preview_capture)
        buttons.addWidget(self._save)
        tab.addLayout(form)
        tab.addWidget(self._preview)
        tab.addLayout(buttons)
        return self._wrap(tab)

    def _build_overlay_tab(self, form_cls, hbox_cls, vbox_cls):
        tab = vbox_cls()
        form = form_cls()
        form.addRow("X", self._overlay_x)
        form.addRow("Y", self._overlay_y)
        form.addRow("Largura", self._overlay_width)
        form.addRow("Altura", self._overlay_height)
        form.addRow("Fonte", self._overlay_font_size)
        form.addRow("Opacidade", self._overlay_opacity)
        buttons = hbox_cls()
        buttons.addWidget(self._show_overlay)
        buttons.addWidget(self._save_overlay)
        tab.addLayout(form)
        tab.addLayout(buttons)
        return self._wrap(tab)

    def _build_run_tab(self, group_cls, hbox_cls, vbox_cls):
        tab = vbox_cls()
        status_group = group_cls("Status")
        status_layout = vbox_cls()
        status_layout.addWidget(self._capture_status)
        status_layout.addWidget(self._pipeline_status)
        status_group.setLayout(status_layout)
        buttons = hbox_cls()
        buttons.addWidget(self._pause)
        buttons.addWidget(self._resume)
        buttons.addWidget(self._quit)
        tab.addWidget(status_group)
        tab.addLayout(buttons)
        return self._wrap(tab)

    def _wrap(self, layout):
        from PySide6.QtWidgets import QWidget

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _spinbox(self, minimum: int, maximum: int):
        from PySide6.QtWidgets import QSpinBox

        spinbox = QSpinBox()
        spinbox.setRange(minimum, maximum)
        return spinbox

    def _capture_preview_image(self) -> bool:
        try:
            path = self._capture_preview.capture_preview(
                x=self._x.value(),
                y=self._y.value(),
                width=self._width.value(),
                height=self._height.value(),
            )
        except Exception as error:
            self._status.setText(f"Preview falhou: {error}")
            return False

        self._show_preview(path)
        self._status.setText(f"Preview atualizado: {path}")
        return True

    def _select_region_on_screen(self) -> None:
        from live_translator.ui.region_selector_window import RegionSelectorWindow

        self._status.setText("Arraste a caixa de texto do jogo. ESC cancela.")
        self._region_selector = RegionSelectorWindow(self._apply_selected_region)
        self._region_selector.show()

    def _apply_selected_region(self, region: TextRegion) -> None:
        self._x.setValue(region.x)
        self._y.setValue(region.y)
        self._width.setValue(region.width)
        self._height.setValue(region.height)
        self._status.setText(
            "Area selecionada: "
            f"x={region.x} y={region.y} {region.width}x{region.height}"
        )
        self._capture_preview_image()

    def _start_overlay_adjustment(self) -> None:
        placement = self._placement_from_fields()
        self._overlay.apply_placement(placement)
        self._overlay.show_calibration_text()
        self._overlay.set_edit_mode(True, self._sync_overlay_fields)
        self._status.setText(
            "Arraste o overlay para mover. Arraste o canto inferior direito para redimensionar."
        )

    def _save_overlay_placement(self) -> None:
        placement = self._overlay.current_placement()
        self._overlay.set_edit_mode(False)
        self._overlay_settings.save_placement(placement)
        self._sync_overlay_fields(placement)
        self._status.setText("Overlay salvo.")

    def _sync_overlay_fields(self, placement: OverlayPlacement) -> None:
        widgets = (
            self._overlay_x,
            self._overlay_y,
            self._overlay_width,
            self._overlay_height,
            self._overlay_font_size,
            self._overlay_opacity,
        )
        for widget in widgets:
            widget.blockSignals(True)
        self._overlay_x.setValue(placement.x)
        self._overlay_y.setValue(placement.y)
        self._overlay_width.setValue(placement.width)
        self._overlay_height.setValue(placement.height)
        self._overlay_font_size.setValue(placement.font_size)
        self._overlay_opacity.setValue(placement.opacity)
        for widget in widgets:
            widget.blockSignals(False)

    def _placement_from_fields(self) -> OverlayPlacement:
        return OverlayPlacement(
            x=self._overlay_x.value(),
            y=self._overlay_y.value(),
            width=self._overlay_width.value(),
            height=self._overlay_height.value(),
            opacity=self._overlay_opacity.value(),
            font_size=self._overlay_font_size.value(),
        )

    def _show_preview(self, path: Path) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._preview.setText(f"Preview salvo, mas nao foi possivel abrir: {path}")
            return

        scaled = pixmap.scaled(
            460,
            170,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setPixmap(scaled)

    def _load_active_profile(self) -> None:
        profile = self._profile_settings.get_active_profile()
        if profile is None:
            self._name.setText("Default Lower Screen")
            self._x.setValue(256)
            self._y.setValue(950)
            self._width.setValue(2048)
            self._height.setValue(360)
            self._status.setText("Selecione a area do texto ou ajuste os numeros.")
            return

        self._name.setText(profile.name)
        self._x.setValue(profile.text_region.x)
        self._y.setValue(profile.text_region.y)
        self._width.setValue(profile.text_region.width)
        self._height.setValue(profile.text_region.height)

    def _load_overlay_placement(self) -> None:
        placement = self._overlay_settings.get_placement()
        self._overlay.apply_placement(placement)
        self._sync_overlay_fields(placement)

    def _save_profile(self) -> None:
        try:
            profile = self._profile_settings.save_profile(
                name=self._name.text(),
                window_title="Manual Region",
                x=self._x.value(),
                y=self._y.value(),
                width=self._width.value(),
                height=self._height.value(),
            )
        except ValueError as error:
            self._status.setText(f"Area invalida: {error}")
            return

        self._status.setText(
            "Area salva: "
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
        self._overlay.set_edit_mode(False)
        QApplication.quit()
        event.accept()
