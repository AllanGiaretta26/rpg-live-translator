# Report V13

## Summary

This checkpoint stabilizes RPG Maker MV/MZ batch translation and patch export
after the first large Demons Roots patch tests. The main fixes prevent
punctuation-only text from being expanded into invented dialogue, keep visual
RPG Maker prefixes on wrapped patch lines, and reject translations that add
unexpected visual markers such as `€`.

## Completed

- Added passthrough handling for RPG Maker text that contains only punctuation
  or control tokens, such as `...`.
- Changed catalog batch translation so passthrough entries are saved directly
  to cache without calling the model.
- Changed single-entry catalog translation and forced retranslation to use the
  same passthrough behavior.
- Added invalid-translation detection for punctuation-only source text that was
  expanded into full dialogue.
- Added invalid-translation detection for unexpected leading visual markers
  such as `€`, `¥` and `￥`.
- Updated translation prompts to tell the model not to add those visual/currency
  symbols unless they exist in the source.
- Updated patch line wrapping so simple visual prefixes such as `\#` are copied
  to every wrapped continuation line.
- Disabled short-line reflow for message groups that already contain visual
  prefixes, preserving the original per-line formatting intent.
- Added regression tests for punctuation passthrough, contaminated cache cleanup,
  added visual markers and wrapped visual-prefix lines.

## Behavior Notes

- A cached translation for source text `...` that expands to a sentence is now
  considered contaminated.
- `Limpar cache contaminado` removes that bad cache entry for the active RPG
  Maker project scope.
- The next batch run saves `...` as `...` instead of translating it.
- Patch generation still does not call Ollama. It uses existing cache, skips
  missing/invalid entries, and writes skipped entries to the patch report.
- If the game currently has an older patch applied, restore the latest backup
  before applying a patch generated after these fixes. Otherwise, source
  validation can report mismatches against already-modified JSON.

## Local Findings

The local Demons Roots cache had this contaminated entry:

```txt
source_text: ...
translated_text: Eu não sei quem você é, Mas ele já me pediu para falar com você.
catalog refs: 544
```

With the new validation, this entry is now marked invalid and can be cleaned by
the existing cache-cleanup action.

The latest observed broken prologue line came from `Map111.json`. The translated
line kept `\#` only on the first generated line, so the continuation lost the
visual alignment. The patch wrapper now carries `\#` to every generated line.

## Recommended Next Manual Test

1. Restore the latest patch backup if an older patch is currently applied.
2. Run `Limpar cache contaminado`.
3. Run batch translation again for missing/invalid entries.
4. Generate a new patch.
5. Apply the new patch.
6. Check:
   - the repeated `...` dialogue no longer appears;
   - the `Map111` prologue centered text no longer drops alignment on wrapped
     lines;
   - battle skill descriptions remain translated and fit within two lines.

## Validation

Automated tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

Result:

```txt
185 passed
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
7 files already formatted
```

## Remaining Risks

- Some cached translations may still be linguistically poor while passing
  structural validation.
- Custom plugins may use visual escape codes with behavior that differs by
  window type.
- Long centered/cinematic text still needs manual inspection in-game because
  exact font metrics are game/theme dependent.
