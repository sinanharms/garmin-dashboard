# Open questions

Questions below come from differences between approved design documents and current source/configuration. They are not implementation assumptions.

## Runtime scheduling

- **OQ-1: What starts recurring sync?** Older design documents describe a nightly incremental synchronization. Current Compose starts `python -m strava_dashboard.worker` once and the process exits. Decide whether an external scheduler, Compose restart policy, host timer, or application scheduler owns recurrence.

- **OQ-2: What creates daily backups?** Design documents describe daily compressed backups. Current code exposes manual `POST /api/dev/storage/backup`; no scheduled backup trigger is present. Decide whether daily backup scheduling belongs in the worker, host automation, or remains manual.

## Health and observability

- **OQ-3: Should Garmin health perform a live MCP check?** The design describes authentication state and last MCP check. Current `SQLiteInspectionService.garmin_health()` reports stored sync information and does not perform a live check. Define expected timing, cost, and failure semantics before changing it.

- **OQ-4: Which sync details are canonical?** Older design text mentions authentication, fetch, persistence, and metric-rebuild stages. Current `SyncRun` contains only activities, sleep, and recovery stage results. Decide whether to expand the model or keep the current three-family contract.

## Data model and provider scope

- **OQ-5: Are derived-metric and coach-context tables required?** Older design text lists daily derived metrics, coach context, and backup metadata as SQLite data. Current schema has no such tables. Decide whether these are future entities or stale design scope.

- **OQ-6: When does a concrete coach provider ship?** Current production wiring exposes `CoachHealth` as unavailable and uses no concrete AI provider. Decide provider, configuration, security, and user-consent requirements before implementation.

- **OQ-7: Where should planning writes be exposed?** Current planning services and stores exist, but FastAPI exposes no goal/plan write routes. Decide whether planning remains an internal/application boundary or gains an HTTP/UI surface.

## Dependency reproducibility

- **OQ-8: Should Docker pin Garmin MCP to the discovered schema commit?** The adapter records commit `3610be6feed93088d85b0f35aba9d7d07c2505a7`, while `Dockerfile` installs from the repository Git URL without an explicit commit selector. Decide the release reproducibility policy.
