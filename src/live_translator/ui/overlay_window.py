from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from live_translator.domain.interfaces import OverlayRenderer
from live_translator.domain.models import OverlayPlacement


@dataclass(frozen=True, slots=True)
class OverlayStyle:
    opacity: float = 0.85
    font_size: int = 24
    width: int = 900
    height: int = 120
    bottom_margin: int = 560


class OverlayWindow(OverlayRenderer):
    def __init__(self, style: OverlayStyle | None = None) -> None:
        from PySide6.QtCore import QObject, Qt, Signal, Slot
        from PySide6.QtWidgets import QApplication, QLabel, QWidget

        class OverlayBridge(QObject):
            show_requested = Signal(str)
            hide_requested = Signal()

        self._qt = Qt
        self._app = QApplication.instance()
        if self._app is None:
            self._app = QApplication([])

        self._style = style or OverlayStyle()
        self._edit_mode = False
        self._on_changed: Callable[[OverlayPlacement], None] | None = None
        self._drag_start_global = None
        self._drag_start_geometry = None
        self._resizing = False
        self._window = QWidget()
        self._window.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self._window.setAttribute(Qt.WA_TranslucentBackground, True)
        self._window.setWindowOpacity(self._style.opacity)

        self._label = QLabel(self._window)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(
            "QLabel {"
            "background-color: rgba(0, 0, 0, 190);"
            "color: white;"
            "border-radius: 8px;"
            "padding: 16px;"
            f"font-size: {self._style.font_size}px;"
            "}"
        )
        self._window.resize(self._style.width, self._style.height)
        self._label.setGeometry(0, 0, self._style.width, self._style.height)
        self._window.keyPressEvent = self._handle_key_press
        self._window.mousePressEvent = self._handle_mouse_press
        self._window.mouseMoveEvent = self._handle_mouse_move
        self._window.mouseReleaseEvent = self._handle_mouse_release
        self._bridge = OverlayBridge()
        self._bridge.show_requested.connect(self._show_text_on_ui_thread)
        self._bridge.hide_requested.connect(self._hide_on_ui_thread)
        self.apply_placement(self._default_placement())

    @property
    def app(self):
        return self._app

    def show_text(self, text: str) -> None:
        self._bridge.show_requested.emit(text)

    def hide(self) -> None:
        self._bridge.hide_requested.emit()

    def apply_placement(self, placement: OverlayPlacement) -> None:
        self._style = OverlayStyle(
            opacity=placement.opacity,
            font_size=placement.font_size,
            width=placement.width,
            height=placement.height,
            bottom_margin=self._style.bottom_margin,
        )
        self._window.setWindowOpacity(placement.opacity)
        self._window.setGeometry(
            placement.x,
            placement.y,
            placement.width,
            placement.height,
        )
        self._label.setGeometry(0, 0, placement.width, placement.height)
        self._label.setStyleSheet(self._label_stylesheet(placement.font_size))

    def current_placement(self) -> OverlayPlacement:
        geometry = self._window.geometry()
        return OverlayPlacement(
            x=geometry.x(),
            y=geometry.y(),
            width=geometry.width(),
            height=geometry.height(),
            opacity=self._style.opacity,
            font_size=self._style.font_size,
        )

    def show_calibration_text(self) -> None:
        self._show_text_on_ui_thread("Texto de teste do overlay")

    def set_edit_mode(
        self,
        enabled: bool,
        on_changed: Callable[[OverlayPlacement], None] | None = None,
    ) -> None:
        self._edit_mode = enabled
        self._on_changed = on_changed
        self._window.setCursor(
            self._qt.CursorShape.SizeAllCursor
            if enabled
            else self._qt.CursorShape.ArrowCursor
        )

    def _show_text_on_ui_thread(self, text: str) -> None:
        self._label.setText(text)
        self._window.show()

    def _hide_on_ui_thread(self) -> None:
        self._window.hide()

    def _move_to_bottom_center(self) -> None:
        screen = self._app.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        x = geometry.x() + (geometry.width() - self._style.width) // 2
        y = geometry.y() + geometry.height() - self._style.height - self._style.bottom_margin
        self._window.move(x, y)

    def _default_placement(self) -> OverlayPlacement:
        screen = self._app.primaryScreen()
        if screen is None:
            return OverlayPlacement(
                x=0,
                y=0,
                width=self._style.width,
                height=self._style.height,
                opacity=self._style.opacity,
                font_size=self._style.font_size,
            )
        geometry = screen.availableGeometry()
        return OverlayPlacement(
            x=geometry.x() + (geometry.width() - self._style.width) // 2,
            y=geometry.y()
            + geometry.height()
            - self._style.height
            - self._style.bottom_margin,
            width=self._style.width,
            height=self._style.height,
            opacity=self._style.opacity,
            font_size=self._style.font_size,
        )

    def _label_stylesheet(self, font_size: int) -> str:
        return (
            "QLabel {"
            "background-color: rgba(0, 0, 0, 190);"
            "color: white;"
            "border-radius: 8px;"
            "padding: 16px;"
            f"font-size: {font_size}px;"
            "}"
        )

    def _handle_key_press(self, event) -> None:
        if event.key() == self._qt.Key_Escape:
            if self._edit_mode:
                self.set_edit_mode(False)
            else:
                self._app.quit()
            return
        event.ignore()

    def _handle_mouse_press(self, event) -> None:
        if not self._edit_mode:
            event.ignore()
            return
        self._drag_start_global = event.globalPosition().toPoint()
        self._drag_start_geometry = self._window.geometry()
        position = event.position().toPoint()
        self._resizing = (
            self._drag_start_geometry.width() - position.x() <= 24
            and self._drag_start_geometry.height() - position.y() <= 24
        )
        event.accept()

    def _handle_mouse_move(self, event) -> None:
        if not self._edit_mode:
            event.ignore()
            return
        if self._drag_start_global is None or self._drag_start_geometry is None:
            return

        current_global = event.globalPosition().toPoint()
        delta = current_global - self._drag_start_global
        if self._resizing:
            width = max(160, self._drag_start_geometry.width() + delta.x())
            height = max(60, self._drag_start_geometry.height() + delta.y())
            self._window.resize(width, height)
            self._label.setGeometry(0, 0, width, height)
        else:
            self._window.move(
                self._drag_start_geometry.x() + delta.x(),
                self._drag_start_geometry.y() + delta.y(),
            )
        self._notify_changed()
        event.accept()

    def _handle_mouse_release(self, event) -> None:
        if not self._edit_mode:
            event.ignore()
            return
        self._drag_start_global = None
        self._drag_start_geometry = None
        self._resizing = False
        self._notify_changed()
        event.accept()

    def _notify_changed(self) -> None:
        if self._on_changed is not None:
            self._on_changed(self.current_placement())
