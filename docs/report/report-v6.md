# Report V6

## Summary

This checkpoint adds the first practical RPG Maker MV/MZ workflow on top of the
capture-based MVP. The app can import MV/MZ text catalogs, pre-cache
translations in batches, receive runtime text from a game plugin and diagnose
whether bad overlay output came from the plugin, cache or model.

## Completed

- Added explicit Universal and RPG Maker MV/MZ modes.
- Added read-only MV/MZ detection for `www/data` and `data`.
- Added JSON parsing for `MapXXX.json` and `CommonEvents.json`.
- Added `rpg_maker_text_catalog` in SQLite for extracted source text and origin.
- Added catalog UI with single-entry translation and batch translation.
- Added batch controls for `100`, `500` or all entries, with progress,
  cancellation, cache-hit count and error count.
- Added runtime HTTP bridge and `LiveTranslatorBridge.js`.
- Added MV/MZ runtime diagnostics in the `Executar` status panel.
- Added prompt-leak detection and retry with a shorter translation prompt.
- Added cache validation in MV/MZ runtime so contaminated cached translations
  are ignored and overwritten.

## Manual Findings

- MV/MZ runtime path is much faster than the Universal OCR path when cache hits
  are available.
- The `Fonte MV/MZ` diagnostic confirmed that some bad overlay outputs were not
  OCR-related: capture was disabled and the runtime was using cached text.
- Some early batch/cache entries contained prompt instructions in
  `translated_text`. The runtime now treats those cache entries as invalid.
- The overlay/capture overlap warning can be misleading in MV/MZ mode because
  capture is disabled there.

## Validation

Automated tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

Result:

```txt
96 passed
```

Lint:

```powershell
.venv\Scripts\python.exe -m ruff check .
```

Result:

```txt
All checks passed!
```

## Remaining Risks

- Batch translation still only reports error counts; it does not yet persist
  per-entry error details.
- Plugin compatibility can vary with custom message systems.
- The MV/MZ plugin still needs manual installation in Steam/distributed games.
- Cache cleanup tools are not implemented yet.
- The overlay/capture overlap warning should be hidden or reworded in MV/MZ
  mode.
