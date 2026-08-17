# Task 4 implementation report

## Result

Implemented the transactional SQLite storage adapter behind the existing storage ports.

- Added SQLite connection setup with `sqlite3.Row`, foreign keys, WAL mode, bounded busy timeout, and schema versioning.
- Added idempotent activity, sleep, and recovery stores with UTC timestamp/date serialization, deterministic range reads, family-specific cursors, and atomic record-plus-cursor transactions.
- Added goal, validated-plan, workout, and sync-run persistence with typed Pydantic domain-model round trips.
- Added reusable contract coverage for cursor state, atomic upserts, idempotency, deterministic ordering, rollback, and independent data-family progress.
- No dataclasses were introduced; all persisted application data is represented by existing immutable Pydantic models.
- All new source files are below the repository’s 300-line limit.

## Verification

Commands were run from `/Users/sinan/Developer/strava-dashboard` using the existing `.venv` because direct `uv run` could not initialize the host uv cache in this sandbox.

| Command | Result |
| --- | --- |
| `.venv/bin/pytest tests/contracts/test_storage_contract.py tests/test_sqlite_stores.py -q` | 9 passed |
| `.venv/bin/pytest -q` | 86 passed |
| `.venv/bin/ruff format --check .` | passed; 32 files already formatted |
| `.venv/bin/ruff check .` | passed |
| `.venv/bin/ty check .` | passed |
| `docker compose config` | passed |
| `git diff --check` | passed |

## Environment limitation

`docker compose run --rm app uv run pytest tests/contracts/test_storage_contract.py tests/test_sqlite_stores.py -q` could not run because the Docker daemon is unavailable:

`failed to connect to the docker API at unix:///Users/sinan/.docker/run/docker.sock: ... connect: no such file or directory`

Direct `uv run` was also unavailable because uv could not initialize `/Users/sinan/.cache/uv` under the sandbox. Equivalent checks passed through the existing project virtualenv.

## Review fixes

- Replaced the single-shot schema initializer with a sequential migration runner.
- Added fresh/legacy upgrade and unsupported-future-version tests.
- Moved the SQLite storage factory into test fixtures so the contract assertions are backend-agnostic.
- Added parameterized sleep/recovery round-trip, ordering, and record-plus-cursor rollback coverage.

Final verification after review fixes:

```text
rtk uv run pytest -q
89 passed in 0.51s

rtk uv run ruff format --check .
32 files already formatted

rtk uv run ruff check .
All checks passed!

rtk uv run ty check .
All checks passed!
```
