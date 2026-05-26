from __future__ import annotations

from dataclasses import dataclass

from live_translator.domain.interfaces import OverlayRenderer


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
        self._bridge = OverlayBridge()
        self._bridge.show_requested.connect(self._show_text_on_ui_thread)
        self._bridge.hide_requested.connect(self._hide_on_ui_thread)
        self._move_to_bottom_center()

    @property
    def app(self):
        return self._app

    def show_text(self, text: str) -> None:
        self._bridge.show_requested.emit(text)

    def hide(self) -> None:
        self._bridge.hide_requested.emit()

    def _show_text_on_ui_thread(self, text: str) -> None:
        self._label.setText(text)
        self._move_to_bottom_center()
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

    def _handle_key_press(self, event) -> None:
        if event.key() == self._qt.Key_Escape:
            self._app.quit()
            return
        event.ignore()
