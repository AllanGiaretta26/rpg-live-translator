# Report V10

## Summary

This checkpoint improves the main window UX by separating the capture-based
Universal workflow from the RPG Maker MV/MZ catalog/runtime workflow. The app
now makes the active mode clearer and disables controls that do not apply to
the current mode.

## Completed

- Renamed the main workflow tabs to separate `Universal` from
  `RPG Maker MV/MZ`.
- Grouped related controls with clearer sections for active mode, project
  setup, Universal capture/OCR, MV/MZ catalog maintenance, batch translation,
  shared overlay settings and run-time actions.
- Added centralized mode-control state for the main window.
- Disabled Universal capture controls while RPG Maker MV/MZ mode is active.
- Disabled MV/MZ catalog, batch, cache and error controls while Universal mode
  is active.
- Kept RPG Maker project selection/import available when the user selects
  RPG Maker MV/MZ in the mode dropdown, even before saving the mode.
- Kept overlay controls available in both workflows.

## Behavior Notes

- In Universal mode, the app keeps capture/OCR controls active and marks MV/MZ
  catalog/cache/lote controls as unavailable.
- In RPG Maker MV/MZ mode, the app pauses capture as before and makes the
  catalog/runtime controls the active workflow.
- `Reprocessar fala atual` is enabled only when RPG Maker MV/MZ mode is active
  and the runtime service is available.
- Batch controls now follow the same mode state: start is available only when
  MV/MZ is active and no batch is running; pause/resume/cancel are available
  only during an active MV/MZ batch.

## Validation

Automated tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

Result:

```txt
120 passed
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

- The new mode-state tests cover the behavior rules without instantiating Qt.
  A future UI test layer with Qt widgets could catch visual regressions more
  directly.
- The main window still uses a tabbed desktop layout. A larger redesign could
  improve visual density further, but this checkpoint intentionally keeps the
  change focused.
