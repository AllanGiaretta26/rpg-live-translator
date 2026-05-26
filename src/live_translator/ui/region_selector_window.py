from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from live_translator.domain.models import TextRegion
from live_translator.ui.screen_geometry import (
    ScreenRect,
    local_to_physical_point,
    select_screen_for_point,
)


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
        from PySide6.QtWidgets import QLabel, QRubberBand, QVBoxLayout, QWidget

        self._start_global = QPoint()
        self._start_local = QPoint()
        self._selected_screen: ScreenRect | None = None
        self._window = QWidget()
        self._window.setWindowTitle("Selecionar regiao")
        self._window.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self._window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._window.setCursor(Qt.CursorShape.CrossCursor)
        self._window.setStyleSheet("background-color: rgba(0, 0, 0, 45);")
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self._window)
        self._rubber_band.setStyleSheet(
            "border: 3px solid #39ff88; background-color: rgba(57, 255, 136, 35);"
        )

        self._instruction = QLabel(
            "Arraste sobre a caixa de texto do jogo\nESC cancela",
            self._window,
        )
        self._instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._instruction.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self._instruction.setStyleSheet(
            "QLabel {"
            "background-color: rgba(0, 0, 0, 180);"
            "color: white;"
            "font-size: 24px;"
            "padding: 18px;"
            "border-radius: 8px;"
            "}"
        )
        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self._instruction, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)
        self._window.setLayout(layout)

        self._window.mousePressEvent = self._mouse_press_event
        self._window.mouseMoveEvent = self._mouse_move_event
        self._window.mouseReleaseEvent = self._mouse_release_event
        self._window.keyPressEvent = self._key_press_event

    def show(self) -> None:
        from PySide6.QtGui import QCursor, QGuiApplication

        cursor_position = QCursor.pos()
        screens = []
        for screen in QGuiApplication.screens():
            geometry = screen.geometry()
            screens.append(
                ScreenRect(
                    x=geometry.x(),
                    y=geometry.y(),
                    width=geometry.width(),
                    height=geometry.height(),
                    scale=float(screen.devicePixelRatio()),
                )
            )

        self._selected_screen = select_screen_for_point(
            cursor_position.x(),
            cursor_position.y(),
            tuple(screens),
        )
        self._window.setGeometry(
            self._selected_screen.x,
            self._selected_screen.y,
            self._selected_screen.width,
            self._selected_screen.height,
        )
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _mouse_press_event(self, event) -> None:
        from PySide6.QtCore import QRect

        self._start_local = event.position().toPoint()
        if self._selected_screen is not None:
            start_x, start_y = local_to_physical_point(
                self._start_local.x(),
                self._start_local.y(),
                self._selected_screen,
            )
            self._start_global = QPoint(start_x, start_y)
        else:
            self._start_global = event.globalPosition().toPoint()
        self._instruction.hide()
        self._rubber_band.setGeometry(QRect(self._start_local, self._start_local))
        self._rubber_band.show()

    def _mouse_move_event(self, event) -> None:
        from PySide6.QtCore import QRect

        current = event.position().toPoint()
        self._rubber_band.setGeometry(QRect(self._start_local, current).normalized())

    def _mouse_release_event(self, event) -> None:
        from PySide6.QtCore import QPoint

        end_local = event.position().toPoint()
        if self._selected_screen is not None:
            end_x, end_y = local_to_physical_point(
                end_local.x(),
                end_local.y(),
                self._selected_screen,
            )
            end_global = QPoint(end_x, end_y)
        else:
            end_global = event.globalPosition().toPoint()
        try:
            region = normalize_region(
                self._start_global.x(),
                self._start_global.y(),
                end_global.x(),
                end_global.y(),
            )
        except ValueError:
            self._rubber_band.hide()
            self._instruction.setText(
                "Selecao muito pequena\nArraste sobre a caixa de texto do jogo"
            )
            self._instruction.show()
            return

        self.on_selected(region)
        self._window.close()

    def _key_press_event(self, event) -> None:
        from PySide6.QtCore import Qt

        if event.key() == Qt.Key.Key_Escape:
            self._window.close()
