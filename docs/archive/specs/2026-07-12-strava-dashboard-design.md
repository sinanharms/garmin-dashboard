# Garmin Training Dashboard Design

## Purpose

Build a self-hosted, single-user training dashboard that provides useful long-term insight from Garmin data. It runs on a Raspberry Pi and is available only on the home LAN.

The dashboard focuses on long-term trends, fitness status, sleep and recovery context, goal progress, workout planning, and explained suggestions. Recent activities are supporting context rather than the primary screen.

## Scope

The MVP includes:

- Garmin MCP authentication for one user.
- One historical import, followed by nightly incremental synchronization.
- Garmin activity summaries for all activity types exposed by MCP.
- Sleep sessions and recovery/readiness signals exposed by MCP.
- Long-term activity, sleep, recovery, and training-load trends.
- Fitness status that clearly reports stale or missing health data.
- Goal capture, editable weekly plans, and suggested next workouts.
- AI-assisted coaching that asks for a goal and constraints before proposing a plan.
- Optional comparison of a selected past race or activity against its preceding training block.
- Predefined, read-only inspection endpoints for troubleshooting.

The MVP excludes:

- Public hosting, remote access, user accounts, multi-user data, and social features.
- Photos, GPX/FIT files, full route streams, map tiles, raw MCP payloads, and direct database access.
- Direct Garmin API/client calls outside the MCP adapter.
- Medical, diagnostic, or injury guidance.

The dashboard layout and information hierarchy are an MVP baseline and may be reworked independently in a later design pass.

## Deployment and authentication

The Raspberry Pi runs one Docker Compose stack on the home LAN. The stack contains the web application, its scheduler, and SQLite mounted on persistent storage. Garmin MCP is started by the scheduler over stdio for each sync run; it has no exposed HTTP endpoint.

Garmin authentication is an explicit bootstrap operation using `garmin-mcp-auth`. MFA remains interactive during bootstrap. The resulting `~/.garminconnect` token state is stored on a persistent volume and reused by scheduled syncs.

`GARMIN_EMAIL` and `GARMIN_PASSWORD` are loaded through a Pydantic Settings model. Required settings fail validation at startup when missing or invalid. Credentials, tokens, prompts, raw MCP responses, and the AI provider key remain server-side and are never returned by APIs or diagnostics.

## Modular architecture

The application follows dependency inversion and keeps replaceable concerns behind app-owned ports:

1. **Domain**: activities, sleep, recovery, goals, plans, sync state, and derived metrics. This layer has no Garmin, MCP, SQLite, filesystem, HTTP, or AI-provider dependency.
2. **Use cases**: synchronization, metric rebuilding, dashboard queries, race analysis, coaching, and plan validation.
3. **Ports**: interfaces for Garmin data, activity/sleep/recovery persistence, goals and plans, sync state, backups, time, and AI coaching.
4. **Adapters**: Garmin MCP, SQLite, future filesystem storage, HTTP API, scheduled jobs, and UI.

The dashboard depends only on dashboard query and use-case interfaces. Synchronization depends on a `GarminDataSource` port and storage ports. No use case imports MCP protocol types or SQLite-specific models.

The `GarminMcpAdapter` implements the Garmin data port. SQLite repositories implement the storage ports. A future filesystem adapter can replace SQLite in the composition root without changing dashboard, metrics, coaching, or synchronization logic.

Port contracts define behavior rather than storage details, including stable identifiers, idempotent upserts, date-range queries, per-data-family watermarks, atomic updates or equivalent failure safety, and explicit missing-data handling. The filesystem adapter must implement its own indexing, deduplication, atomic writes, and consistency guarantees.

Concrete adapters are wired in one composition-root module. Each module has one focused responsibility and remains small enough to understand and test independently.

## Components

### Web dashboard

The MVP homepage prioritizes:

1. Fitness status: training load, weekly volume, trend direction, sleep, and recovery signals.
2. Long-term charts: distance, duration, elevation, sport mix, sleep, recovery, and load by week, month, and year.
3. Goal card: goal, target date, current plan phase, and progress.
4. This week: planned and completed workouts plus the next suggested session.
5. Compact recent-activity list for context.

The planning UI lets the user define or edit a goal, target date, activity preferences, weekly time budget, available days, and constraints. Plans and workouts remain editable by the user. The UI must show when sleep or recovery data is unavailable or stale; it must not treat missing data as normal recovery.

### Application API and use cases

The application API serves dashboard data, invokes use cases, validates plans, and exposes read-only debugging views. It does not contain persistence queries, MCP calls, or provider-specific coaching logic.

The AI provider is isolated behind a coach port so it can be changed without changing dashboard, metrics, or storage logic.

### Garmin MCP adapter

The adapter owns MCP process startup and shutdown, typed tool calls, timeouts, protocol errors, Garmin failure mapping, and normalization into app-owned activity, sleep, and recovery models.

The scheduler starts one MCP stdio process per sync run and closes it when the run finishes. The application does not expose a pass-through MCP endpoint and does not silently fall back to another Garmin client.

### Storage

SQLite is the MVP canonical store. It provides indexed date queries, atomic upserts, transaction boundaries, and safe concurrent access from the web application and scheduler without a separate database service.

SQLite stores normalized activity summaries, sleep sessions, recovery/readiness records, daily derived metrics, goals, plans, coach context, sync-run history, and backup metadata. It does not store media, route streams, raw MCP payloads, or map data.

