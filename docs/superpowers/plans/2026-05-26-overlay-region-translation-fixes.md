# Overlay Region Translation Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make calibration usable by fixing overlay mouse resizing, region selection geometry, overlap warnings, and translation diagnostics.

**Architecture:** Keep UI thin and limited to rendering/input. Put pure geometry helpers in application or UI-adjacent pure modules, keep capture in infrastructure, and keep Ollama prompt/validation changes inside `infrastructure/translation`.

**Tech Stack:** Python 3, PySide6, pytest, MSS, Pillow, Ollama HTTP API.

---

## File Structure

- Modify `src/live_translator/ui/overlay_window.py`: use resize handles for all edges/corners and keep placement callbacks current.
- Create `src/live_translator/ui/overlay_geometry.py`: pure helper for overlay move/resize hit testing.
- Test `tests/unit/ui/test_overlay_geometry.py`: unit tests for resize handles without launching Qt.
- Modify `src/live_translator/ui/region_selector_window.py`: choose the screen under the cursor and show a full-screen selector on that screen.
- Create `src/live_translator/ui/screen_geometry.py`: pure screen-selection helper.
- Test `tests/unit/ui/test_screen_geometry.py`: screen selection by point with fallback.
- Create `src/live_translator/application/geometry.py`: pure rectangle overlap helper for `TextRegion` and `OverlayPlacement`.
- Test `tests/unit/application/test_geometry.py`: overlap and non-overlap cases.
- Modify `src/live_translator/ui/main_window.py`: show overlap warning and refresh it when region or overlay values change.
- Modify `src/live_translator/infrastructure/translation/prompt_builder.py`: strengthen complete-translation instructions.
- Modify `src/live_translator/infrastructure/translation/ollama_translator.py`: reject empty/blank translation payloads with a clear error.
- Test `tests/unit/infrastructure/translation/test_prompt_builder.py`: assert complete-translation requirements.
- Create `tests/unit/infrastructure/translation/test_ollama_translator.py`: translator validation coverage.
- Modify `src/live_translator/application/translation_pipeline_service.py`: clearer diagnostic around translation failures.
- Test `tests/unit/application/test_translation_pipeline_service.py`: failure diagnostic leaves overlay unchanged.

## Task 0: Branch and Baseline

**Files:**
- No source edits.

- [ ] **Step 1: Create the implementation branch**

Run:

```powershell
git switch -c fix/overlay-region-translation-calibration
```

Expected: branch changes from `main` to `fix/overlay-region-translation-calibration`.

- [ ] **Step 2: Run baseline tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest
```

Expected: all existing tests pass before changes, currently expected around `52 passed`.

## Task 1: Rectangle Overlap Helper

**Files:**
- Create: `src/live_translator/application/geometry.py`
- Test: `tests/unit/application/test_geometry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/application/test_geometry.py`:

```python
from live_translator.application.geometry import rectangles_overlap
from live_translator.domain.models import OverlayPlacement, TextRegion


def test_rectangles_overlap_when_regions_intersect():
    region = TextRegion(x=100, y=100, width=300, height=120)
    overlay = OverlayPlacement(x=250, y=150, width=400, height=80)

    assert rectangles_overlap(region, overlay) is True


def test_rectangles_do_not_overlap_when_edges_only_touch():
    region = TextRegion(x=100, y=100, width=300, height=120)
    overlay = OverlayPlacement(x=400, y=100, width=200, height=120)

    assert rectangles_overlap(region, overlay) is False


def test_rectangles_do_not_overlap_when_separated():
    region = TextRegion(x=100, y=100, width=300, height=120)
    overlay = OverlayPlacement(x=100, y=260, width=300, height=120)

    assert rectangles_overlap(region, overlay) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\application\test_geometry.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `live_translator.application.geometry`.

- [ ] **Step 3: Implement the helper**

Create `src/live_translator/application/geometry.py`:

```python
from __future__ import annotations

from live_translator.domain.models import OverlayPlacement, TextRegion


def rectangles_overlap(region: TextRegion, overlay: OverlayPlacement) -> bool:
    region_right = region.x + region.width
    region_bottom = region.y + region.height
    overlay_right = overlay.x + overlay.width
    overlay_bottom = overlay.y + overlay.height

    return (
        region.x < overlay_right
        and region_right > overlay.x
        and region.y < overlay_bottom
        and region_bottom > overlay.y
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\application\test_geometry.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src\live_translator\application\geometry.py tests\unit\application\test_geometry.py
git commit -m "Add rectangle overlap helper"
```

