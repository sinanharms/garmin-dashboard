# Documentation Refresh Design

## Status

Approved design. This change documents the implemented Garmin Training Dashboard without changing runtime behavior.

## Goal

Make the repository understandable to a new operator and developer by separating onboarding, architecture, and HTTP API reference material.

## Scope

- Refresh `README.md` as the entry point for setup, local operation, testing, backups, security, and navigation.
- Add `docs/architecture.md` covering runtime components, data flow, persistence, and trust boundaries.
- Add `docs/api.md` covering the implemented root/static routes and `/api` endpoints, query parameters, response contracts, errors, and safe examples.
- Describe only behavior present in the current source and Compose configuration.
- Mark the planned React redesign as future work rather than presenting it as shipped functionality.

## Documentation Boundaries

`README.md` is for someone running the project. It will use Docker Compose as the primary workflow and link to the deeper references.

`docs/architecture.md` is for maintainers. It will describe the dependency direction from domain models through application services to Garmin MCP and SQLite adapters, plus the API and worker entrypoints.

`docs/api.md` is for API consumers and operators. It will document the FastAPI routes declared in `routes_dashboard.py` and `routes_dev.py`, including validation and error behavior visible at the HTTP boundary.

## Source of Truth

Documentation facts will be checked against:

- `compose.yaml`, `Dockerfile`, `.env.example`, and `scripts/garmin-auth.sh` for operations.
- `pyproject.toml` and the `../../../src/garmin_dashboard` package for runtime dependencies and structure.
- FastAPI route modules and Pydantic response models for endpoint contracts.
- Existing tests for supported behavior and error cases.

The generated docs will not expose credential values, token state, raw MCP responses, or local secret paths.

## Acceptance Criteria

- A new operator can configure and start the Compose stack from the README.
- Every environment variable in `.env.example` has a documented purpose and required status.
- The README explains authentication bootstrap, manual sync, health checks, and safe backup restore ordering.
- Architecture docs distinguish current implementation from planned frontend work.
- API docs cover every implemented HTTP endpoint with method, path, purpose, parameters, response shape, and relevant errors.
- Markdown links and code examples are internally consistent with repository paths and commands.
- No source or runtime behavior changes are introduced.
