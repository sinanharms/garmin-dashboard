# Strava Dashboard Design

## Purpose

Build a self-hosted, single-user training dashboard that provides more useful long-term insight than the native Strava app. It runs on a Raspberry Pi and is available only on the home LAN.

The dashboard focuses on long-term trends, fitness status, goal progress, workout planning, and explained suggestions. Recent activities are supporting context rather than the primary screen.

## Scope

Initial release includes:

- Strava OAuth connection for the single authorized athlete.
- One historical import, followed by nightly incremental synchronization.
- All Strava activity types.
- Long-term activity and training-load trends.
- Fitness status and recovery signals derived locally from stored activity summaries.
- Goal capture, editable weekly plans, and suggested next workouts.
- AI-assisted coaching that asks for a goal and constraints before proposing a plan.
- Optional comparison of a selected past race or activity against its preceding training block.
- Predefined, read-only inspection endpoints for troubleshooting.

Initial release excludes:

- Public hosting, remote access, user accounts, multi-user data, and social features.
- Photos, GPX/FIT files, full route streams, map tiles, and direct writable SQLite access.
- Medical or injury guidance.

## Deployment

The Raspberry Pi runs one Docker Compose stack on the home LAN. The stack contains the web application, its scheduler, and a SQLite database mounted on persistent storage. No public ingress, remote authentication, or external database is required.

The app owns secrets. Strava OAuth tokens and the selected AI provider key remain server-side and are never returned from API responses.

## Components

### Web dashboard

The homepage has these priority areas:

1. Current fitness status: training load, weekly volume, trend direction, and recovery signal.
2. Long-term charts: distance, duration, elevation, sport mix, and load by week, month, and year.
3. Goal card: goal, target date, current plan phase, and progress.
4. This week: planned and completed workouts plus the next suggested session.
5. Compact recent-activity list for context.

The planning UI lets the user define or edit a goal, target date, activity preferences, weekly time budget, available days, and constraints. Plans and workouts remain editable by the user.

### Application API

The application API serves dashboard data, owns Strava synchronization, calculates derived metrics, creates race-analysis inputs, validates plans, and exposes read-only debugging views. It is the only component that reads or writes SQLite.

The AI provider is isolated behind a single interface so it can be changed without changing dashboard, metrics, or storage logic.

### Storage

SQLite stores normalized activity summaries, daily derived metrics, goals, plans, coach context, sync-run history, and backup metadata. It does not store media, route streams, raw activity files, or map data.

The application makes a daily compressed database backup. Backup retention is explicit and configurable. The dashboard exposes database, backup, and disk use. Nothing is silently deleted. Synchronization stops with a visible error when configured storage capacity is reached.

### Strava synchronization

OAuth identifies and authorizes the athlete. The user ID is recorded as identity metadata; authorization uses the OAuth token.

The initial import pages through historical activities at the largest supported page size. Future nightly runs use the last successful synchronization timestamp and stop once the known range is reached. The sync captures rate-limit response headers, respects limits, and records the outcome of each stage.

On token failure, API failure, or rate limiting, the application retains existing data and reports the failed stage. It does not silently mutate data or plans, and it retries only on the next scheduled run or an explicit manual retry.

### Metric and race analysis engine

The metric engine produces daily and aggregate measures used by the dashboard, including volume, duration, elevation, sport mix, rolling load, trend direction, and recovery signal.

When the user selects a past race or other outcome activity, the race analyzer identifies the preceding training block and produces a structured summary of volume, load, intensity distribution, recovery pattern, and result context. The summary becomes evidence for a future plan; it does not claim causal certainty.

### AI coach and plan validator

The coach first collects goal and constraints. It receives a compact structured summary of the current training state, goal, constraints, and optional race analysis. It returns a proposed weekly plan with each workout's purpose, duration, intensity, and explanation.

The application validates plan structure and explicit user-defined constraints before it can be saved. It does not infer medical limits. The coach cannot auto-change an existing plan. The user can accept, edit, skip, or regenerate each workout. After nightly synchronization, the app may recommend a plan change but must not apply it without user action.

AI failures, invalid response schemas, and rejected plans leave the previous plan unchanged and expose a clear reason. No prompt, token, or API key is exposed by diagnostics.

## Data Flow

1. Nightly sync fetches authorized Strava activity summaries.
2. The application persists changed activities in SQLite and rebuilds affected metrics.
3. Dashboard reads derived metrics and plans from the application API.
4. The user sets a goal and constraints, optionally selecting a past race to analyze.
5. The race analyzer and metric engine construct a compact coach input.
6. The AI coach returns an explainable plan proposal.
7. The plan validator accepts or rejects it before the user saves or edits it.

## Inspection API

All inspection endpoints are predefined and read-only. They expose no secrets and do not allow arbitrary SQL.

- `GET /api/dev/health`: combined health summary.
- `GET /api/dev/strava/health`: token validity, authorization status, last API check, rate-limit remaining, and last sync result.
- `GET /api/dev/sync/runs`: recent runs, stages, counts, duration, and failures.
- `GET /api/dev/sync/runs/{id}`: token refresh, fetch, persistence, and metric rebuild detail for one run.
- `GET /api/dev/storage/health`: database size, backup size, and disk status.
- `GET /api/dev/coach/health`: last AI-call status and schema-validation failures without prompts or credentials.

## Failure Behavior

Failure status is explicit, inspectable, and non-destructive.

- Strava rate limit, expired token, or API error: retain known-good data and show synchronization failure.
- AI unavailable or invalid response: save no new plan and retain current plan.
- Plan validation failure: reject proposal and show the violated rule.
- Storage hard limit: stop sync and show capacity condition.
- Backup failure: report it separately; do not represent data as protected when it is not.

## Verification

Automated coverage must include:

- Strava pagination, incremental synchronization, rate-limit handling, and token failures.
- Metric calculations using known activity fixtures.
- Race-block selection and structured analysis inputs.
- Goal capture, plan validation, invalid AI responses, and unchanged-plan failure behavior.
- Read-only inspection endpoints and secret redaction.
- Database backup, retention, and storage-limit reporting.

Before release, run formatting, linting, type checks, tests, and Docker Compose startup on a Pi-compatible architecture.