## Task 2: Overlay Warning in Settings Window

**Files:**
- Modify: `src/live_translator/ui/main_window.py`

- [ ] **Step 1: Import the overlap helper**

Add near the existing model import:

```python
from live_translator.application.geometry import rectangles_overlap
```

- [ ] **Step 2: Add a warning label**

In `SettingsWindow.__init__`, after `self._status = QLabel("")`, add:

```python
self._overlap_warning = QLabel("")
self._overlap_warning.setWordWrap(True)
self._overlap_warning.setStyleSheet(
    "QLabel {"
    "color: #ffd166;"
    "background-color: rgba(80, 45, 0, 120);"
    "border: 1px solid #b7791f;"
    "padding: 8px;"
    "}"
)
self._overlap_warning.hide()
```

- [ ] **Step 3: Add the warning to the layout**

In the main `layout`, add the warning before `self._status`:

```python
layout.addWidget(tabs)
layout.addWidget(self._overlap_warning)
layout.addWidget(self._status)
```

- [ ] **Step 4: Connect numeric field changes to warning refresh**

After existing button signal connections, add:

```python
for widget in (
    self._x,
    self._y,
    self._width,
    self._height,
    self._overlay_x,
    self._overlay_y,
    self._overlay_width,
    self._overlay_height,
):
    widget.valueChanged.connect(self._refresh_overlap_warning)
```

- [ ] **Step 5: Add warning refresh methods**

Add methods to `SettingsWindow`:

```python
def _text_region_from_fields(self) -> TextRegion:
    return TextRegion(
        x=self._x.value(),
        y=self._y.value(),
        width=self._width.value(),
        height=self._height.value(),
    )

def _refresh_overlap_warning(self, *_unused: object) -> None:
    try:
        region = self._text_region_from_fields()
        placement = self._placement_from_fields()
    except ValueError:
        self._overlap_warning.hide()
        return

    if rectangles_overlap(region, placement):
        self._overlap_warning.setText(
            "O overlay esta sobre a area capturada. "
            "Isso pode fazer o OCR ler a traducao em vez do texto do jogo."
        )
        self._overlap_warning.show()
        return

    self._overlap_warning.hide()
```

- [ ] **Step 6: Refresh warning after load and sync**

At the end of `_load_overlay_placement`, `_apply_selected_region`, and `_sync_overlay_fields`, call:

```python
self._refresh_overlap_warning()
```

In `_load_active_profile`, call it before both exits:

```python
if profile is None:
    self._name.setText("Default Lower Screen")
    self._x.setValue(256)
    self._y.setValue(950)
    self._width.setValue(2048)
    self._height.setValue(360)
    self._status.setText("Selecione a area do texto ou ajuste os numeros.")
    self._refresh_overlap_warning()
    return

self._name.setText(profile.name)
self._x.setValue(profile.text_region.x)
self._y.setValue(profile.text_region.y)
self._width.setValue(profile.text_region.width)
self._height.setValue(profile.text_region.height)
self._refresh_overlap_warning()
```

- [ ] **Step 7: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\application\test_geometry.py -v
```

Expected: PASS. UI warning is manually validated in Task 8.

- [ ] **Step 8: Commit**

Run:

```powershell
git add src\live_translator\ui\main_window.py
git commit -m "Warn when overlay overlaps capture region"
```

## Task 3: Overlay Mouse Resize Handles

**Files:**
- Create: `src/live_translator/ui/overlay_geometry.py`
- Modify: `src/live_translator/ui/overlay_window.py`
- Test: `tests/unit/ui/test_overlay_geometry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/ui/test_overlay_geometry.py`:

```python
from live_translator.ui.overlay_geometry import (
    ResizeHandle,
    WindowGeometry,
    detect_resize_handle,
    resize_geometry,
)


def test_detects_corner_resize_handle():
    assert detect_resize_handle(398, 118, 400, 120) == ResizeHandle.BOTTOM_RIGHT


def test_detects_left_edge_resize_handle():
    assert detect_resize_handle(2, 60, 400, 120) == ResizeHandle.LEFT


def test_detects_move_area_when_not_on_resize_handle():
    assert detect_resize_handle(200, 60, 400, 120) == ResizeHandle.MOVE


