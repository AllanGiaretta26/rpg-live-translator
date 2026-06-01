# Report V12

## Summary

This checkpoint completes the expanded RPG Maker MV/MZ database, battle-event
patch and project-scoped cache work. The catalog now imports standard database
files, system terms and troop events; batch translation can cache them by
default, and patch export can write translated database JSON alongside event
JSON files.

## Completed

- Added catalog types for `item_name`, `item_description`, `skill_name` and
  `skill_description`.
- Added catalog types for `skill_message`, `weapon_name`, `weapon_description`,
  `armor_name`, `armor_description`, `state_name`, `state_message`,
  `class_name`, `enemy_name`, `troop_message`, `troop_choice`,
  `troop_scrolling_text` and `troop_speaker`.
- Added catalog types for `actor_name` and `system_term`.
- Added parser support for `Items.json`, `Skills.json`, `Weapons.json`,
  `Armors.json`, `States.json`, `Classes.json`, `Enemies.json`, `Actors.json`,
  `System.json` and `Troops.json`.
- Added database origin metadata with SQLite migration for existing catalogs.
- Added project-scoped translation cache for RPG Maker MV/MZ while keeping the
  global cache for Universal/OCR mode.
- Added batch defaults and UI filters for database, actor, system and troop
  text.
- Added patch replacement for database `name`, `description` and nested system
  term fields.
- Added patch replacement for battle event commands in `Troops.json`.
- Added translation validation for RPG Maker escape codes such as `\N[1]` and
  battle placeholders such as `%1`.
- Added type-aware translation prompts for dialogue, names, descriptions,
  system terms and battle/status messages.
- Added line wrapping for long patched message/scrolled-text lines.
- Updated docs and MV/MZ checklist for the expanded patch scope.

## Behavior Notes

- Patch generation still uses only translations that already exist in cache.
- Database replacement validates the file, object ID and field name before
  writing translated text.
- System term replacement validates the nested term path before writing.
- Troop event replacement uses the same command replacement flow as map events,
  scoped to the troop ID and page.
- If a cached translation drops an RPG Maker escape code, it is treated as
  invalid and skipped/retranslated depending on the flow.
- If a cached translation drops `%1`, `%2` or `%3`, it is treated as invalid.
- `speaker` remains disabled by default in batch translation.
- Common `speaker` remains optional in patch export; `troop_speaker` is included
  as a battle text type.

## Validation

Automated tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

Result:

```txt
154 passed
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
20 files already formatted
```

## Remaining Risks

- Custom RPG Maker plugins may store menu or database text outside standard
  database and `System.json` fields.
- Manual testing across multiple MV and MZ games is still needed before treating
  the patcher as broadly safe.
