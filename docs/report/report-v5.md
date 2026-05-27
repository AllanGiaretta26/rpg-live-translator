# Report V5

## Summary

This checkpoint closes the current MVP scope for the external capture workflow.
Manual testing showed that disabling recent-context prompts resolved the visible
context contamination issue and improved perceived latency. The app now exposes
basic timing diagnostics in the status panel so OCR, translation and total frame
time can be compared during real gameplay.

## Completed

- Disabled recent translation context by default to avoid previous dialogue
  leaking into the current output.
- Shortened translation prompts when no context is sent to the model.
- Added pipeline timing diagnostics for total frame time, OCR time, translation
  time and the path taken by the frame.
- Displayed the timing summary in the `Executar` status panel.
- Updated documentation to mark the capture-based MVP as functionally complete.
- Documented RPG Maker MV/MZ file-reading support as the next major evolution.

## Manual Findings

- Context pollution appears resolved after context was disabled.
- Latency improved enough for the current MVP workflow.
- OCR and translation each stayed around or below 1.50 seconds in testing.
- End-to-end frame time was observed around 3.40 seconds in cache-miss cases.
- The current status line is useful as-is; more granular timing would likely
  make the panel noisy unless gated behind a future debug mode.

## Validation

Automated tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

Result:

```txt
75 passed
```

Style validation was attempted with:

```powershell
.venv\Scripts\python.exe -m ruff check .
```

Result:

```txt
No module named ruff
```

## MVP Status

The MVP criteria in `BRIEFING.md` are met for the screen-capture workflow:

- selectable text region;
- region capture;
- local OCR/vision and translation through Ollama;
- translated overlay;
- image and text cache;
- pause/resume controls;
- basic pipeline status and timing diagnostics.

## Next Phase: RPG Maker MV/MZ Support

The next major phase should add read-only RPG Maker MV/MZ support:

- detect `www/data` or `data` folders;
- parse `MapXXX.json` and `CommonEvents.json`;
- extract dialogue, choices and scrolling text commands;
- preserve text origin for debugging and cache traceability;
- pre-cache known translations;
- use OCR/vision as runtime matching and fallback instead of the only source of
  truth.

This should improve latency, consistency and translation quality without
modifying game files.

## Remaining Risks

- The app is still not packaged as a Windows executable.
- Capture is still based on absolute screen coordinates, not a moving game
  window.
- OCR/vision remains necessary for images, plugin-generated text and unknown
  runtime strings.
- Production logging and exportable diagnostics are still pending.
