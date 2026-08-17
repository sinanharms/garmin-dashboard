# Garmin Training Dashboard

Personal, single-user Garmin training dashboard. It imports activities, sleep, and recovery data through the Garmin MCP stdio server, stores normalized records in SQLite, and serves a local FastAPI dashboard.

The browser UI is a React build served by FastAPI at `/`; its Vite assets are served at `/static/app/`. Docker builds the frontend in a Node stage and copies its production output into the final application image. Browser API requests remain same-origin under `/api`.

## Quick start

Prerequisites:

- Docker with Docker Compose.
- Garmin account credentials available through a local secret manager or editor.
- Local access to loopback port `8000`.

Create local configuration. Never commit or print `.env`.

```bash
cp .env.example .env
```

Set `GARMIN_EMAIL` and `GARMIN_PASSWORD` in `.env`, then validate the Compose file without printing its merged environment:

```bash
docker compose config --quiet
```

Bootstrap Garmin authentication once. Complete MFA interactively if Garmin requests it:

```bash
docker compose run --rm app bash scripts/garmin-auth.sh
```

Start the dashboard and one scheduler run:

```bash
docker compose up --build
```

Open <http://127.0.0.1:8000>. The `app` service stays running. The `scheduler` service runs one sync command and exits; start it again when another explicit sync is needed.

## Configuration

`strava_dashboard.config.Settings` requires every setting below. Compose supplies the container paths and operational defaults; `.env` should provide the Garmin credentials.

| Variable | Purpose | Required |
| --- | --- | --- |
| `GARMIN_EMAIL` | Garmin account email. | Yes |
| `GARMIN_PASSWORD` | Garmin account password. Loaded as a secret value. | Yes |
| `GARMIN_TOKEN_DIR` | Persisted Garmin authentication state directory. | Yes |
| `DATABASE_PATH` | SQLite database file. | Yes |
| `BACKUP_DIR` | Directory for compressed SQLite backups. | Yes |
| `GARMIN_MCP_COMMAND` | MCP executable started over stdio. | Yes |
| `MCP_TIMEOUT_SECONDS` | Maximum wait for one MCP tool call. | Yes |
| `BACKUP_RETENTION_COUNT` | Maximum number of generated backups retained. | Yes |
| `BACKUP_RETENTION_DAYS` | Maximum age of generated backups. | Yes |

Default container paths are `/root/.garminconnect`, `/var/lib/dashboard/dashboard.sqlite3`, and `/var/lib/dashboard/backups`. The Compose file sets the MCP command to `garmin-mcp`, a 30-second MCP timeout, seven retained backups, and 31 retained days.

## Operations

Check application, Garmin inspection, and storage health without exposing tokens or raw MCP responses:

```bash
curl --fail http://127.0.0.1:8000/api/dev/health
curl --fail http://127.0.0.1:8000/api/dev/garmin/health
curl --fail http://127.0.0.1:8000/api/dev/storage/health
```

Run a manual sync with the scheduler image and environment:

```bash
docker compose run --rm scheduler uv run python -m garmin_dashboard.worker
```

Create a compressed SQLite backup through the local operations endpoint:

```bash
curl --fail --request POST http://127.0.0.1:8000/api/dev/storage/backup
```

Backups use generated identifiers ending in `.sqlite3.gz`. Stop both services before restoring one. Pass only the generated filename, not a filesystem path:

```bash
docker compose stop app scheduler
docker compose run --rm app uv run python -c '
from datetime import UTC, datetime

from garmin_dashboard.adapters.sqlite.backup import SQLiteBackupStore
from garmin_dashboard.adapters.sqlite.connection import open_connection
from garmin_dashboard.config import Settings

settings = Settings()
connection = open_connection(settings.database_path)
store = SQLiteBackupStore(
    connection,
    settings.backup_dir,
    settings.backup_retention_count,
    settings.backup_retention_days,
    lambda: datetime.now(UTC),
)
store.restore("BACKUP_ID.sqlite3.gz")
connection.close()
'
docker compose up -d app scheduler
```

Protect the `garmin_tokens` volume and `.env`. Do not copy token state into the repository or expose the MCP server over HTTP.

## Testing and linting

The runtime image copies application sources, not the repository test suite. Mount tests read-only for containerized development checks:

```bash
docker compose config --quiet
docker compose run --rm \
  -v "$PWD/tests:/app/tests:ro" \
  app uv run pytest tests/test_config.py -q
docker compose run --rm \
  -v "$PWD/tests:/app/tests:ro" \
  app uv run pytest -q
docker compose run --rm app uv run ruff check .
docker build --target frontend-checks .
docker build --target browser-smoke -t garmin-dashboard-browser-smoke .
docker compose up -d --build app
docker run --rm --add-host host.docker.internal:host-gateway \
  -e BASE_URL=http://host.docker.internal:8000 \
  garmin-dashboard-browser-smoke
```

## Project structure

```text
src/strava_dashboard/
├── domain/                  # Immutable business models
├── ports/                   # Garmin, storage, coach, and backup boundaries
├── application/             # Sync, metrics, dashboard, planning, operations
├── adapters/
│   ├── garmin_mcp/          # MCP stdio session, tool mapping, data adapter
│   └── sqlite/               # SQLite schema, stores, connection, backups
├── api/                     # FastAPI app, routes, built frontend assets
├── config.py                # Pydantic Settings and environment aliases
└── worker.py                # One-shot sync entrypoint
frontend/                    # React UI, component tests, and production browser smoke
```

Additional references:

- [Documentation index](docs/INDEX.md): canonical navigation for architecture, stories, APIs, conventions, and decisions.
- [Architecture](docs/architecture/overview.md): runtime components, data flow, persistence, and deployment.
- [API reference](docs/api/application.md): HTTP routes, query parameters, response fields, and errors.
- [Open questions](docs/decisions/open-questions.md): unresolved differences between source and approved designs.
- [Historical source](docs/archive/): original specifications and implementation plans.

## Contributing

Keep domain and application boundaries explicit, use Pydantic v2 models for application data, preserve environment aliases, and keep source files below 300 lines. Run Compose validation, focused tests, the full test suite, and Ruff before submitting changes. Never include credentials, token state, raw MCP responses, or local database files in a change.
