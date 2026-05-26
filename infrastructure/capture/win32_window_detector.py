from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DetectedWindow:
    handle: int
    title: str
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class Win32WindowDetector:
    win32gui_module: Any | None = None

    def find_game_window(self, title: str) -> DetectedWindow | None:
        needle = title.strip().casefold()
        if not needle:
            raise ValueError("window title must not be blank")

        win32gui = self.win32gui_module
        if win32gui is None:
            import win32gui

        matches: list[DetectedWindow] = []

        def visit(handle: int, _: object) -> None:
            if not win32gui.IsWindowVisible(handle):
                return
            window_title = win32gui.GetWindowText(handle)
            if needle not in window_title.casefold():
                return
            left, top, right, bottom = win32gui.GetWindowRect(handle)
            matches.append(
                DetectedWindow(
                    handle=handle,
                    title=window_title,
                    left=left,
                    top=top,
                    width=max(0, right - left),
                    height=max(0, bottom - top),
                )
            )

        win32gui.EnumWindows(visit, None)
        return matches[0] if matches else None
