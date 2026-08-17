# Application API reference

Current local FastAPI contract. This document covers browser delivery, dashboard queries, inspection, storage operations, response fields, and HTTP errors.

## Overview

FastAPI serves the dashboard and JSON API from the same origin. Compose publishes it at `http://127.0.0.1:8000`; there is no application-level authentication because the service is intended for local loopback access.

Responses use JSON unless a route serves HTML, CSS, or JavaScript. Dates use ISO `YYYY-MM-DD`. Datetimes are timezone-aware ISO 8601 values. Pydantic response models reject unexpected fields.

The API does not expose Garmin credentials, token state, raw MCP responses, arbitrary SQL, or arbitrary MCP tool calls.

## Route summary

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | React dashboard shell. |
| GET | `/static/app/{path}` | Hashed React production assets. |
| GET | `/docs` | FastAPI Swagger UI. |
| GET | `/redoc` | FastAPI ReDoc UI. |
| GET | `/openapi.json` | FastAPI-generated OpenAPI document. |
| GET | `/api/dashboard` | Current dashboard summary. |
| GET | `/api/dashboard/trends` | Training and health summaries over a requested range. |
| GET | `/api/dev/health` | Application inspection status. |
| GET | `/api/dev/garmin/health` | Garmin sync inspection status. |
| GET | `/api/dev/sync/runs` | Recent sync runs. |
| GET | `/api/dev/sync/runs/{run_id}` | One sync run. |
| GET | `/api/dev/storage/health` | Database, backup, disk, and freshness status. |
| POST | `/api/dev/storage/backup` | Create a compressed SQLite backup. |
| GET | `/api/dev/coach/health` | Coach-provider inspection status. |

## Common response and error behavior

Successful JSON responses use HTTP `200`. The backup endpoint also uses `200` when the operation result is `failed`; inspect its `status` and `failure_code` fields.

Common errors:

| Status | Body | Cause |
| --- | --- | --- |
| `404` | `{"detail":"sync run not found"}` | Requested sync run does not exist. |
| `405` | FastAPI method error | HTTP method is not supported by the route. |
| `422` | FastAPI validation body, or `{"detail":"start must be before end"}` | Invalid query/path input. |
| `503` | `{"detail":"storage unavailable"}` | Storage-layer exception reached the API handler. |
| `500` | `{"detail":"internal server error"}` | Unexpected exception; internal details are redacted. |

## Dashboard

### GET `/api/dashboard`

Return the current dashboard view. It uses the requested `today` date, or the server’s current date when omitted. The service summarizes the seven-day period ending on that date, includes up to ten recent activities, and loads the current goal and validated plan when present.

Query parameters:

| Name | Type | Required | Default | Rules |
| --- | --- | --- | --- | --- |
| `today` | date | No | Server current date | ISO `YYYY-MM-DD`. |

Example:

```bash
curl --fail 'http://127.0.0.1:8000/api/dashboard?today=2026-08-17'
```

Response shape:

```json
{
  "generated_at": "2026-08-17T08:00:00Z",
  "training": {
    "start": "2026-08-10",
    "end": "2026-08-18",
    "activity_count": 1,
    "duration_seconds": 3600,
    "distance_meters": 10000.0,
    "elevation_meters": 100.0,
    "sport_counts": [["running", 1]],
    "training_load": 60.0
  },
  "health": {
    "start": "2026-08-10",
    "end": "2026-08-18",
    "available": true,
    "average_sleep_seconds": 28800.0,
    "average_sleep_score": 82.0,
    "recovery_metrics": [["body_battery", 75.0, "percent"]]
  },
  "health_status": "available",
  "goal": {
    "goal_id": "goal-1",
    "description": "Run 10 km",
    "target_date": "2026-10-01"
  },
  "plan": null,
  "recent_activities": [
    {
      "external_id": "activity-1",
      "activity_type": "running",
      "started_at": "2026-08-17T08:00:00Z",
      "local_date": "2026-08-17",
      "duration_seconds": 3600,
      "distance_meters": 10000.0,
      "elevation_meters": 100.0,
      "average_heart_rate": 145.0,
      "max_heart_rate": 170.0,
      "calories": 500.0
    }
  ]
}
```

`health_status` is `available` or `missing`. Missing sleep/recovery values remain `null` or empty collections. `goal`, `plan`, and nullable activity metrics can be `null`.

### GET `/api/dashboard/trends`

Return training and health summaries grouped by a time bucket.

Query parameters:

| Name | Type | Required | Default | Rules |
| --- | --- | --- | --- | --- |
| `start` | date | Yes | — | ISO `YYYY-MM-DD`. |
| `end` | date | Yes | — | Must be after `start`. |
| `bucket` | `week`, `month`, `year` | No | `week` | Controls summary grouping. |

Example:

```bash
curl --fail \
  'http://127.0.0.1:8000/api/dashboard/trends?start=2026-07-01&end=2026-08-17&bucket=month'
```

Response shape:

```json
{
  "start": "2026-07-01",
  "end": "2026-08-17",
  "bucket": "month",
  "training": [],
  "health": []
}
```

Each item in `training` has the same fields as the `training` object from `/api/dashboard`. Each item in `health` has the same fields as the `health` object. Equal or inverted dates return `422` with `{"detail":"start must be before end"}`.

## Inspection and operations

