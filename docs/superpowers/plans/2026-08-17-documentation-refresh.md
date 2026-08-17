# Documentation Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Garmin Training Dashboard understandable to operators, maintainers, and API consumers without changing runtime behavior.

**Architecture:** Keep onboarding in `README.md`, maintainer context in `docs/architecture.md`, and HTTP contracts in `docs/api.md`. Derive operational commands and endpoint details from the current Compose, Python, and test sources.

**Tech Stack:** Markdown, Docker Compose, Python 3.14, FastAPI, Pydantic v2, SQLite, Garmin MCP over stdio.

## Global Constraints

- Use Docker Compose as the primary project workflow.
- Do not expose or print credentials, token state, raw MCP responses, or secret values.
- Document implemented behavior only; identify the React redesign as planned.
- Keep source files unchanged and under the repository’s existing limits.
- Preserve unrelated user changes, including the existing `.gitignore` modification.

---

### Task 1: Refresh operator README

**Files:**
- Modify: `README.md`
- Reference: `.env.example`, `compose.yaml`, `Dockerfile`, `scripts/garmin-auth.sh`, `pyproject.toml`

**Interfaces:**
- Consumes: Current Compose service names and commands.
- Produces: A safe onboarding path, environment-variable table, operational procedures, project map, and links to deeper docs.

- [ ] **Step 1: Replace setup-only content with sections for overview, prerequisites, quick start, configuration, operations, project structure, testing, security, and related docs.**
- [ ] **Step 2: Add all nine `.env.example` variables with purpose and required status, without showing local secret values.**
- [ ] **Step 3: Keep authentication bootstrap, health checks, manual sync, and backup restore commands aligned with `compose.yaml` and the existing README safety rules.**
- [ ] **Step 4: Link to `docs/architecture.md`, `docs/api.md`, and the approved design/planning docs with current/planned labels.**
- [ ] **Step 5: Review the README for commands or paths that do not exist in the repository.**

### Task 2: Add architecture reference

**Files:**
- Create: `docs/architecture.md`
- Reference: `src/strava_dashboard/domain`, `ports`, `application`, `adapters`, `api`, `worker.py`, `compose.yaml`

**Interfaces:**
- Consumes: Current module boundaries and runtime wiring.
- Produces: Maintainer-facing component map, data flows, persistence model, failure boundaries, and security/trust-boundary notes.

- [ ] **Step 1: Describe the current runtime components and dependency direction with a compact repository tree.**
- [ ] **Step 2: Document sync flow from scheduler through Garmin MCP stdio, mapping, application sync, and SQLite stores.**
- [ ] **Step 3: Document request flow from FastAPI routes through application query/operations services to SQLite.**
- [ ] **Step 4: Document named volumes, loopback-only HTTP exposure, token handling, backup retention, and failure behavior supported by code/config.**
- [ ] **Step 5: Clearly separate current static dashboard behavior from the planned React redesign.**

### Task 3: Add API reference

**Files:**
- Create: `docs/api.md`
- Reference: `src/strava_dashboard/api/routes_dashboard.py`, `src/strava_dashboard/api/routes_dev.py`, response models, `tests/test_api.py`

**Interfaces:**
- Consumes: FastAPI route paths, query parameters, response models, and tested HTTP errors.
- Produces: Consumer-facing endpoint reference for `/`, `/static/*`, `/api/dashboard`, `/api/dashboard/trends`, and all `/api/dev/*` routes.

- [ ] **Step 1: Add base URL, content-type, authentication scope, and safe request conventions.**
- [ ] **Step 2: Document dashboard endpoints with parameters, validation rules, response-field summaries, and examples.**
- [ ] **Step 3: Document inspection, sync-run, storage, backup, and coach-health endpoints with status/error behavior.**
- [ ] **Step 4: Keep examples free of real credentials, tokens, raw MCP payloads, and machine-specific paths.**
- [ ] **Step 5: Cross-check every listed route against the two route modules and tests.**

### Task 4: Verify documentation

**Files:**
- Verify: `README.md`, `docs/architecture.md`, `docs/api.md`

- [ ] **Step 1: Run `docker compose config` and confirm documented service names and configuration still match.**
- [ ] **Step 2: Run `docker compose run --rm app uv run pytest tests/test_config.py -q`.**
- [ ] **Step 3: Run `docker compose run --rm app uv run pytest -q`.**
- [ ] **Step 4: Run `docker compose run --rm app uv run ruff check .`.**
- [ ] **Step 5: Review the final diff and confirm no runtime files or unrelated user changes were modified.**
