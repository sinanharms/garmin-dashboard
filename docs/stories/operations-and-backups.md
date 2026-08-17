# Story: Operations and backups

## Summary

As the operator, I need safe health inspection and compressed SQLite backup operations so that storage, sync, disk, and backup state can be checked without exposing secrets or arbitrary database controls.

## Status

The current implementation exposes read-only health/sync inspection plus a backup creation endpoint. Restore is an explicit container command and requires stopping both services first.

## Context

- [Architecture overview](../architecture/overview.md)
- [Application API](../api/application.md)
- [Security convention](../conventions/security-and-secrets.md)
- [Data-integrity convention](../conventions/data-integrity-and-failure.md)
- [Runtime convention](../conventions/runtime-and-verification.md)

## Acceptance Criteria

1. Health routes report application, Garmin inspection, storage, and coach-provider states using safe status values.
2. Sync-run routes provide recent runs and one-run details; unknown IDs return `404`.
3. Storage health reports database, backup, disk, and backup-freshness components.
4. `POST /api/dev/storage/backup` accepts no body and returns a generated backup ID or safe failure code.
5. Backups are compressed SQLite images with count and age retention rules.
6. Restore validates generated backup identifiers and rejects arbitrary paths.
7. Operators stop `app` and `scheduler` before restore.
8. The API does not expose arbitrary SQL, arbitrary MCP calls, credentials, tokens, prompts, raw MCP responses, or internal exception text.

## Testing Notes

Operations tests cover health aggregation, backup success/failure, retention, restore validation, concurrent SQLite access, safe API responses, and production composition wiring.
