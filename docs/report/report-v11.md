# Report V11

## Summary

This checkpoint adds the first RPG Maker MV/MZ JSON patch workflow. The current
overlay/runtime workflow remains unchanged, while cached catalog translations
can now be exported to translated JSON files, applied to the game with backup,
and restored from the latest backup.

## Completed

- Added a patch service for `Map*.json` and `CommonEvents.json`.
- Added patch support for messages, choices, scrolling text and optional
  speakers.
- Added exact-origin replacement using catalog metadata instead of global text
  search.
- Added patch reports in JSON and Markdown.
- Added automatic backup before applying patch files to the active project.
- Added restoration from the latest backup created for the active project.
- Added UI controls in the RPG Maker MV/MZ tab for generating, applying and
  restoring patches.

## Behavior Notes

- Patch generation uses only translations that already exist in cache.
- Missing cache entries, invalid translations and source mismatches are skipped
  and reported.
- `speaker` entries are skipped unless `Incluir speakers` is checked.
- Generated patches are written under `exports/patches/`.
- Backups are written under `backups/patches/`.
- Database files such as `Skills.json` and `Items.json` are not covered yet.

## Validation

Automated tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

Result:

```txt
124 passed
```

Lint:

```powershell
.venv\Scripts\python.exe -m ruff check .
```

Result:

```txt
All checks passed!
```

Formatting check for changed Python files:

```powershell
.venv\Scripts\python.exe -m ruff format --check <changed-files>
```

Result:

```txt
6 files already formatted
```

## Remaining Risks

- Applying a patch overwrites game JSON files by design, so backup integrity is
  essential.
- The first patch scope does not translate database UI content such as skills,
  items, weapons, armors or states.
- Games with custom event/plugin formats may have text outside the currently
  cataloged commands.
