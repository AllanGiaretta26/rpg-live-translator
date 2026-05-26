# Report V3

## Summary

This checkpoint improves calibration reliability. The overlay is treated as translated output only, the source text region is easier to select, and the app warns when overlay placement can contaminate OCR.

## Completed

- Added rectangle overlap detection for text region and overlay placement.
- Added in-app overlap warning when overlay intersects the captured text area.
- Improved overlay mouse resizing across edges and corners.
- Fixed region selector screen selection by using the monitor under the cursor.
- Strengthened translation prompts and blank-result validation.
- Added clearer diagnostics for translation failure.

## Validation

- Automated tests: `.venv\Scripts\python.exe -m pytest` passed with 68 tests.
- Architecture import scan: no sensitive imports found in `domain` or `application`.
- Manual checks still needed: region selection, capture preview, overlay resize, overlap warning, and multi-line dialogue translation against the real game.

## Remaining Risks

- Translation completeness still depends on OCR quality and model behavior.
- Window-relative capture remains a future improvement.
- Manual GUI validation is still required on the target monitor/game setup.
- Packaging and production logging are still pending.
