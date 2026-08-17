# Story: Garmin data synchronization

## Summary

As the dashboard operator, I need Garmin activity, sleep, and recovery data imported through the approved Garmin MCP stdio boundary so that local summaries can be updated without exposing raw Garmin data or credentials.

## Status

The current Python implementation supports one-shot sync runs for activities, sleep, and recovery. Historical initial import and a recurring nightly trigger remain source-design intent; Compose currently starts a scheduler process that performs one run and exits.

## Context

- [Architecture overview](../architecture/overview.md)
- [Data model](../architecture/data-model.md)
- [Garmin MCP contract](../api/garmin-mcp.md)
- [Security convention](../conventions/security-and-secrets.md)
- [Data-integrity convention](../conventions/data-integrity-and-failure.md)
- [Open questions](../decisions/open-questions.md)

## Acceptance Criteria

1. `Settings` validates Garmin credentials, token directory, database/backup paths, MCP command, timeout, and retention settings.
2. Authentication is an explicit `garmin-mcp-auth` bootstrap operation with interactive MFA support.
3. Sync uses a Garmin MCP child process over stdio; no direct Garmin client or HTTP MCP endpoint is used.
4. Activities use paged date-range requests; sleep and recovery use date-based requests.
5. Payloads are validated and mapped into `Activity`, `SleepSession`, and `RecoverySignal` models.
6. Activities, sleep, and recovery maintain independent cursors and stage results.
7. Records and their cursor advance are persisted through storage boundaries without discarding known-good data on stage failure.
8. Missing sleep or HRV responses remain missing rather than becoming zero values.
9. Sync runs expose counts and safe error codes through the inspection API.
10. Credentials, token state, prompts, raw MCP payloads, and provider keys never appear in API responses or diagnostics.

## Testing Notes

Relevant coverage includes configuration validation, MCP session lifecycle/errors, tool mapping fixtures, adapter errors, sync stages, cursor behavior, and worker exit status. Run the focused config test and full suite using the read-only test mount described in [runtime and verification](../conventions/runtime-and-verification.md).
