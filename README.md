# Garmin Training Dashboard

Personal Garmin training dashboard.

## Setup

Create the local environment file, then replace the placeholder credentials with values held in your local secret manager or editor. Never print or commit `.env`.

```bash
cp .env.example .env
```

Required environment variable names:

- `GARMIN_EMAIL`
- `GARMIN_PASSWORD`
- `GARMIN_TOKEN_DIR`
- `DATABASE_PATH`
- `BACKUP_DIR`
- `GARMIN_MCP_COMMAND`
- `MCP_TIMEOUT_SECONDS`
- `BACKUP_RETENTION_COUNT`
- `BACKUP_RETENTION_DAYS`

```bash
docker compose config
docker compose up --build
```

Bootstrap Garmin authentication once, with MFA if Garmin requests it. Run the script through the `app` service so it writes into the same protected named token volume used by the application:

```bash
docker compose run --rm app bash scripts/garmin-auth.sh
```

The scheduler never runs the authentication script. It uses the persisted token state for scheduled MCP pulls.

## Operations

Check Garmin authentication and the latest sync without exposing tokens:

```bash
curl --fail http://127.0.0.1:8000/api/dev/garmin/health
curl --fail http://127.0.0.1:8000/api/dev/storage/health
```

Trigger a manual sync with the same container image and environment as the scheduler:

```bash
docker compose run --rm scheduler uv run python -m strava_dashboard.worker
```

Backups are compressed SQLite files in the persistent dashboard volume. To restore one, stop the application and scheduler first, then run the adapter against the backup identifier (the filename, not a path):

```bash
docker compose stop app scheduler
docker compose run --rm app uv run python -c '
from strava_dashboard.adapters.sqlite.backup import SQLiteBackupStore
from strava_dashboard.adapters.sqlite.connection import open_connection
from strava_dashboard.config import Settings
from datetime import UTC, datetime

settings = Settings()
connection = open_connection(settings.database_path)
store = SQLiteBackupStore(connection, settings.backup_dir, settings.backup_retention_count, settings.backup_retention_days, lambda: datetime.now(UTC))
store.restore("BACKUP_ID.sqlite3.gz")
connection.close()
'
docker compose up -d app scheduler
```

Protect the `garmin_tokens` volume and the `.env` file. Do not copy token state into the repository or expose the MCP server over HTTP.
