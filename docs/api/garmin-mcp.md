# Garmin MCP integration contract

## Boundary

The application uses Garmin MCP as its only Garmin training-data source. `StdioMcpSessionFactory` starts the configured command as a child process, sets `GARMIN_MCP_TRANSPORT=stdio`, passes the persisted token directory through `GARMINTOKENS`, initializes an MCP `ClientSession`, and closes the process after each adapter run.

The MCP server is not exposed through FastAPI. Browser/API consumers receive normalized Pydantic models, never tool arguments, raw MCP payloads, prompts, tokens, or provider credentials.

## Schema source

The adapter records the discovered MCP tool schema at commit `3610be6feed93088d85b0f35aba9d7d07c2505a7`. The fixture used to inspect that schema is `tests/fixtures/garmin_mcp_list_tools_schema.json`. The Dockerfile currently installs the Garmin MCP repository from a Git URL; whether image builds must pin the same commit is recorded in [open questions](../decisions/open-questions.md).

## Tool contracts

| Tool | Required arguments | Optional arguments | Adapter behavior |
| --- | --- | --- | --- |
| `get_activities_by_date` | `start_date` string, `end_date` string | `activity_type` string, `page` integer, `page_size` integer | Requests date range with page size `200`, follows `has_more` and increasing `next_page`, maps rows to `Activity`. |
| `get_sleep_summary` | `date` string | None | Requests each date in the window and maps sleep start/end, seconds, and optional score to `SleepSession`. |
| `get_hrv_data` | `date` string | `return_timeseries` boolean, sent as `false` | Requests each date and maps supported HRV metrics to `RecoverySignal` values in `ms`. |

Dates are sent as ISO dates. Activity timestamps are mapped with the sync-window timezone. Sleep and recovery records retain Garmin-local date attribution plus timezone-aware measurement timestamps.

## Normalized outputs

- Activities preserve Garmin external IDs and summary metrics for duration, distance, elevation, heart rate, and calories.
- Sleep produces one normalized session per returned date payload; explicit “No sleep summary found” responses are skipped.
- Recovery maps only supported metrics present in the payload. Explicit “No HRV data found” responses are skipped.

Malformed payloads, invalid pagination, invalid required fields, MCP startup failures, MCP tool errors, timeouts, and malformed content become Garmin source failures. The adapter closes the session even when a fetch fails.

## Mapping to stories

| Story | Primary integration | Operation |
| --- | --- | --- |
| [Garmin synchronization](../stories/garmin-sync.md) | `get_activities_by_date` | Import paged activity summaries and advance the activity cursor after storage succeeds. |
| [Garmin synchronization](../stories/garmin-sync.md) | `get_sleep_summary` | Import date-based sleep sessions and preserve missing-health state. |
| [Garmin synchronization](../stories/garmin-sync.md) | `get_hrv_data` | Import supported recovery signals without inventing unavailable metrics. |
| [Dashboard and trends](../stories/dashboard-and-trends.md) | Normalized domain models | Supply training, sleep, recovery, and trend summaries through the application API. |
