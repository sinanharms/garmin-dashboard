# Architecture

## Current system

Garmin Training Dashboard is a local, single-user Python service. Docker Compose runs one FastAPI process and one one-shot sync worker from the same image. Both services share SQLite data and Garmin authentication state through named volumes.

```text
Garmin account
    │
    ▼
garmin-mcp-auth ──► garmin_tokens volume
                         │
                         ▼
scheduler ── stdio ──► garmin-mcp ──► Garmin MCP adapter
                                          │
                                          ▼
                                   SyncService
                                          │
                                          ▼
                              SQLite stores + sync cursors
                                          │
                                          ▼
app ──► DashboardService / OperationsService ──► FastAPI API
  │                                                   │
  └──────────── static HTML + JavaScript ◄────────────┘
```

The browser never connects directly to Garmin, MCP, SQLite, credentials, or token state.

## Repository boundaries

| Boundary | Location | Responsibility |
| --- | --- | --- |
| Domain | `src/strava_dashboard/domain/` | Immutable Pydantic models for activities, sleep, recovery, sync, summaries, goals, and plans. |
| Ports | `src/strava_dashboard/ports/` | Stable protocols and storage/source errors used by application services. |
| Application | `src/strava_dashboard/application/` | Sync workflow, metric calculation, dashboard queries, planning validation, and operational health/backup behavior. |
| Garmin adapter | `src/strava_dashboard/adapters/garmin_mcp/` | Starts the MCP subprocess over stdio, calls Garmin tools, validates payload shape, maps data into domain models, and closes the session. |
| SQLite adapters | `src/strava_dashboard/adapters/sqlite/` | Opens and migrates SQLite, stores normalized records, persists sync cursors/runs, and creates/restores compressed backups. |
| HTTP delivery | `src/strava_dashboard/api/` | Builds production services, exposes FastAPI routes, serves the static dashboard, and redacts storage/unexpected errors. |
| Worker delivery | `src/strava_dashboard/worker.py` | Builds sync dependencies and executes one 30-day lookback sync run. |

Domain records and application/API response models use Pydantic v2. Models are frozen and reject unexpected fields. Collections crossing runtime boundaries use tuples where immutability matters.

## Runtime composition

`api.app.build_production_services()` is the production composition root. It opens one SQLite connection, creates SQLite stores, then injects them into `DashboardService`, `SQLiteInspectionService`, and `OperationsService`. FastAPI owns that service bundle for the application lifespan and closes the connection during shutdown.

The `worker` composition root creates a `StdioMcpSessionFactory`, `GarminMcpAdapter`, SQLite activity/sleep/recovery stores, and `SyncService`. The worker opens a connection for one run and closes it afterward. It returns exit code `0` only when all three data-family stages succeed.

Tests inject fake dashboard, inspection, and operations services through `create_app()`. This keeps HTTP tests independent of Garmin credentials and live MCP state.

## Sync data flow

1. `worker.py` creates a timezone-aware window ending at the current time and beginning 30 days earlier.
2. `SyncService` runs independent activities, sleep, and recovery stages.
3. Each stage reads its SQLite cursor and narrows the request window when prior data exists.
4. `GarminMcpAdapter` opens one MCP stdio session, calls the relevant Garmin tools, maps validated payloads, and closes the session.
5. Each SQLite store upserts normalized records and advances its cursor to the sync window end.
6. The run is saved in `sync_runs` with one `SyncStageResult` per data family.
7. Garmin or storage failures become stage-level failure codes (`garmin_source_error` or `storage_error`); the run remains inspectable through `/api/dev/sync/runs`.

The adapter skips explicit “no sleep summary” and “no HRV data” responses. Missing health data remains missing; it is not converted to zero or an invented score.

## Request data flow

The static dashboard at `/` loads `/static/dashboard.js`, which requests `GET /api/dashboard`. The dashboard service reads the selected seven-day window, computes training and health summaries, loads the current goal/plan, and returns up to ten recent activities.

Trend requests use `GET /api/dashboard/trends` with an explicit start date, end date, and week/month/year bucket. The route rejects equal or inverted dates before the application service runs.

Inspection routes read sync history, database/storage health, or coach availability. The backup route calls `OperationsService.backup()` and returns a generated backup identifier; it accepts no request body and does not expose arbitrary SQL or MCP calls.

## Persistence

SQLite is the canonical store. Schema version 1 contains tables for:

- `activities`
- `sleep_sessions`
- `recovery_signals`
- `sync_cursors`
- `sync_runs`
- `goals`
- `plans` and `plan_workouts`

Connections enable foreign keys, WAL mode, and a five-second busy timeout. A process-local re-entrant lock protects connection operations and backup/restore operations.

Backups are compressed SQLite database images named `dashboard-<timestamp>-<random>.sqlite3.gz`. Creation applies both count and age retention rules. Restore validates a generated backup identifier and uses SQLite’s backup API. Stop `app` and `scheduler` before restoring so no process writes during replacement.

## Compose deployment and trust boundaries

`compose.yaml` defines:

- `app`: FastAPI/Uvicorn on container port `8000`, published only to host loopback `127.0.0.1:8000`.
- `scheduler`: one-shot `python -m strava_dashboard.worker` process with no published port.
- `dashboard_data`: SQLite database and backups at `/var/lib/dashboard`.
- `garmin_tokens`: Garmin authentication state at `/root/.garminconnect`.

The image installs `garmin-mcp` from its pinned Git revision during build. The MCP server remains a child stdio process; Compose does not expose an HTTP MCP service.

`Settings` uses explicit uppercase environment aliases and `SecretStr` for the password. API exception handlers return generic storage or internal-error details and do not return exception text, credentials, token contents, raw MCP payloads, or local paths.

## Current versus planned frontend

Current frontend consists of `api/templates/index.html`, `api/static/dashboard.js`, and `api/static/dashboard.css`. It renders dashboard summary, health, goal, plan, and recent-activity text from same-origin API calls.

The React + TypeScript + Vite redesign in [the approved design](specs/2026-08-17-react-dashboard-redesign-design.md) is future work. It must keep FastAPI response contracts and same-origin access as the backend boundary; no React application is currently present in this repository.