def test_resize_from_right_edge_changes_width():
    geometry = WindowGeometry(x=100, y=100, width=400, height=120)

    resized = resize_geometry(geometry, ResizeHandle.RIGHT, delta_x=50, delta_y=0)

    assert resized == WindowGeometry(x=100, y=100, width=450, height=120)


def test_resize_from_left_edge_moves_x_and_changes_width():
    geometry = WindowGeometry(x=100, y=100, width=400, height=120)

    resized = resize_geometry(geometry, ResizeHandle.LEFT, delta_x=50, delta_y=0)

    assert resized == WindowGeometry(x=150, y=100, width=350, height=120)


def test_resize_respects_minimum_size():
    geometry = WindowGeometry(x=100, y=100, width=180, height=70)

    resized = resize_geometry(geometry, ResizeHandle.TOP_LEFT, delta_x=100, delta_y=80)

    assert resized.width == 160
    assert resized.height == 60
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\ui\test_overlay_geometry.py -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement pure overlay geometry helper**

Create `src/live_translator/ui/overlay_geometry.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResizeHandle(str, Enum):
    MOVE = "move"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass(frozen=True, slots=True)
class WindowGeometry:
    x: int
    y: int
    width: int
    height: int


def detect_resize_handle(
    local_x: int,
    local_y: int,
    width: int,
    height: int,
    margin: int = 14,
) -> ResizeHandle:
    near_left = local_x <= margin
    near_right = width - local_x <= margin
    near_top = local_y <= margin
    near_bottom = height - local_y <= margin

    if near_top and near_left:
        return ResizeHandle.TOP_LEFT
    if near_top and near_right:
        return ResizeHandle.TOP_RIGHT
    if near_bottom and near_left:
        return ResizeHandle.BOTTOM_LEFT
    if near_bottom and near_right:
        return ResizeHandle.BOTTOM_RIGHT
    if near_left:
        return ResizeHandle.LEFT
    if near_right:
        return ResizeHandle.RIGHT
    if near_top:
        return ResizeHandle.TOP
    if near_bottom:
        return ResizeHandle.BOTTOM
    return ResizeHandle.MOVE


def resize_geometry(
    geometry: WindowGeometry,
    handle: ResizeHandle,
    *,
    delta_x: int,
    delta_y: int,
    min_width: int = 160,
    min_height: int = 60,
) -> WindowGeometry:
    x = geometry.x
    y = geometry.y
    width = geometry.width
    height = geometry.height

    if handle in {
        ResizeHandle.LEFT,
        ResizeHandle.TOP_LEFT,
        ResizeHandle.BOTTOM_LEFT,
    }:
        requested_width = width - delta_x
        width = max(min_width, requested_width)
        x = x + (geometry.width - width)
    elif handle in {
        ResizeHandle.RIGHT,
        ResizeHandle.TOP_RIGHT,
        ResizeHandle.BOTTOM_RIGHT,
    }:
        width = max(min_width, width + delta_x)

    if handle in {
        ResizeHandle.TOP,
        ResizeHandle.TOP_LEFT,
        ResizeHandle.TOP_RIGHT,
    }:
        requested_height = height - delta_y
        height = max(min_height, requested_height)
        y = y + (geometry.height - height)
    elif handle in {
        ResizeHandle.BOTTOM,
        ResizeHandle.BOTTOM_LEFT,
        ResizeHandle.BOTTOM_RIGHT,
    }:
        height = max(min_height, height + delta_y)

    return WindowGeometry(x=x, y=y, width=width, height=height)
```

- [ ] **Step 4: Update overlay window to use handles**

In `src/live_translator/ui/overlay_window.py`, import:

```python
from live_translator.ui.overlay_geometry import (
    ResizeHandle,
    WindowGeometry,
    detect_resize_handle,
    resize_geometry,
)
```

Replace `self._resizing = False` in `__init__` with:

```python
self._active_handle = ResizeHandle.MOVE
```

In `_handle_mouse_press`, replace the bottom-right-only detection with:

```python
position = event.position().toPoint()
self._active_handle = detect_resize_handle(
    position.x(),
    position.y(),
    self._drag_start_geometry.width(),
    self._drag_start_geometry.height(),
)
```

In `_handle_mouse_move`, replace the resize/move block with:

