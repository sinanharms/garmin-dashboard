# Repository Guidance

Use Docker Compose as the primary project workflow. The `app` and `scheduler` services share the application image and persistent named volumes for dashboard data and Garmin token state.

Create `.env` locally with Garmin credentials before running Compose. Never commit or print credential values.

Run focused checks with `docker compose run --rm app uv run pytest tests/test_config.py -q`, then run the full relevant test suite with `docker compose run --rm app uv run pytest -q`. Validate the Compose definition with `docker compose config`.

Keep runtime configuration in `strava_dashboard.config.Settings`, preserve explicit environment aliases, and keep source files under 300 lines.

Use Pydantic v2 `BaseModel` for all domain, port, application, API, and adapter data models. Configure immutable models with `ConfigDict(frozen=True)` and use tuple-typed collections where runtime immutability is required. Do not introduce dataclasses for application data.

Operational workflow is Docker-first. Use `docker compose config` before startup, `docker compose up --build` for the app, `docker compose run --rm app bash scripts/garmin-auth.sh` for one-time Garmin MFA bootstrap, and `docker compose run --rm scheduler uv run python -m strava_dashboard.worker` for an explicit manual sync. Check `/api/dev/garmin/health` and `/api/dev/storage/health` through the loopback-bound app port. Stop both services before restoring a compressed SQLite backup. Never print `.env`, Garmin credentials, token-volume contents, MCP responses, or backup paths containing secrets.

## Documentation navigation

Start documentation work from [docs/INDEX.md](docs/INDEX.md). Before implementation, read the relevant story in `docs/stories/`, its linked architecture and convention documents, and [docs/decisions/open-questions.md](docs/decisions/open-questions.md).

Canonical documentation lives outside `docs/archive/`; archived specifications and plans preserve historical intent but do not override current source behavior. If a raw API or schema reference is added under `docs/api/specs/`, check its size before loading and ask before reading files around 200KB or larger. Record newly discovered gaps in `docs/decisions/open-questions.md` instead of guessing.
