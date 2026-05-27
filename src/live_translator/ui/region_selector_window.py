from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from live_translator.domain.models import TextRegion
from live_translator.ui.screen_geometry import (
    ScreenRect,
    global_to_physical_point,
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
        from PySide6.QtGui import QColor, QFont, QPainter, QPen
        from PySide6.QtWidgets import QWidget

        owner = self

        class SelectionWidget(QWidget):
            def paintEvent(self, event) -> None:
                super().paintEvent(event)
                painter = QPainter(self)
                painter.fillRect(self.rect(), QColor(0, 0, 0))

                painter.setOpacity(1.0)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                font = QFont()
                font.setPointSize(18)
                painter.setFont(font)

                instruction_rect = self.rect().adjusted(0, 28, 0, 0)
                instruction_rect.setHeight(88)
                instruction_rect.setWidth(min(620, self.width() - 80))
                instruction_rect.moveCenter(self.rect().center())
                instruction_rect.moveTop(34)
                painter.setBrush(QColor(0, 0, 0, 230))
                painter.setPen(QPen(QColor(0, 0, 0, 0), 0))
                painter.drawRoundedRect(instruction_rect, 8, 8)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(
                    instruction_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    owner._instruction_text,
                )

                if not owner._selecting:
                    return

                selection_rect = owner._selection_rect()
                if selection_rect.isNull():
                    return

                painter.setBrush(QColor(57, 255, 136, 45))
                painter.setPen(QPen(QColor(57, 255, 136), 3))
                painter.drawRect(selection_rect)

        self._start_global = QPoint()
        self._start_local = QPoint()
        self._current_local = QPoint()
        self._selected_screen: ScreenRect | None = None
        self._selecting = False
        self._instruction_text = "Arraste sobre a caixa de texto do jogo\nESC cancela"
        self._window = SelectionWidget()
        self._window.setWindowTitle("Selecionar regiao")
        self._window.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self._window.setMouseTracking(True)
        self._window.setWindowOpacity(0.68)
        self._window.setCursor(Qt.CursorShape.CrossCursor)

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

    def _selection_rect(self):
        from PySide6.QtCore import QRect

        return QRect(self._start_local, self._current_local).normalized()

    def _mouse_press_event(self, event) -> None:
        self._start_local = event.position().toPoint()
        self._current_local = self._start_local
        self._selecting = True
        self._instruction_text = "Arraste para cobrir a caixa de texto\nSolte para confirmar"
        start_global = event.globalPosition().toPoint()
        if self._selected_screen is not None:
            start_x, start_y = global_to_physical_point(
                start_global.x(),
                start_global.y(),
                self._selected_screen,
            )
            self._start_global = QPoint(start_x, start_y)
        else:
            self._start_global = start_global
        self._window.update()
        event.accept()

    def _mouse_move_event(self, event) -> None:
        if not self._selecting:
            event.ignore()
            return
        self._current_local = event.position().toPoint()
        self._window.update()
        event.accept()

    def _mouse_release_event(self, event) -> None:
        from PySide6.QtCore import QPoint

        end_local = event.position().toPoint()
        end_global_position = event.globalPosition().toPoint()
        self._current_local = end_local
        if self._selected_screen is not None:
            end_x, end_y = global_to_physical_point(
                end_global_position.x(),
                end_global_position.y(),
                self._selected_screen,
            )
            end_global = QPoint(end_x, end_y)
        else:
            end_global = end_global_position
        try:
            region = normalize_region(
                self._start_global.x(),
                self._start_global.y(),
                end_global.x(),
                end_global.y(),
            )
        except ValueError:
            self._selecting = False
            self._instruction_text = (
                "Selecao muito pequena\nArraste sobre a caixa de texto do jogo"
            )
            self._window.update()
            event.accept()
            return

        self.on_selected(region)
        self._window.close()
        event.accept()

    def _key_press_event(self, event) -> None:
        from PySide6.QtCore import Qt

        if event.key() == Qt.Key.Key_Escape:
            self._window.close()