```python
if self._active_handle == ResizeHandle.MOVE:
    self._window.move(
        self._drag_start_geometry.x() + delta.x(),
        self._drag_start_geometry.y() + delta.y(),
    )
else:
    resized = resize_geometry(
        WindowGeometry(
            x=self._drag_start_geometry.x(),
            y=self._drag_start_geometry.y(),
            width=self._drag_start_geometry.width(),
            height=self._drag_start_geometry.height(),
        ),
        self._active_handle,
        delta_x=delta.x(),
        delta_y=delta.y(),
    )
    self._window.setGeometry(
        resized.x,
        resized.y,
        resized.width,
        resized.height,
    )
    self._label.setGeometry(0, 0, resized.width, resized.height)
```

In `_handle_mouse_release`, replace `self._resizing = False` with:

```python
self._active_handle = ResizeHandle.MOVE
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\ui\test_overlay_geometry.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src\live_translator\ui\overlay_geometry.py src\live_translator\ui\overlay_window.py tests\unit\ui\test_overlay_geometry.py
git commit -m "Improve overlay mouse resizing"
```

## Task 4: Region Selector Screen Geometry

**Files:**
- Create: `src/live_translator/ui/screen_geometry.py`
- Modify: `src/live_translator/ui/region_selector_window.py`
- Test: `tests/unit/ui/test_screen_geometry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/ui/test_screen_geometry.py`:

```python
from live_translator.ui.screen_geometry import ScreenRect, select_screen_for_point


def test_selects_screen_containing_point():
    screens = (
        ScreenRect(x=0, y=0, width=1920, height=1080),
        ScreenRect(x=1920, y=0, width=1920, height=1080),
    )

    assert select_screen_for_point(2000, 500, screens) == screens[1]


def test_uses_first_screen_as_fallback():
    screens = (
        ScreenRect(x=0, y=0, width=1920, height=1080),
        ScreenRect(x=1920, y=0, width=1920, height=1080),
    )

    assert select_screen_for_point(-500, -500, screens) == screens[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\ui\test_screen_geometry.py -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement screen geometry helper**

Create `src/live_translator/ui/screen_geometry.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScreenRect:
    x: int
    y: int
    width: int
    height: int


def select_screen_for_point(
    point_x: int,
    point_y: int,
    screens: Sequence[ScreenRect],
) -> ScreenRect:
    if not screens:
        raise ValueError("at least one screen is required")

    for screen in screens:
        if (
            screen.x <= point_x < screen.x + screen.width
            and screen.y <= point_y < screen.y + screen.height
        ):
            return screen
    return screens[0]
```

- [ ] **Step 4: Update region selector show behavior**

In `src/live_translator/ui/region_selector_window.py`, import:

```python
from live_translator.ui.screen_geometry import ScreenRect, select_screen_for_point
```

Remove this line from `__post_init__` because explicit geometry is more reliable for multi-monitor selection:

```python
self._window.setWindowState(Qt.WindowState.WindowFullScreen)
```

Replace `show` with:

```python
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
            )
        )

    selected = select_screen_for_point(
        cursor_position.x(),
        cursor_position.y(),
        tuple(screens),
    )
    self._window.setGeometry(
        selected.x,
        selected.y,
        selected.width,
        selected.height,
    )
    self._window.show()
    self._window.raise_()
    self._window.activateWindow()
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\ui\test_screen_geometry.py tests\unit\ui\test_region_selector_window.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src\live_translator\ui\screen_geometry.py src\live_translator\ui\region_selector_window.py tests\unit\ui\test_screen_geometry.py
git commit -m "Fix region selector screen selection"
```

## Task 5: Prompt and Translator Validation

**Files:**
- Modify: `src/live_translator/infrastructure/translation/prompt_builder.py`
- Modify: `src/live_translator/infrastructure/translation/ollama_translator.py`
- Modify: `tests/unit/infrastructure/translation/test_prompt_builder.py`
- Create: `tests/unit/infrastructure/translation/test_ollama_translator.py`

- [ ] **Step 1: Extend prompt tests**

Add to `tests/unit/infrastructure/translation/test_prompt_builder.py`:

```python
def test_translation_prompt_requires_complete_translation_without_summary():
    prompt = build_translation_prompt("Line one.\nLine two.", [], "pt-BR")

    assert "Traduza todo o texto" in prompt
    assert "Nao resuma" in prompt
    assert "Nao omita frases" in prompt
```

- [ ] **Step 2: Create translator validation tests**

Create `tests/unit/infrastructure/translation/test_ollama_translator.py`:

```python
import pytest

