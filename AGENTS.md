# Repository Guidelines

## Project Structure & Module Organization

This is a Windows-first Python desktop app for live translation of RPG Maker games. Product context lives in `docs/BRIEFING.md`, and the current layer design lives in `ARCHITECTURE.md`.

- `src/live_translator/ui/` for windows, overlays, hotkeys, and user-facing state.
- `src/live_translator/application/` for capture, OCR, translate, cache, and display orchestration.
- `src/live_translator/domain/` for core models, cache keys, and language rules.
- `src/live_translator/infrastructure/` for OCR, LLM, screen capture, storage, and Windows adapters.
- `src/live_translator/app/` for bootstrap and composition root.
- `src/live_translator/config/` for settings and defaults.
- `src/live_translator/scripts/` for development utilities.
- `tests/` for automated tests mirroring the package layout.
- `docs/` for reports and planning notes.

## Build, Test, and Development Commands

- `python -m venv .venv` creates a local virtual environment.
- `.venv\Scripts\Activate.ps1` activates it in Windows PowerShell.
- `.venv\Scripts\python.exe -m pip install -e .[dev,desktop]` installs the app, tests, and desktop dependencies.
- `.venv\Scripts\python.exe -m pytest` runs the test suite.
- `.venv\Scripts\pythonw.exe -m live_translator.app.main` starts the desktop app without a console.
- `.venv\Scripts\python.exe -m live_translator.scripts.capture_region --output captures\latest.png` saves a capture preview.
- `ruff check .` runs lint checks.
- `ruff format .` formats Python code.

## Coding Style & Naming Conventions

Use Python 3 with 4-space indentation, type hints for public functions, and small modules grouped by responsibility. Use `snake_case` for functions, methods, modules, and variables; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants.

Keep UI logic thin. UI must not access SQLite, Ollama, MSS, OpenCV, or capture adapters directly. Put translation flow decisions in `application`, pure rules and protocols in `domain`, and external-service details in `infrastructure`.

## Testing Guidelines

Use `pytest`. Name files `test_<module>.py` and test functions `test_<behavior>()`. Prioritize translation cache behavior, OCR/translation orchestration, configuration loading, and fallback paths. Use fixtures for OCR text, screenshots, and RPG Maker dialogue examples.

## Commit & Pull Request Guidelines

Use short imperative commit subjects, for example `Move package to src layout` or `Add capture preview action`.

Pull requests should include a concise description, linked issue or task when available, test results, and screenshots or short screen recordings for UI/overlay changes.

## Security & Configuration Tips

Do not commit API keys, local model paths, captured game screenshots containing personal data, or machine-specific configuration. Keep secrets in environment variables or local ignored config files. Document any required Windows permissions for screen capture, overlays, or global hotkeys.
