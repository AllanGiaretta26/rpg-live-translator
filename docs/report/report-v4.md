# Report V4

## Summary

This checkpoint fixes the remaining calibration mismatch and the most visible
translation consistency issue found during manual testing with the RPG Maker
game window.

## Completed

- Fixed region selector output so local drag coordinates are converted to
  physical capture coordinates with screen origin and DPI scale.
- Kept `X`, `Y`, `Largura` and `Altura` visible because they are the exact MSS
  capture region used by preview and runtime capture.
- Updated translation prompts to separate recent context from the current text
  to translate.
- Added defensive validation in the Ollama translator to reject responses that
  appear to include previous context lines.
- Added unit coverage for selector coordinate conversion, prompt boundaries and
  context-leak rejection.

## Validation

- Automated tests: `.venv\Scripts\python.exe -m pytest` passed with 74 tests.
- Manual validation: selected text preview matched the game dialogue region.
- Manual validation: translation stopped showing accumulated previous dialogue
  after the prompt and translator guard changes.

## Remaining Risks

- OCR and translation quality still depend on the local Ollama model behavior.
- The current capture region is screen-coordinate based, not bound to a moving
  game window.
- A packaged Windows build and production logging are still pending.
