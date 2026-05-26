from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from live_translator.domain.models import TextRegion


def normalize_region(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
) -> TextRegion:
    left = min(start_x, end_x)
    top = min(start_y, end_y)
    width = abs(end_x - start_x)
    height = abs(end_y - start_y)
    return TextRegion(x=left, y=top, width=width, height=height)


@dataclass
class RegionSelectorWindow:
    on_selected: Callable[[TextRegion], None]

    def __post_init__(self) -> None:
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtWidgets import QRubberBand, QWidget

        self._start_global = QPoint()
        self._start_local = QPoint()
        self._window = QWidget()
        self._window.setWindowTitle("Selecionar regiao")
        self._window.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self._window.setWindowState(Qt.WindowState.WindowFullScreen)
        self._window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._window.setCursor(Qt.CursorShape.CrossCursor)
        self._window.setStyleSheet("background-color: rgba(0, 0, 0, 90);")
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self._window)

        self._window.mousePressEvent = self._mouse_press_event
        self._window.mouseMoveEvent = self._mouse_move_event
        self._window.mouseReleaseEvent = self._mouse_release_event
        self._window.keyPressEvent = self._key_press_event

    def show(self) -> None:
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _mouse_press_event(self, event) -> None:
        from PySide6.QtCore import QRect

        self._start_global = event.globalPosition().toPoint()
        self._start_local = event.position().toPoint()
        self._rubber_band.setGeometry(QRect(self._start_local, self._start_local))
        self._rubber_band.show()

    def _mouse_move_event(self, event) -> None:
        from PySide6.QtCore import QRect

        current = event.position().toPoint()
        self._rubber_band.setGeometry(QRect(self._start_local, current).normalized())

    def _mouse_release_event(self, event) -> None:
        end_global = event.globalPosition().toPoint()
        try:
            region = normalize_region(
                self._start_global.x(),
                self._start_global.y(),
                end_global.x(),
                end_global.y(),
            )
        except ValueError:
            self._window.close()
            return

        self.on_selected(region)
        self._window.close()

    def _key_press_event(self, event) -> None:
        from PySide6.QtCore import Qt

        if event.key() == Qt.Key.Key_Escape:
            self._window.close()
