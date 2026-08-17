# Story: Dashboard and trends

## Summary

As the dashboard operator, I need current training and health summaries plus date-bucketed trends so that activity volume, sleep, recovery, goals, plans, and recent activities are visible from the local dashboard.

## Status

The backend exposes dashboard and trend responses. The React browser UI renders current values, supported breakdowns, planning explanations, and lazy historical card detail without changing API ownership.

## Context

- [Architecture overview](../architecture/overview.md)
- [Data model](../architecture/data-model.md)
- [Application API](../api/application.md)
- [Security convention](../conventions/security-and-secrets.md)
- [React dashboard story](react-dashboard.md)

## Acceptance Criteria

1. `GET /api/dashboard` accepts an optional `today` date and returns generated time, training, health, health status, goal, plan, and up to ten recent activities.
2. Training summaries include activity count, duration, distance, elevation, sport counts, and optional training load.
3. Health summaries include availability, average sleep duration/score, and recovery metrics without inventing unavailable values.
4. `GET /api/dashboard/trends` requires `start` and `end`, accepts week/month/year buckets, and rejects equal or inverted dates with `422`.
5. The React dashboard loads same-origin `/api/dashboard` data and displays explicit unavailable states.
6. API errors return safe generic details and never include internal exception text.
7. Frontend detail keeps FastAPI response contracts as the source of truth and adds presentation progressively without changing backend ownership.

## Testing Notes

API tests cover dashboard fields, trend query validation, response redaction, shell/static delivery, and unexpected error handling. Frontend tests cover historical query ranges, inclusive display dates, gap preservation, and supported dashboard presentation. Metric tests cover training, health, rolling load, and trend summaries.