The application makes a daily compressed database backup. Backup retention is explicit and configurable. The dashboard exposes database, backup, and disk use. Nothing is silently deleted. Synchronization stops with a visible error when configured storage capacity is reached.

JSONL and CSV may be added later as export or debugging formats; they are not canonical storage for the MVP.

## Garmin synchronization

The initial import is date/window based and resumable. The adapter handles the pagination or windowing supported by the available MCP tools. Future nightly runs use the last successful watermark for each data family: activities, sleep, and recovery.

Each run records these stages:

1. Validate `GarminSettings` from the environment.
2. Check persisted Garmin authentication state.
3. Start the MCP stdio process.
4. Fetch changed activities, sleep, and recovery records.
5. Normalize and idempotently upsert records by Garmin identifiers.
6. Rebuild affected derived metrics.
7. Advance only the watermarks for completed data families.
8. Record counts, duration, and outcome.

Successful records are persisted before their watermark advances. A failure in one data family does not hide successful progress in another. Existing data and plans remain unchanged when a stage fails.

Authentication failure, expired tokens, MCP protocol errors, timeouts, unavailable data, and malformed responses produce an explicit failed stage. The system does not silently authenticate, discard records, invent missing health data, or apply plan changes. Retry occurs on the next scheduled run or an explicit manual retry.

## Data and metrics

The canonical models retain Garmin identifiers, source timestamps, UTC ordering timestamps, and Garmin-local dates/timezones for daily attribution.

The activity model contains the normalized summary fields required for duration, distance, elevation, sport mix, intensity, and training-load calculations. The sleep model contains the sleep sessions and nightly measures exposed by MCP. The recovery model contains the recovery/readiness signals exposed by MCP, with source metric identity and measurement time.

Unsupported or unavailable source fields remain explicitly unavailable. They are not replaced with assumed values.

The metric engine produces daily and aggregate measures used by the dashboard, including volume, duration, elevation, sport mix, rolling load, trend direction, sleep context, and recovery context.

When the user selects a past race or other outcome activity, the race analyzer identifies the preceding training block and produces a structured summary of volume, load, intensity distribution, sleep pattern, recovery pattern, and result context. The summary becomes evidence for a future plan; it does not claim medical or causal certainty.

## AI coach and plan validator

The coach first collects the goal and constraints. It receives a compact structured summary of current training, sleep, recovery, goal, constraints, and optional race analysis. It returns a proposed weekly plan with each workout's purpose, duration, intensity, and explanation.

The application validates plan structure and explicit user-defined constraints before saving. It does not infer medical limits. The coach cannot auto-change an existing plan. The user can accept, edit, skip, or regenerate each workout. After synchronization, the app may recommend a plan change but must not apply it without user action.

AI failures, invalid response schemas, and rejected plans leave the previous plan unchanged and expose a clear reason. No prompt, token, or API key is exposed by diagnostics.

## Data flow

1. The scheduler validates settings and starts the Garmin MCP stdio process.
2. The adapter fetches changed activity, sleep, and recovery records.
3. Use cases normalize and persist data through storage ports.
4. The metric engine rebuilds affected derived measures.
5. The dashboard reads use-case results through the application API.
6. The user sets a goal and constraints, optionally selecting a past outcome activity.
7. The race analyzer and metric engine construct a compact coach input.
8. The AI coach returns an explainable proposal.
9. The plan validator accepts or rejects it before the user saves or edits it.

## Inspection API

All inspection endpoints are predefined and read-only. They expose no secrets and do not allow arbitrary MCP calls or SQL.

- `GET /api/dev/health`: combined application health summary.
- `GET /api/dev/garmin/health`: authentication state, last MCP check, and last sync result without token data.
- `GET /api/dev/sync/runs`: recent runs, stages, counts, duration, and redacted failures.
- `GET /api/dev/sync/runs/{id}`: authentication, fetch, persistence, and metric rebuild detail for one run.
- `GET /api/dev/storage/health`: database size, backup size, and disk status.
- `GET /api/dev/coach/health`: last AI-call status and schema-validation failures without prompts or credentials.

## Failure behavior

Failure status is explicit, inspectable, and non-destructive.

- Invalid settings or unavailable authentication: stop the run and report bootstrap or configuration failure.
- MCP timeout, protocol error, unavailable data, or malformed response: retain known-good data and report the failed stage.
- AI unavailable or invalid response: save no new plan and retain the current plan.
- Plan validation failure: reject the proposal and show the violated rule.
- Storage hard limit: stop synchronization and show the capacity condition.
- Backup failure: report it separately; do not represent data as protected when it is not.

## Verification

Automated coverage must include:

- Pydantic Settings validation for missing and invalid Garmin credentials.
- MCP stdio startup, shutdown, timeout, protocol-error, and expired-token behavior.
- Activity, sleep, and recovery normalization using known fixtures.
- Idempotent imports, date-window imports, and per-data-family watermarks.
- Partial sync failure without data or plan loss.
- Metric calculations using activity, sleep, and recovery fixtures.
- Race-block selection and structured coaching inputs.
- Goal capture, plan validation, invalid AI responses, and unchanged-plan failure behavior.
- Read-only inspection endpoints and secret redaction.
- SQLite backup, restore, retention, and storage-limit reporting.
- Contract tests that can run against both SQLite and a future filesystem storage adapter.
- Docker Compose startup on a Raspberry Pi-compatible architecture.

Before release, run formatting, linting, type checks, tests, and Docker Compose startup on a Pi-compatible architecture.
