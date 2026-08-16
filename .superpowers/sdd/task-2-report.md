# Task 2 completion report

## Scope

Completed the existing Task 2 implementation from HEAD `38e77c6`. The partial
domain models, planning models, Garmin source port, storage ports, coach port,
fixtures, and domain tests were preserved. Cleanup was limited to Ruff/ty
issues: import organization, one unused import, and three unused ty
suppressions. No framework/provider/storage dependencies were added.

## TDD evidence

The inherited `tests/test_domain_models.py` contains the Task 2 validation
coverage for non-empty identities, non-negative durations, timezone-aware
timestamps, preserved timezone information, sleep ordering, recovery metric
identity/units, sync-family validation, immutable slotted records, planning
validation, protocol shape, and framework-independent ports.

Because this takeover only removed static-checker diagnostics and did not add
behavior, no new production behavior was introduced. The focused suite was
run before cleanup (`28 passed`) and again after cleanup (`28 passed`), showing
the cleanup preserved the existing behavior.

## Verification

All required commands completed successfully:

| Command | Result |
| --- | --- |
| `uv run pytest tests/test_domain_models.py -q` | 28 passed |
| `uv run pytest -q` | 33 passed |
| `uv run ruff format --check .` | 11 files already formatted |
| `uv run ruff check .` | All checks passed |
| `uv run ty check .` | All checks passed |

The required Docker workflow was unavailable in this environment. The exact
check `docker compose version` failed because the installed Docker CLI does
not provide the `compose` command. The uv-based checks above were run
successfully outside the sandbox using the existing uv cache.

During commit hooks, the direct `ty` hook was unavailable with the exact
failure `Executable \`ty\` not found`. The canonical required command
`uv run ty check .` passed, so the commit used `SKIP=ty` for that unavailable
hook only.

## Committed files

Only the Task 2 files and this report are intended for the commit:

- `.superpowers/sdd/task-2-report.md`
- `src/strava_dashboard/domain/models.py`
- `src/strava_dashboard/domain/plan_models.py`
- `src/strava_dashboard/ports/garmin.py`
- `src/strava_dashboard/ports/storage.py`
- `src/strava_dashboard/ports/coach.py`
- `tests/conftest.py`
- `tests/test_domain_models.py`

## Task 2 review-fix report

Fixed all three review findings on HEAD `d4c851d`:

1. Added strict non-negative integer validation for duration and count fields.
   Fractional values, `NaN`, negative values, and booleans are rejected rather
   than passing through numeric comparisons. Regression coverage includes
   activity/sleep durations and sync record counts.
2. Normalized mutable collection inputs to tuples in `__post_init__` across
   sync runs, summaries, dashboard/trend snapshots, training blocks, plan
   constraints, and plan proposals. Nested summary collections are normalized
   to tuples as well. Runtime regression coverage verifies tuple storage.
3. Added immutable `ActivityCursor`, `SleepCursor`, and `RecoveryCursor`
   value types with literal family ownership. Each storage port now accepts
   and returns only its matching cursor type, leaving the contract ready for
   independent SQLite-backed implementations. Regression coverage checks the
   protocol annotations.

## Fix verification

Commands run separately, in the requested order:

| Command | Result |
| --- | --- |
| `uv run pytest tests/test_domain_models.py -q` | 37 passed |
| `uv run pytest -q` | 42 passed |
| `uv run ruff format --check .` | 11 files already formatted |
| `uv run ruff check .` | All checks passed! |
| `uv run ty check .` | All checks passed! |

Docker was unavailable and was not used. No Docker wait or Compose check was
performed.

## Fix commit

Commit message: `fix: address Task 2 review findings`.
