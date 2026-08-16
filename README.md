# Garmin Training Dashboard

Personal Garmin training dashboard.

## Setup

Create a local `.env` file with the required Garmin credentials and runtime settings. Keep credential values out of source control.

```bash
uv sync
uv run pytest
```

Run the application and scheduler with Docker Compose:

```bash
docker compose up --build
```
