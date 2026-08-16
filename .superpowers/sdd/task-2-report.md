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
   sync runs, summaries, dashboard/trend snapshots, training blocks, and plan
   constraints and plan proposals. Nested summary collections are normalized
   to tuples as well. Runtime regression coverage verifies tuple storage.
3. Added immutable `ActivityCursor`, `SleepCursor`, and `RecoveryCursor` value
   types with literal family ownership. Each storage port now accepts and
   returns only its matching cursor type, leaving the contract ready for
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

## Task 2 review equality fix

Fixed the remaining Task 2 review finding on HEAD `b083209`: `SyncRun` now
rejects `ended_at` equal to `started_at`, as well as earlier timestamps. Added
the equality regression to `tests/test_domain_models.py`.

### Exact verification commands and results

```text
$ uv run pytest tests/test_domain_models.py -q
..............................................                           [100%]
46 passed in 0.07s

$ uv run pytest -q
.......................................................                  [100%]
55 passed in 0.09s

$ uv run ruff check .
All checks passed!

$ uv run ty check .
All checks passed!
```

---

# Task 2 Pydantic migration report

## Scope

Converted domain and plan records from dataclasses to Pydantic v2 models. Added shared immutable `DomainModel` configuration with `frozen=True` and `extra="forbid"`, strict non-negative integer validation, timezone-aware datetime validation, ordering validators, literal family-specific cursors, and tuple-typed nested collections. Preserved public model names and port interfaces. No Docker commands were run, per request.

Existing migration tests were preserved and completed with the model-specific type-check suppressions required for Pydantic runtime list-to-tuple normalization.

## Verification

All commands were run from `/Users/sinan/Developer/strava-dashboard` on 2026-08-17.

### Focused migration tests

Command:

```text
uv run pytest tests/test_domain_models.py tests/test_domain_ports.py tests/test_no_dataclasses.py -q
```

Result:

```text
..................................................                       [100%]
50 passed in 0.10s
```

### Full test suite

Command:

```text
uv run pytest -q
```

Result:

```text
.......................................................                  [100%]
55 passed in 0.09s
```

### Ruff format

Command:

```text
uv run ruff format --check .
```

Result:

```text
13 files already formatted
```

### Ruff lint

Command:

```text
uv run ruff check .
```

Result:

```text
All checks passed!
```

### Ty type check

Command:

```text
uv run ty check .
```

Result:

```text
All checks passed!
```

## Concerns

- `uv` required access to its existing cache outside the default sandbox; no dependency installation or Docker execution was performed.
- Pydantic accepts list inputs and materializes tuple fields at validation time. Existing tests retain list-shaped constructor inputs and use narrow `ty` ignores for that runtime normalization boundary.
