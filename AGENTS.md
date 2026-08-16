# Repository Guidance

Use Docker Compose as the primary project workflow. The `app` and `scheduler` services share the application image and persistent named volumes for dashboard data and Garmin token state.

Create `.env` locally with Garmin credentials before running Compose. Never commit or print credential values.

Run focused checks with `docker compose run --rm app uv run pytest tests/test_config.py -q`, then run the full relevant test suite with `docker compose run --rm app uv run pytest -q`. Validate the Compose definition with `docker compose config`.

Keep runtime configuration in `strava_dashboard.config.Settings`, preserve explicit environment aliases, and keep source files under 300 lines.
