# Convention: data integrity and failure

## Sync integrity

Each data family has its own cursor and stage result. Stores persist records and advance the corresponding cursor atomically through `upsert_batch`. A Garmin or storage failure produces an explicit stage failure and does not erase known-good records or plans.

Sync stage error codes are operator-safe: `garmin_source_error` or `storage_error`. A later run or explicit manual run retries failed work; the system does not silently switch to another Garmin client.

## Missing data

The MCP adapter skips explicit “no sleep summary” and “no HRV data” responses. The application preserves unavailable health data as `null`, empty collections, or `health_status: "missing"`. Missing data is never converted to zero or an invented recovery value.

## Plan integrity

`PlanValidator` checks Monday week starts, workout dates inside the proposal week, duplicate scheduled days, weekly time budget, available weekdays, activity preferences, and explicit text requirements. Invalid provider responses or plans raise a validation error. Existing plans remain unchanged until a validated plan is accepted or edited.

## Backup integrity

Backups are generated compressed SQLite images. Retention applies count and age rules. Restore accepts only generated backup identifiers, not arbitrary paths. Stop `app` and `scheduler` before restore so no process writes concurrently.

Applies primarily to [Garmin synchronization](../stories/garmin-sync.md), [planning and coaching](../stories/planning-and-coaching.md), and [operations and backups](../stories/operations-and-backups.md).
