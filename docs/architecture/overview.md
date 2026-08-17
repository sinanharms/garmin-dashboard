# Architecture overview

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
  └──────────── React production build ◄──────────────┘
```

The browser never connects directly to Garmin, MCP, SQLite, credentials, or token state.

## Boundaries

| Boundary | Location | Responsibility |
| --- | --- | --- |
| Domain | `src/strava_dashboard/domain/` | Immutable Pydantic models for activities, sleep, recovery, sync, summaries, goals, and plans. |
| Ports | `src/strava_dashboard/ports/` | Stable protocols and source/storage/coach errors used by application services. |
| Application | `src/strava_dashboard/application/` | Sync workflow, metric calculation, dashboard queries, planning validation, and operations. |
| Garmin adapter | `src/strava_dashboard/adapters/garmin_mcp/` | Starts MCP over stdio, calls tools, validates payloads, maps records, and closes sessions. |
| SQLite adapters | `src/strava_dashboard/adapters/sqlite/` | Schema, connection, normalized stores, sync history, and compressed backups. |
| HTTP delivery | `src/strava_dashboard/api/` | Production wiring, FastAPI routes, built React assets, and redacted error responses. |
| Browser UI | `frontend/` | React presentation, typed same-origin API client, responsive card interaction, and frontend tests. |
| Worker delivery | `src/strava_dashboard/worker.py` | One-shot sync entrypoint with a 30-day initial lookback. |

Detailed data entities and persistence tables live in [data-model.md](data-model.md). Shared rules live in [runtime](../conventions/runtime-and-verification.md), [security](../conventions/security-and-secrets.md), and [data integrity](../conventions/data-integrity-and-failure.md).

## Runtime composition

`api.app.build_production_services()` is the production composition root. It opens one SQLite connection, creates SQLite stores, then injects them into `DashboardService`, `SQLiteInspectionService`, and `OperationsService`. FastAPI owns that service bundle for the application lifespan and closes the connection during shutdown.

The worker composition root creates a `StdioMcpSessionFactory`, `GarminMcpAdapter`, SQLite activity/sleep/recovery stores, and `SyncService`. The worker opens a connection for one run and closes it afterward. It returns exit code `0` only when all three data-family stages succeed.

Tests inject fake dashboard, inspection, and operations services through `create_app()`. HTTP tests therefore do not require Garmin credentials or live MCP state.

## Synchronization flow

1. `worker.py` creates a timezone-aware window ending at the current time and beginning 30 days earlier.
2. `SyncService` runs independent activities, sleep, and recovery stages.
3. Each stage reads its SQLite cursor and narrows the request window when prior data exists.
4. `GarminMcpAdapter` opens one MCP stdio session, calls the relevant Garmin tools, maps validated payloads, and closes the session.
5. Each SQLite store upserts normalized records and advances its cursor to the sync window end.
6. The run is saved in `sync_runs` with one `SyncStageResult` per data family.
7. Garmin or storage failures become stage-level failure codes; the run remains inspectable through `/api/dev/sync/runs`.

The adapter skips explicit “no sleep summary” and “no HRV data” responses. Missing health data remains missing; it is not converted to zero or an invented score.

## Request flow

The React shell at `/` loads its hashed Vite assets from `/static/app/`, then requests `GET /api/dashboard`. The dashboard service reads the selected seven-day window, computes training and health summaries, loads the current goal/plan, and returns up to ten recent activities.

Expanding a metric card lazily requests `GET /api/dashboard/trends` with an explicit start date, exclusive end date, and week/month/year bucket. Weekly, monthly, and yearly controls request 12 weeks, 12 backend 30-day buckets, and five backend 365-day buckets respectively. The route rejects equal or inverted dates before the application service runs.

Inspection routes read sync history, database/storage health, or coach availability. The backup route calls `OperationsService.backup()` and returns a generated backup identifier; it accepts no request body and does not expose arbitrary SQL or MCP calls.

## Compose deployment

`compose.yaml` defines:

- `app`: FastAPI/Uvicorn on container port `8000`, published only to host loopback `127.0.0.1:8000`.
- `scheduler`: one-shot `python -m strava_dashboard.worker` process with no published port.
- `dashboard_data`: SQLite database and backups at `/var/lib/dashboard`.
- `garmin_tokens`: Garmin authentication state at `/root/.garminconnect`.

The image installs `garmin-mcp` from its pinned Git revision during build. The MCP server remains a child stdio process; Compose does not expose an HTTP MCP service.

The Docker frontend stage builds `frontend/` and copies `frontend/dist` into `api/static/app` in the application image. FastAPI serves `index.html` at `/` and the hashed assets under `/static/app/`. See the [React dashboard story](../stories/react-dashboard.md).

## Related stories

- [Garmin synchronization](../stories/garmin-sync.md)
- [Dashboard and trends](../stories/dashboard-and-trends.md)
- [Planning and coaching](../stories/planning-and-coaching.md)
- [Operations and backups](../stories/operations-and-backups.md)
- [React dashboard](../stories/react-dashboard.md)
