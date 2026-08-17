# Task 8 implementation report

Implemented the read-only dashboard query service, FastAPI application boundary, inspection API, and provisional dashboard shell.

## Behaviors covered

- `DashboardService` composes activity, sleep, recovery, goal, and plan ports without importing SQL, MCP, or FastAPI types.
- Current dashboard reads expose training load, recent activities, goals, plans, sleep/recovery summaries, and explicit `available`/`missing` health status.
- Trend reads use typed date and bucket parameters and return the existing immutable Pydantic trend models.
- Six predefined inspection endpoints expose typed, redacted health, Garmin, sync, storage, and coach views.
- Routes are read-only; no arbitrary SQL or MCP pass-through endpoints exist.
- Storage failures and unexpected route errors return stable redacted messages rather than raw exception text.
- Production wiring is isolated in the FastAPI lifespan composition root; test fakes are constructor-injected.
- The homepage, CSS, and dashboard script are isolated under `api/templates` and `api/static` for later dashboard redesign.
- The dashboard trend route rejects equal or inverted date ranges with a stable 422 response before calling the service.
- The provisional shell renders weekly plan/workout details and separate sleep/recovery details, including explicit unavailable states.
- All API/application data models use frozen, `extra="forbid"` Pydantic models; no dataclasses were introduced.

## TDD and verification

- Review-fix regression tests: `uv run pytest tests/test_api.py -q` — 9 passed.
- Full suite: `uv run pytest -q` — 128 passed.
- Ruff check — passed.
- Ruff format check — passed.
- `uv run ty check .` — passed.
- `docker compose config --quiet` — passed.
- Docker-focused test was attempted but could not run because the Docker daemon is unavailable.

All Task 8 Python source and test files remain below 300 lines.
