# Domain glossary

| Term | Meaning in this project |
| --- | --- |
| Activity | Normalized Garmin activity summary stored as an `Activity` model. |
| Backup ID | Generated filename identifying a compressed SQLite backup; it is not an arbitrary filesystem path. |
| Coach provider | Port that may propose a `PlanProposal` from structured `CoachContext`; current production wiring uses an unavailable provider. |
| Cursor / watermark | Per-data-family timestamp used to narrow later sync windows. |
| Data family | One of `activities`, `sleep`, or `recovery`. |
| Garmin MCP | The external Garmin MCP server launched as a child stdio process. |
| Garmin token state | Persisted authentication state written by `garmin-mcp-auth` and mounted from the `garmin_tokens` volume. |
| Health summary | Aggregated sleep and recovery information for a requested date range. |
| Plan proposal | Structured weekly workouts proposed by a coach or user before validation. |
| Recovery signal | A measured recovery/HRV metric with name, value, unit, and measurement time. |
| Sync run | One worker execution containing independent stage results for each data family. |
| Training summary | Aggregated activity count, volume, distance, elevation, sport mix, and optional load. |
| Validated plan | A plan proposal that passed explicit user constraints and application validation. |
| Workout | One scheduled training session inside a plan proposal. |
