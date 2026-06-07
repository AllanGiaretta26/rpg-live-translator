# Report V14

## Summary

This checkpoint is a code audit focused on optimization and bug handling rather
than new features. It removes repeated per-connection schema work from the SQLite
layer, collapses per-entry cache lookups into a single batched query, fixes the
catalog cache count so it no longer reports contaminated translations as hits,
fixes a false positive in the unexpected-visual-marker validation, and hardens
the RPG Maker runtime bridge HTTP handler. Reported issues from earlier docs were
re-checked against the actual code; several were confirmed already resolved or
were false alarms and are listed below so they are not re-investigated.

## Audit Scope

- Infrastructure layer: translation (Ollama), persistence (SQLite), capture,
  image, and RPG Maker bridge/parser.
- Application and domain layers: capture loop, translation pipeline, translation
  quality heuristics, patch service, runtime service, mode settings.
- Cross-check of CHANGELOG/reports V1–V13 against current code to confirm whether
  reported fixes are fully resolved.

## Completed

### Performance

- Changed `SQLiteConnectionManager` to initialize schema and migrations once per
  instance (guarded by a lock and a flag) instead of running the full
  `SCHEMA_SQL` script plus migration introspection on every `open()`. `PRAGMA
  foreign_keys = ON` stays per connection and `timeout` is now explicit.
- Added `TranslationCache.get_many_by_text`, a single batched lookup (chunked to
  stay under the SQLite bound-parameter limit) that returns a mapping keyed by
  the original input text.
- Changed `count_cached_catalog_entries` and `clear_contaminated_catalog_cache`
  to use the batched lookup instead of one `get_by_text` (and therefore one
  connection) per catalog entry.
- Changed `replace_project_entries` to insert catalog rows with a single
  `executemany` instead of one `INSERT` per entry.

### Correctness

- Fixed `count_cached_catalog_entries` so it validates each cached entry with
  `looks_like_invalid_translation` and counts only valid translations. The
  `Cache: X/Y` number now matches what the batch and patch flows treat as a real
  cache hit.
- Fixed `adds_unexpected_leading_visual_marker` so it only compares translated
  lines that have a matching source line. A valid translation that wraps one
  source line into several lines is no longer rejected just because an extra line
  has no source counterpart.

### Robustness

- Hardened the RPG Maker runtime bridge `do_POST` handler: it bounds the request
  body (`413` when it exceeds the limit, `400` for an invalid `Content-Length`),
  and separates client errors (`400`) from internal processing errors (`500`,
  logged with a stack trace) instead of mapping every failure to `400`.

### Tests

- Added regression tests for: one-time schema initialization, batched cache
  lookup (including scope isolation and batches above the chunk size), the
  contaminated-aware cache count, the large-batch catalog import, the
  visual-marker false positive, and the bridge `413`/`400`/`500` responses.

## Behavior Notes

- `get_many_by_text` keys the result by the original requested text and omits any
  text without a cached translation, so callers can look up by `entry.source_text`
  directly.
- The translation pipeline still never feeds prior lines back to the translator;
  the empty `context` is intentional (anti-leak design from V0.2.0) and is kept
  only as a regression guard. This was reviewed during the audit and left as is,
  with a clarifying comment.

## Discarded / Confirmed-Resolved Findings

These were raised during the audit but verified to be non-issues, to avoid
re-investigation:

- The RPG Maker escape regex does match `\C[1]`; `C` is a letter and is covered
  by `\\[A-Za-z]+`. No change needed.
- The `_replace_parameter` index check in the patch service is correct.
- `sqlite3.connect` already applies a default 5s busy timeout, so the previous
  code was not blocking indefinitely; the explicit timeout is a clarity change.
- Runtime MV/MZ does not delete an invalid cache entry explicitly, but the
  subsequent `save_translation` overwrites it, so it self-heals. Request
  versioning via `_latest_request_id` plus a lock is correct.

## Validation

Automated tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

Result:

```txt
197 passed
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
12 files already formatted
```

## Remaining Risks

- The repository was not fully `ruff format`-clean before this work; pre-existing
  formatting drift in untouched files was intentionally left alone to keep the
  diff focused.
- Batched cache lookups load matched rows into memory; for very large catalogs
  this trades many small queries for a few larger result sets, which is the
  intended improvement but increases peak memory per call.
- The bridge body limit (1 MiB) is fixed in code, not configurable from the UI.
