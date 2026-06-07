# Report V15

## Summary

This checkpoint fixes three in-game problems with the RPG Maker MV/MZ translation
patch: dialogue lines breaking in awkward places (after a comma or period), text
rendering larger than the message box / running off-screen, and special escape
codes leaking across lines. The message wrapper was rewritten to fill each line
up to the box width using an escape-code-aware width measurement, and the line
width limits became configurable per game.

## Root Causes

- **Duplicated font-size codes.** The previous wrapper re-added the leading
  visual prefix to every wrapped line, and the prefix set included `\{`/`\}`
  (font size, cumulative within a message). A single `\{Hello ...` became
  `\{line1`/`\{line2`/`\{line3`, so the font grew line by line and the code
  "leaked" / duplicated.
- **Width measured in raw characters.** Wrapping counted escape codes such as
  `\C[3]`, `\N[1]`, `\V[2]`, `\I[64]`, `\{` as visible characters. Zero-width
  control codes wrapped too early, and `\N`/`\V`/`\P` (which expand to longer text
  at runtime) were underestimated, causing overflow.
- **Sentence-aware reflow.** A polish pass deliberately pushed the text after a
  `.`/`!`/`?` onto the next line, and the non-collapsing path kept the model's own
  line breaks (including after commas).

## Completed

- Added `_visible_width`: measures rendered width, excluding zero-width codes
  (`\C`, `\I`, `\{`, `\}`, waits) and estimating dynamic codes (`\N`, `\P`, `\V`)
  with a conservative fixed width.
- Added `_fill_wrap` / `_greedy_wrap_words`: collapse the model's line breaks and
  greedily fill each line up to the visible width. Long single-line translations
  are always split into multiple lines, so they no longer run off-screen.
- Restricted the repeated per-line prefix to `\#` only. Stateful codes such as
  `\{`/`\}` now stay inline and appear once.
- Removed the sentence-tail / dangling-word reflow that caused breaks after a
  comma or period.
- Applied the escape-aware wrapper to messages, scrolling text and database
  descriptions.
- Made the patch line-width limits configurable: `AppSettings` gains
  `patch_message_line_limit`, `patch_message_face_line_limit` and
  `patch_description_line_limit` (env prefix `LIVE_TRANSLATOR_`), threaded through
  `ModeSettingsService` into `RpgMakerPatchService`.
- Added/updated regression tests for: `\{` not duplicated, `\#` still repeated,
  `_visible_width`, color codes not splitting a fitting line early, long single
  lines wrapping into multiple lines, the configurable limit, and the new
  fill-to-width output for existing message/scenario tests.

## Behavior Notes

- Message boxes are reflowed (the model's own line breaks are discarded and the
  text is refilled). Short multi-line translations may merge onto fewer lines when
  they fit; long ones are always split to fit the width.
- The previous off-screen single-line problem does not return: `_fill_wrap` always
  wraps to the configured width.
- Scrolling text keeps its intentional line breaks; each line is wrapped
  independently with the escape-aware width.

## Validation

Automated tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

Result:

```txt
203 passed
```

Lint:

```powershell
.venv\Scripts\python.exe -m ruff check src/live_translator tests
```

Result:

```txt
All checks passed!
```

## Recommended Next Manual Test

1. Restore the latest patch backup if an older patch is currently applied.
2. Generate a new patch and apply it.
3. In-game, check:
   - long dialogue wraps into multiple lines and stays inside the box (never one
     off-screen line);
   - no line break right after a comma or period;
   - the font does not grow line by line (`\{` is not duplicated);
   - no leftover/duplicated escape codes in the dialogue.
4. If a specific game's box is narrower/wider, tune
   `LIVE_TRANSLATOR_PATCH_MESSAGE_LINE_LIMIT` (and the face/description limits)
   and regenerate the patch.

## Remaining Risks / Limitations

- The width estimate for `\N`/`\P`/`\V` is heuristic; the real runtime length is
  unknown, so the estimate is conservative to avoid overflow.
- Text genuinely enlarged by `\{...\}` occupies more pixels per character; the fix
  stops duplicating the code but does not model the larger glyph precisely.
- The ideal width still depends on the game's font/theme, which is why the limits
  are configurable.
