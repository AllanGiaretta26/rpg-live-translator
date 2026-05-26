# Overlay, Region Selection, and Translation Consistency Design

## Goal

Fix the current calibration pain points without changing the application architecture: overlay sizing should be mouse-driven, region selection must work on the correct screen, the app should warn when the overlay overlaps the OCR region, and translation prompts/diagnostics should reduce partial translation behavior.

## Context

The app has separate responsibilities already in place:

- UI renders the settings window, overlay, and visual region selector.
- Application services orchestrate capture, preview, pipeline, profile settings, and overlay settings.
- Infrastructure owns screen capture, image utilities, persistence, and Ollama integration.

The overlay is output only. It should not be placed over the source text region unless the user accepts the risk that OCR may read translated text instead of game text.

## Scope

This change will:

- Improve overlay edit mode so users can move and resize it with the mouse, including edges and corners.
- Keep overlay numeric fields synchronized with mouse movement and resizing.
- Fix the region selector so it opens as a usable full-screen selection layer on the target screen.
- Keep the capture preview focused on showing exactly what will be sent to OCR.
- Add an in-app warning when the overlay rectangle intersects the selected text region.
- Strengthen prompt wording and response handling so the translator is asked to translate the complete extracted text.
- Improve diagnostics for empty OCR, empty translation, cache hits, and completed translation.

This change will not:

- Hide the overlay during capture.
- Redesign the whole settings UI.
- Add new concrete infrastructure dependencies to UI.
- Move business rules into UI.
- Implement a new OCR or translation provider.

## User Experience

The intended setup flow is:

1. Select the text area used by the game.
2. Check the preview to verify the source text area.
3. Adjust the overlay somewhere outside that source region.
4. Start or resume translation.

If the overlay overlaps the selected source region, the app displays a warning:

`O overlay esta sobre a area capturada. Isso pode fazer o OCR ler a traducao em vez do texto do jogo.`

The warning does not block saving. It explains the likely cause of inconsistent translations.

## Architecture

UI remains thin:

- `ui/main_window.py` displays controls, preview, and overlap warnings.
- `ui/overlay_window.py` handles mouse interaction for the overlay window only.
- `ui/region_selector_window.py` handles visual region selection only.

Application remains the orchestration layer:

- Existing services continue to own profile, overlay, preview, and pipeline state.
- Rectangle overlap calculation can live in a small application/domain-safe helper because it is pure geometry and has no UI dependency.

Infrastructure remains behind contracts:

- `MSSScreenCapture` continues to implement `ScreenCapture`.
- Ollama prompt and parsing changes remain under `infrastructure/translation`.

## Error Handling and Diagnostics

The pipeline should distinguish the main user-visible states:

- no visual change;
- image cache hit;
- text cache hit;
- OCR returned no usable text;
- translation returned no usable text;
- translation completed;
- unexpected error.

When source text is non-empty but translated text is empty, the overlay should not be updated with blank text. The diagnostic should explain the failed translation result.

## Testing

Add or update unit tests for:

- rectangle overlap detection;
- overlay placement synchronization behavior where testable without launching the full app;
- region normalization and selector screen geometry helpers;
- prompt text requiring complete translation;
- translator rejecting or diagnosing empty translated text for non-empty source text;
- pipeline diagnostics for empty translation.

Manual validation after implementation:

- run `python -m pytest`;
- launch the app with `pythonw -m live_translator.app.main`;
- select a text area and verify preview;
- move overlay outside and inside the text area and confirm warning behavior;
- translate a multi-line dialogue and confirm the result does not translate only a small fragment when OCR source text is complete.
