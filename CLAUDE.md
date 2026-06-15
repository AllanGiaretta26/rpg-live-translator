# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Windows-first Python desktop app that translates RPG Maker game text to pt-BR in real time. Two paths: a **universal** mode (screen capture → Ollama vision OCR → translate → PySide6 overlay) and an **RPG Maker MV/MZ** mode (reads game JSON catalog + receives live dialogue via a local HTTP bridge plugin, avoiding OCR). Results are cached in SQLite. Most code, comments, docs, and UI strings are in **Brazilian Portuguese** — match that when editing.

## Commands

```powershell
# Setup (Python 3.13+)
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .[dev,desktop]

# Tests
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pytest tests/unit/domain/test_translation_quality.py            # single file
.venv\Scripts\python.exe -m pytest tests/unit/domain/test_translation_quality.py::test_name  # single test
.venv\Scripts\python.exe -m pytest -k "patch and not batch"                                       # by expression

# Lint / format
ruff check .
ruff format .

# Run the app (GUI, no console window)
.venv\Scripts\pythonw.exe -m live_translator.app.main

# Dev scripts
.venv\Scripts\python.exe -m live_translator.scripts.create_profile --name "Game" --window-title "Manual Region" --x 256 --y 950 --width 2048 --height 360
.venv\Scripts\python.exe -m live_translator.scripts.capture_region --output captures\latest.png
```

The test suite runs **without** desktop/Ollama dependencies — don't add tests that require a live Ollama server, a display, or `pyside6`/`mss`.

## Architecture

Layered monolith under `src/live_translator/`. Dependency rule: **UI and Infrastructure depend on Domain; Domain depends on nothing external.** UI must never touch SQLite, Ollama, MSS, or capture adapters directly — it goes through Application services.

- `domain/` — frozen dataclasses (`models.py`), `Protocol` contracts (`interfaces.py`), translation-quality heuristics (`translation_quality.py`). **No imports of PySide6, mss, sqlite3, requests, etc.**
- `application/` — use-case orchestration (capture loop, translation pipeline, mode/profile/overlay settings, RPG Maker import/batch/runtime/patch). Pure-ish; depends only on domain Protocols.
- `infrastructure/` — concrete adapters implementing domain Protocols: `capture/` (MSS, win32), `image/` (hash, change detection, preprocess), `persistence/` (SQLite repositories), `translation/` (Ollama client/translator/vision/prompt), `rpgmaker/` (JSON parser, project detector, HTTP bridge server, and the `plugin/LiveTranslatorBridge.js` runtime plugin).
- `ui/` — PySide6 main/calibration window, overlay, region selector.
- `app/bootstrap.py` — **composition root**. The single place where concrete implementations are wired to Protocols. Start here to understand how anything connects.
- `config/` — `defaults.py` (constants) + `settings.py` (`AppSettings`).

### Key wiring facts (`app/bootstrap.py`)

- **Graceful headless degradation via `ImportError`**: if `pyside6`/`mss` aren't installed, bootstrap swaps in `ConsoleOverlay`, `ConsoleUiApp`, and `NullScreenCaptureService`. This is why tests and CI can run the full bootstrap without a GUI. Preserve this pattern — keep desktop imports lazy/guarded, never import `pyside6`/`mss` at module top level outside `ui/` and `infrastructure/capture/`.
- `bootstrap()` returns an `AppRuntime` (frozen dataclass holding every service). `AppRuntime.start()` warns if Ollama is down, optionally starts the RPG Maker bridge HTTP server, then runs the UI. It accepts `overlay_factory`/`ui_factory` injection for tests.

### Pipeline (`application/translation_pipeline_service.py`)

Universal-mode frame flow, short-circuiting in this order: change detector → image-hash cache → OCR extract + normalize → text cache → translate → save both caches → overlay. It also filters out OCR results that look like the prompt leaking back (`_looks_like_non_game_text`) and records `last_diagnostic` / `last_timing_summary` for the Status panel.

### Translation quality is correctness-critical (`domain/translation_quality.py`)

This module guards against contaminated/invalid translations and is the heart of MV/MZ patch quality. `looks_like_invalid_translation()` rejects: prompt/context leaks, dropped RPG Maker escape codes (`\N[1]`, `\V[2]`, `\C[3]`, `\I[64]`) and `%1` placeholders, unexpected leading currency markers (`€`/`¥`/`￥`), and over-long names/descriptions. Cached translations that fail these checks are treated as cache misses and re-translated; the batch counts these discards per rule (`invalid_translation_reason`) in its final status. When changing translation behavior or prompts, update these heuristics and their tests together — including the regression corpus in `tests/data/translation_regression_corpus.json` (real source/translation pairs run by `tests/unit/domain/test_translation_regression_corpus.py`).

### Caching & scope

`translations` cache lookups take a `scope` kwarg (see `TranslationCache` Protocol). MV/MZ translations are scoped to the active project path so different games don't share/contaminate caches. `image_cache` keys on perceptual image hash.

### RPG Maker MV/MZ mode

- **Read-only catalog import**: `rpgmaker/project_detector.py` + `json_text_parser.py` extract text from `Map*.json`, `CommonEvents.json`, `System.json`, database files (`Items`, `Skills`, `Weapons`, `Armors`, `States`, `Classes`, `Enemies`, `Actors`, `Troops`), and `Scenario.json`, preserving exact origin (file/event/page/command/param or object id/field) for safe write-back.
- **Runtime bridge**: `rpgmaker/runtime_bridge_server.py` runs a local HTTP server (default `http://127.0.0.1:8765/rpgmaker/text`); the in-game `LiveTranslatorBridge.js` plugin POSTs current dialogue, processed by `RpgMakerRuntimeService`.
- **Patch generation** (`application/rpg_maker_patch_service.py`): builds translated JSON from catalog + existing cache only (does **not** call Ollama). Validates that source text still matches the game JSON before replacing; writes to `exports/patches/<game>-ptBR-<ts>/data/` with a report. Applying patches backs up to `backups/patches/...` first. The app never modifies game files except via the explicit apply/restore actions.

## Conventions

- Type hints on public functions; `snake_case` / `PascalCase` / `UPPER_SNAKE_CASE`; small single-responsibility modules.
- Ruff line length 88, target `py313`.
- Tests mirror the package layout under `tests/unit/<layer>/` and `tests/integration/`; name `test_<module>.py` / `test_<behavior>()`. Test against Protocols with fakes/mocks rather than real infrastructure.
- Settings load from env (prefix `LIVE_TRANSLATOR_`, e.g. `LIVE_TRANSLATOR_RPG_MAKER_BRIDGE_PORT`) and a `.env` file via `pydantic-settings`; defaults live in `config/defaults.py`. `settings.py` has a no-pydantic dataclass fallback — keep both definitions in sync when adding a setting.
- Commit subjects: short imperative (e.g. "Add capture preview action").

## Reference docs

`ARCHITECTURE.md` describes the actual architecture (layers, dependency rules, failure-handling map) and is kept in sync with the code — when it drifts, the code wins and `app/bootstrap.py` is the source of truth. `README.md` is the end-user guide (pt-BR). `docs/rpg-maker-mvmz.md` covers the full RPG Maker MV/MZ workflow: plugin install/recovery, diagnostics and patch generation. `docs/README.md` is the documentation index and style guide. `AGENTS.md` mirrors these contributor guidelines. `docs/BRIEFING.md` holds product context; `docs/` has reports and plans.