from live_translator.infrastructure.translation.ollama_client import (
    OllamaInvalidResponseError,
)
from live_translator.infrastructure.translation.ollama_translator import OllamaTranslator


class FakeClient:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload
        self.prompt = ""

    def generate(self, prompt: str):
        self.prompt = prompt
        return self.payload


def test_translator_returns_translation_result():
    client = FakeClient({"translated_text": "Ola mundo"})
    translator = OllamaTranslator(client)

    result = translator.translate("Hello world", [])

    assert result.source_text == "Hello world"
    assert result.translated_text == "Ola mundo"


def test_translator_rejects_blank_translated_text():
    translator = OllamaTranslator(FakeClient({"translated_text": "   "}))

    with pytest.raises(OllamaInvalidResponseError, match="translated_text is empty"):
        translator.translate("Hello world", [])
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\infrastructure\translation\test_prompt_builder.py tests\unit\infrastructure\translation\test_ollama_translator.py -v
```

Expected: FAIL because the prompt lacks the exact complete-translation instructions and blank translation raises `ValueError` instead of `OllamaInvalidResponseError`.

- [ ] **Step 4: Strengthen translation prompt**

In `build_translation_prompt`, add these lines before the JSON instruction:

```python
"Traduza todo o texto de entrada, incluindo todas as linhas e frases.\n"
"Nao resuma. Nao omita frases. Nao traduza apenas o trecho mais recente.\n"
```

- [ ] **Step 5: Validate blank translation in `OllamaTranslator`**

In `OllamaTranslator.translate`, after the existing type check, add:

```python
translated_text = translated_text.strip()
if not translated_text:
    raise OllamaInvalidResponseError("translated_text is empty")
```

Keep `TranslationResult` construction using the stripped text.

- [ ] **Step 6: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\infrastructure\translation\test_prompt_builder.py tests\unit\infrastructure\translation\test_ollama_translator.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src\live_translator\infrastructure\translation\prompt_builder.py src\live_translator\infrastructure\translation\ollama_translator.py tests\unit\infrastructure\translation\test_prompt_builder.py tests\unit\infrastructure\translation\test_ollama_translator.py
git commit -m "Improve translation prompt validation"
```

## Task 6: Pipeline Translation Failure Diagnostic

**Files:**
- Modify: `src/live_translator/application/translation_pipeline_service.py`
- Modify: `tests/unit/application/test_translation_pipeline_service.py`

- [ ] **Step 1: Add failing diagnostic test**

Add to `tests/unit/application/test_translation_pipeline_service.py`:

```python
@dataclass
class FailingTranslator:
    message: str = "translated_text is empty"

    def translate(self, text: str, context: list[str]) -> TranslationResult:
        raise ValueError(self.message)


def test_translation_failure_records_clear_diagnostic_and_does_not_update_overlay():
    pipeline, parts = build_pipeline(translator=FailingTranslator())

    try:
        pipeline.process_frame(object())
    except ValueError:
        pass

    assert pipeline.last_diagnostic == "traducao falhou: translated_text is empty"
    assert parts["overlay"].shown == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\application\test_translation_pipeline_service.py::test_translation_failure_records_clear_diagnostic_and_does_not_update_overlay -v
```

Expected: FAIL because the current diagnostic is `erro: translated_text is empty`.

- [ ] **Step 3: Add a translator failure boundary**

In `process_frame`, replace:

```python
self._set_diagnostic("traduzindo")
result = self.translator.translate(normalized_text, self._context)
```

with:

```python
self._set_diagnostic("traduzindo")
try:
    result = self.translator.translate(normalized_text, self._context)
except Exception as error:
    self._set_diagnostic(f"traducao falhou: {error}")
    raise
```

Leave the outer `except` in place but change it to preserve an existing diagnostic:

```python
except Exception as error:
    if self.last_diagnostic is None or not self.last_diagnostic.startswith(
        "traducao falhou:"
    ):
        self._set_diagnostic(f"erro: {error}")
    raise
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\application\test_translation_pipeline_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src\live_translator\application\translation_pipeline_service.py tests\unit\application\test_translation_pipeline_service.py
git commit -m "Clarify translation failure diagnostics"
```

## Task 7: Full Automated Validation

**Files:**
- No source edits unless tests reveal a regression.

- [ ] **Step 1: Run full test suite**

Run:

