# Data model and persistence

## Domain models

All domain and application data models use frozen Pydantic v2 `BaseModel` classes with extra fields forbidden. Tuple-typed collections preserve runtime immutability where records cross boundaries.

| Model | Purpose | Key fields |
| --- | --- | --- |
| `Activity` | Normalized Garmin activity summary. | External ID, type, start/local date, duration, distance, elevation, heart rate, calories. |
| `SleepSession` | One normalized sleep interval. | External ID, start/end, local date, duration, optional score. |
| `RecoverySignal` | One measured recovery/HRV metric. | External ID, local date, measurement time, metric name, value, unit. |
| `SyncWindow` | Source request boundary. | Optional start and required end; timestamps must be timezone-aware and ordered. |
| `ActivityCursor`, `SleepCursor`, `RecoveryCursor` | Per-family incremental watermark. | Data-family literal and watermark. |
| `SyncRun` | One worker execution. | Run ID, start/end, tuple of stage results. |
| `SyncStageResult` | One activity/sleep/recovery outcome. | Family, succeeded/failed status, record count, optional error code. |
| `TrainingSummary` | Activity metrics over a date range. | Counts, duration, distance, elevation, sport counts, optional training load. |
| `HealthSummary` | Sleep/recovery metrics over a date range. | Availability, average sleep duration/score, recovery metrics. |
| `TrendSnapshot` | Grouped training and health summaries. | Date range, week/month/year bucket, summary tuples. |
| `Goal` | User training objective. | Goal ID, description, target date. |
| `Workout` | One planned workout. | Scheduled date, activity type, duration, intensity, purpose, explanation. |
| `PlanConstraints` | User-editable plan limits. | Weekly budget, available weekdays, preferences, requirements. |
| `PlanProposal` | Coach or user-generated plan proposal. | Proposal/goal IDs, week start, workouts, explanation, creation time. |
| `ValidatedPlan` | Proposal that passed application validation. | Proposal and validation time. |
| `CoachContext` | Structured input boundary for a coach provider. | Goal, constraints, training, health, optional preceding block. |

See [glossary](../domain/glossary.md) for terminology and [planning story](../stories/planning-and-coaching.md) for validation behavior.

## Status values

| Concept | Values |
| --- | --- |
| Sync stage | `succeeded`, `failed` |
| Health status | `ok`, `degraded`, `unavailable` |
| Dashboard health data | `available`, `missing` |
| Trend bucket | `week`, `month`, `year` |
| Backup operation | `succeeded`, `failed` |

Missing health records stay nullable or empty. They are not represented as zero values. API consumers should inspect both the health payload and `health_status`.

## SQLite schema

SQLite is the canonical persistence adapter. Schema version 1 contains:

- `activities`: normalized activity summaries keyed by external ID.
- `sleep_sessions`: normalized sleep intervals keyed by external ID.
- `recovery_signals`: measured recovery metrics keyed by external ID.
- `sync_cursors`: one watermark per data family.
- `sync_runs`: run metadata and serialized stage results.
- `goals`: current goal records.
- `plans`: validated plan metadata.
- `plan_workouts`: workouts belonging to plans with cascade deletion.

Connections enable foreign keys, WAL mode, and a five-second busy timeout. A process-local re-entrant lock protects connection operations and backup/restore operations.

The current schema does not contain raw MCP payloads, media, route streams, map data, AI prompts, or provider keys. Older design references to daily derived-metric or coach-context tables remain future-scope questions; see [open questions](../decisions/open-questions.md).

## Related stories

- [Garmin synchronization](../stories/garmin-sync.md) owns source records, cursors, and sync runs.
- [Dashboard and trends](../stories/dashboard-and-trends.md) consumes training, health, and trend summaries.
- [Planning and coaching](../stories/planning-and-coaching.md) owns goals, constraints, proposals, and validated plans.
- [Operations and backups](../stories/operations-and-backups.md) owns storage health and backup lifecycle.
