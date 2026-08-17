# Garmin Training Dashboard — Documentation Index

This is the entry point for project documentation. It separates current implementation guidance from historical specifications and implementation plans.

## How to Use This Index

- **Starting implementation?** Read the relevant story, then its linked architecture and convention docs.
- **Need system context?** Read [architecture overview](architecture/overview.md), then [data model](architecture/data-model.md).
- **Need domain terms?** Read the [glossary](domain/glossary.md).
- **Need API details?** Read the [application API](api/application.md) or [Garmin MCP contract](api/garmin-mcp.md).
- **Unsure about behavior?** Check [open questions](decisions/open-questions.md) before guessing.
- **Need historical intent?** Read `archive/` only after current docs; archived specs are not implementation truth.

Historical files are retained under `archive/` to preserve source context. Canonical documentation lives in the sections below.

## Architecture

- [Overview](architecture/overview.md) — Current runtime components, boundaries, data flow, and deployment.
- [Data model](architecture/data-model.md) — Domain entities, status values, and SQLite persistence.

## Domain

- [Glossary](domain/glossary.md) — Canonical meanings for Garmin, sync, training, health, planning, and API terms.

## Stories

Feature-level context. One story per file; status distinguishes implemented behavior from approved future work.

- [Garmin synchronization](stories/garmin-sync.md) — Authentication bootstrap, MCP ingestion, cursors, and stage results.
- [Dashboard and trends](stories/dashboard-and-trends.md) — Current dashboard summaries and trend API behavior.
- [Planning and coaching](stories/planning-and-coaching.md) — Goals, plan validation, coach boundary, and current limitations.
- [Operations and backups](stories/operations-and-backups.md) — Health inspection, backup creation, restore, and retention.
- [React dashboard](stories/react-dashboard.md) — Approved future frontend redesign; not implemented.

## API

- [Application API](api/application.md) — Local FastAPI routes, request parameters, response shapes, and errors.
- [Garmin MCP contract](api/garmin-mcp.md) — Stdio subprocess, tool contracts, mapping, and failure boundaries.

No raw OpenAPI or vendor API specification is currently stored under `docs/api/specs/`. If one is added later, check its size before loading. Files at or above roughly 200KB require user approval and targeted distillation; never auto-load them.

## Conventions

- [Security and secrets](conventions/security-and-secrets.md) — Loopback exposure, credential/token handling, and redaction rules.
- [Data integrity and failure](conventions/data-integrity-and-failure.md) — Idempotency, cursors, missing data, partial failures, plans, and backups.
- [Runtime and verification](conventions/runtime-and-verification.md) — Docker-first commands, configuration, tests, linting, and source limits.

## Decisions

- [Open questions](decisions/open-questions.md) — Contradictions or undefined behavior requiring a human decision.

## Historical source

- [Archived specifications](archive/specs/) — Original design documents and approved documentation/frontend specs.
- [Archived plans](archive/plans/) — Original implementation plans.
- `superpowers/plans/` — Agent execution artifacts; useful process history, not canonical product documentation.
