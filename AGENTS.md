# Repository Guidelines

## Project Structure & Module Organization

This repository is currently documentation-first. Project context lives in `BRIEFING.md`, the proposed design in `ARCHITECTURE.md`, and release/security placeholders in `CHANGELOG.md` and `SECURITY.md`.

The planned application is a Windows-first Python desktop app for live translation of RPG Maker games. When source code is added, follow the modular monolith described in `ARCHITECTURE.md`:

- `src/live_translator/ui/` for windows, overlays, hotkeys, and user-facing state.
- `src/live_translator/application/` for capture, OCR, translate, cache, and display orchestration.
- `src/live_translator/domain/` for core models, cache keys, and language rules.
- `src/live_translator/infrastructure/` for OCR, LLM, screen capture, storage, and Windows adapters.
- `tests/` for automated tests mirroring the `src/` package layout.
- `assets/` for icons, screenshots, fixtures, and UI resources.

## Build, Test, and Development Commands

No build system is committed yet. Once Python packaging is introduced, prefer standard commands:

- `python -m venv .venv` creates a local virtual environment.
- `.venv\Scripts\Activate.ps1` activates it in Windows PowerShell.
- `pip install -e .[dev]` installs the app and development tools.
- `pytest` runs the test suite.
- `ruff check .` runs lint checks.
- `ruff format .` formats Python code.

Keep command changes synchronized with `pyproject.toml` when that file is added.

## Coding Style & Naming Conventions

Use Python 3 with 4-space indentation, type hints for public functions, and small modules grouped by responsibility. Use `snake_case` for functions, methods, modules, and variables; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants.

Keep UI logic thin. Put translation flow decisions in `application`, pure rules in `domain`, and external-service details in `infrastructure`.

## Testing Guidelines

Use `pytest`. Name files `test_<module>.py` and test functions `test_<behavior>()`. Prioritize translation cache behavior, OCR/translation orchestration, configuration loading, and fallback paths. Use fixtures for OCR text, screenshots, and RPG Maker dialogue examples.

## Commit & Pull Request Guidelines

This checkout does not include Git history, so no existing commit convention can be inferred. Use short imperative commit subjects, for example `Add translation cache interface` or `Document Windows overlay constraints`.

Pull requests should include a concise description, linked issue or task when available, test results, and screenshots or short screen recordings for UI/overlay changes.

## Security & Configuration Tips

Do not commit API keys, local model paths, captured game screenshots containing personal data, or machine-specific configuration. Keep secrets in environment variables or local ignored config files. Document any required Windows permissions for screen capture, overlays, or global hotkeys.
