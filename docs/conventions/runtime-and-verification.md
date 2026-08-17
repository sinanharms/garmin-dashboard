# Convention: runtime and verification

## Configuration

Runtime settings live in `strava_dashboard.config.Settings` with explicit uppercase environment aliases. Required settings are `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `GARMIN_TOKEN_DIR`, `DATABASE_PATH`, `BACKUP_DIR`, `GARMIN_MCP_COMMAND`, `MCP_TIMEOUT_SECONDS`, `BACKUP_RETENTION_COUNT`, and `BACKUP_RETENTION_DAYS`.

## Docker-first workflow

Use Compose as the primary workflow:

```bash
docker compose config --quiet
docker compose up --build
docker compose run --rm app bash scripts/garmin-auth.sh
docker compose run --rm scheduler uv run python -m strava_dashboard.worker
```

The runtime image copies application sources but not `tests/`. Containerized test runs therefore mount the repository test directory read-only:

```bash
docker compose run --rm \
  -v "$PWD/tests:/app/tests:ro" \
  app uv run pytest -q
```

Focused config tests use the same mount. Run Ruff through the app image with `docker compose run --rm app uv run ruff check .`.

Build frontend checks and the containerized production browser smoke with:

```bash
docker build --target frontend-checks .
docker build --target browser-smoke -t garmin-dashboard-browser-smoke .
docker compose up -d --build app
docker run --rm --add-host host.docker.internal:host-gateway \
  -e BASE_URL=http://host.docker.internal:8000 \
  garmin-dashboard-browser-smoke
```

The Playwright smoke must execute the built JS through FastAPI and cover desktop, tablet, and mobile projects. An endpoint-only shell check is not browser coverage.

## Verification baseline

Before handoff, validate Compose, run focused configuration tests, run the full relevant test suite, run Ruff, and inspect `git diff --check`. Keep source files below 300 lines and preserve unrelated working-tree changes.

Applies to every current story, including the implemented [React dashboard](../stories/react-dashboard.md).