```powershell
.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Inspect architecture-sensitive imports**

Run:

```powershell
rg "PySide6|sqlite3|requests|mss|cv2|PIL|Ollama" src\live_translator\domain src\live_translator\application
```

Expected:

- no forbidden imports in `domain`;
- no direct concrete infrastructure usage in `application`;
- references to protocol names or diagnostic text are acceptable if they are not direct imports of concrete adapters.

- [ ] **Step 3: Commit any test-only fix**

Only if Step 1 or Step 2 required a small fix, commit it:

```powershell
git add <changed-files>
git commit -m "Stabilize calibration fix tests"
```

## Task 8: Manual GUI Validation

**Files:**
- No source edits unless manual validation reveals a bug.

- [ ] **Step 1: Launch the app**

Run:

```powershell
.venv\Scripts\pythonw.exe -m live_translator.app.main
```

Expected: settings window opens without terminal-only behavior.

- [ ] **Step 2: Validate region selector**

In the app:

1. Click `Selecionar area do texto`.
2. Confirm the selector covers the active monitor, not a small corner.
3. Drag over the game text box.
4. Confirm the preview updates with the selected region.

Expected: selection is visible and preview shows the source text area only.

- [ ] **Step 3: Validate overlay resizing**

In the app:

1. Click `Ajustar overlay`.
2. Drag the overlay body.
3. Drag left, right, top, bottom, and a corner.
4. Confirm numeric fields update while dragging.
5. Click `Salvar overlay`.

Expected: overlay moves and resizes by mouse, then keeps saved placement.

- [ ] **Step 4: Validate overlap warning**

In the app:

1. Move overlay over the selected text area.
2. Confirm the warning appears.
3. Move overlay outside the selected text area.
4. Confirm the warning disappears.

Expected: warning explains OCR contamination risk and does not block saving.

- [ ] **Step 5: Validate translation behavior**

In the app:

1. Keep overlay outside the captured text region.
2. Start or resume capture.
3. Use a multi-line game dialogue.
4. Confirm the overlay translates the full dialogue when OCR source text is complete.

Expected: no prompt echo; no blank overlay; diagnostics distinguish cache/empty/failure/completed states.

## Task 9: Report and Changelog

**Files:**
- Modify: `CHANGELOG.md`
- Create: `docs/relatorios/relatorio-v03-confiabilidade-calibracao.md`

- [ ] **Step 1: Update changelog**

Add an `Unreleased` entry or top release note:

```markdown
## Unreleased

- Improved overlay calibration with mouse-based edge and corner resizing.
- Fixed region selector screen targeting for text-area selection.
- Added warning when overlay overlaps the OCR capture region.
- Strengthened translation prompt validation and failure diagnostics.
```

- [ ] **Step 2: Create report**

Create `docs/relatorios/relatorio-v03-confiabilidade-calibracao.md`:

```markdown
# Relatório V03 — Confiabilidade da calibração

## Resumo

This checkpoint improves calibration reliability. The overlay is treated as translated output only, the source text region is easier to select, and the app warns when overlay placement can contaminate OCR.

## Entregas

- Added rectangle overlap detection for text region and overlay placement.
- Added in-app overlap warning.
- Improved overlay mouse resizing across edges and corners.
- Fixed region selector screen selection.
- Strengthened translation prompts and blank-result validation.
- Added clearer diagnostics for translation failure.

## Validação

- Automated tests: `python -m pytest`
- Manual checks: region selection, capture preview, overlay resize, overlap warning, multi-line dialogue translation.

## Pendências e riscos

- Translation completeness still depends on OCR quality and model behavior.
- Window-relative capture remains a future improvement.
- Packaging and production logging are still pending.
```

- [ ] **Step 3: Commit documentation**

Run:

```powershell
git add CHANGELOG.md docs\relatorios\relatorio-v03-confiabilidade-calibracao.md
git commit -m "Document calibration fixes"
```

## Final Checkpoint

- [ ] **Step 1: Confirm branch status**

Run:

```powershell
git status --short --branch
```

Expected: clean working tree on `fix/overlay-region-translation-calibration`.

- [ ] **Step 2: Summarize commits**

Run:

```powershell
git log --oneline main..HEAD
```

Expected: commits for geometry helper, overlap warning, overlay resizing, region selector fix, translation validation, diagnostics, and docs.

- [ ] **Step 3: Prepare user handoff**

Report:

- branch name;
- test result;
- manual validation result;
- any remaining issue that needs user confirmation with the real game.