### GET `/api/dev/health`

Return application inspection status.

```json
{
  "status": "ok",
  "detail": null
}
```

`status` is `ok`, `degraded`, or `unavailable`. `detail` is nullable and intended for an operator-safe status description.

### GET `/api/dev/garmin/health`

Return Garmin inspection state without exposing credentials or token details.

```json
{
  "status": "unavailable",
  "authenticated": false,
  "last_mcp_check": null,
  "last_sync": null
}
```

`last_sync`, when present, is a sync-run object with `run_id`, `started_at`, `ended_at`, and `stages`. The current SQLite inspection implementation reports stored sync history but does not perform a live MCP authentication check from this endpoint.

### GET `/api/dev/sync/runs`

Return recent sync runs, newest first.

Query parameters:

| Name | Type | Required | Default | Rules |
| --- | --- | --- | --- | --- |
| `limit` | integer | No | `20` | Must be between `1` and `100`. |

```bash
curl --fail 'http://127.0.0.1:8000/api/dev/sync/runs?limit=10'
```

Response:

```json
{
  "runs": [
    {
      "run_id": "sync-2026-08-17T08:00:00+00:00",
      "started_at": "2026-08-17T08:00:00Z",
      "ended_at": "2026-08-17T08:00:04Z",
      "stages": [
        {
          "data_family": "activities",
          "status": "succeeded",
          "record_count": 12,
          "error_code": null
        }
      ]
    }
  ]
}
```

`data_family` is `activities`, `sleep`, or `recovery`; stage `status` is `succeeded` or `failed`. Failed stages use an operator-safe `error_code`, normally `garmin_source_error` or `storage_error`.

### GET `/api/dev/sync/runs/{run_id}`

Return one sync run and nullable `failure_detail`:

```json
{
  "run": {
    "run_id": "sync-2026-08-17T08:00:00+00:00",
    "started_at": "2026-08-17T08:00:00Z",
    "ended_at": "2026-08-17T08:00:04Z",
    "stages": []
  },
  "failure_detail": null
}
```

Unknown run IDs return `404`.

### GET `/api/dev/storage/health`

Return database, backup, disk, and backup-freshness status.

```json
{
  "status": "degraded",
  "database": {
    "status": "ok",
    "detail": null,
    "size_bytes": 12345
  },
  "backup": {
    "status": "degraded",
    "detail": "backup_missing",
    "size_bytes": 0,
    "failure_code": null
  },
  "disk": {
    "status": "ok",
    "detail": null,
    "available_bytes": 1000000000
  },
  "freshness": {
    "status": "unavailable",
    "detail": "backup_missing",
    "latest_at": null,
    "age_seconds": null
  }
}
```

Each component status is `ok`, `degraded`, or `unavailable`. Overall status is the most severe component status. Health details include safe values such as `database_unavailable`, `backup_missing`, `backup_failed`, `backup_unavailable`, or `disk_unavailable`.

### POST `/api/dev/storage/backup`

Create one compressed SQLite backup. This endpoint accepts no request body and does not accept a backup path or arbitrary identifier.

```bash
curl --fail --request POST http://127.0.0.1:8000/api/dev/storage/backup
```

Success:

```json
{
  "status": "succeeded",
  "backup_id": "dashboard-20260817T080000Z-12345678.sqlite3.gz",
  "failure_code": null
}
```

Failure is returned as a `200` operation result:

```json
{
  "status": "failed",
  "backup_id": null,
  "failure_code": "backup_failed"
}
```

Use the returned `backup_id` with the documented stop/restore procedure in the [README](../../README.md). Do not treat it as a filesystem path.

### GET `/api/dev/coach/health`

Return coach-provider availability without exposing prompts or provider credentials.

```json
{
  "status": "unavailable",
  "last_call_status": null,
  "schema_validation_failures": 0
}
```

## Frontend delivery

`GET /` serves the Vite-generated `index.html` from `api/static/app`. Its hashed JavaScript and CSS load from `/static/app/assets/`; the React application fetches same-origin dashboard and trend APIs. Docker creates these files from `frontend/` during the application build.

FastAPI’s built-in `/docs`, `/redoc`, and `/openapi.json` routes are available for interactive inspection. Keep access loopback-bound through Compose when running locally.

## Mapping to stories

| Story | Primary endpoint | Operation |
| --- | --- | --- |
| [Dashboard and trends](../stories/dashboard-and-trends.md) | `GET /api/dashboard` | Read current training, health, goal, plan, and recent-activity summaries. |
| [Dashboard and trends](../stories/dashboard-and-trends.md) | `GET /api/dashboard/trends` | Read grouped training and health summaries. |
| [Garmin synchronization](../stories/garmin-sync.md) | `GET /api/dev/garmin/health` | Inspect stored Garmin/sync state without token details. |
| [Operations and backups](../stories/operations-and-backups.md) | `GET /api/dev/health` | Inspect application status. |
| [Operations and backups](../stories/operations-and-backups.md) | `GET /api/dev/sync/runs` | Inspect recent sync outcomes. |
| [Operations and backups](../stories/operations-and-backups.md) | `GET /api/dev/storage/health` | Inspect database, backup, disk, and freshness state. |
| [Operations and backups](../stories/operations-and-backups.md) | `POST /api/dev/storage/backup` | Create a generated compressed SQLite backup. |
