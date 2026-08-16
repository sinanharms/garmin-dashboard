# Garmin Training Dashboard

Personal Garmin training dashboard.

## Setup

Create a local `.env` file with the required Garmin credentials and runtime settings. Keep credential values out of source control.

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
uv sync
uv run pytest
```

Run the application and scheduler with Docker Compose:

```bash
docker compose up --build
```
