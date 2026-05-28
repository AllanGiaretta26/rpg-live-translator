# Report V7

## Summary

This checkpoint stabilizes the RPG Maker MV/MZ workflow after the first runtime
tests with real game dialogue. The focus was cache recovery and diagnostics:
the app now gives the user tools to identify bad batch entries, clear
contaminated cache for the current catalog and force a fresh translation for
the current runtime line.

## Completed

- Hid the overlay/capture overlap warning while `RPG Maker MV/MZ` mode is
  active, because capture/OCR is disabled in that mode.
- Added catalog cache count: `Cache: X/Y entradas ja traduzidas`.
- Added manual cleanup for contaminated translations in the active MV/MZ
  catalog.
- Added runtime action to reprocess the current MV/MZ line by deleting its cache
  entry and translating again.
- Added SQLite persistence for last batch errors in `rpg_maker_batch_errors`.
- Added UI action to inspect errors from the most recent batch, including entry
  ID, origin, source text and error message.
- Updated next-step checklists to mark the implemented cache and diagnostic
  items.

## Behavior Notes

- Cache cleanup is scoped to the active MV/MZ project catalog. It does not scan
  unrelated translation cache entries from other games.
- The app keeps only the last batch error list. Starting a new batch clears the
  previous batch errors.
- Runtime cache validation still happens automatically: contaminated cached
  translations are ignored when the same line appears again.
- `Reprocessar fala atual` is the manual escape hatch when the user wants to
  force a new translation immediately.

## Validation

Automated tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

Result:

```txt
103 passed
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

- Plugin compatibility can vary with custom MV/MZ message systems.
- The MV/MZ plugin still needs manual installation in Steam/distributed games.
- Last batch errors can be viewed in the app, but not exported to a file yet.
- Runtime diagnostics are visible in the UI but are not stored as a full session
  log.
- Future work is still needed for translated patch export or direct in-game
  text replacement without overlay.
