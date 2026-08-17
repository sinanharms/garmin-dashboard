# Garmin MCP Training Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Garmin-backed, single-user training dashboard described by the approved design, with Garmin MCP, sleep/recovery data, modular ports, SQLite storage, and a replaceable persistence boundary.

**Architecture:** Keep domain models and use cases independent of Garmin MCP, SQLite, HTTP, and any AI provider. Inject app-owned ports into use cases; wire concrete Garmin, SQLite, API, scheduler, and backup adapters only in the composition root. The first vertical slice is ingestion, followed by metrics/API, then planning/coaching and operations.

**Tech Stack:** Python 3.14, `pydantic-settings`, official Python MCP client, stdlib `sqlite3`, FastAPI/Uvicorn, HTTPX test client, pytest, Ruff, ty, uv, and Docker Compose. Garmin authentication uses `garmin-mcp-auth`; scheduled pulls use the `garmin-mcp` stdio server.

## Global Constraints

- Run the application in Docker Compose on a Raspberry Pi-compatible architecture.
- Garmin MCP is the only external training-data source; no direct Garmin client calls bypass the MCP adapter.
- `GARMIN_EMAIL` and `GARMIN_PASSWORD` are required environment settings validated by Pydantic Settings.
- Persist Garmin authentication state at `~/.garminconnect` through a mounted application volume.
- Never log or return credentials, tokens, prompts, raw MCP responses, or AI provider keys.
- Keep the MCP server on stdio; do not expose an HTTP MCP endpoint in the MVP.
- Store normalized records in SQLite; keep JSONL and CSV as non-canonical export formats.
- Keep domain and use-case code free of provider, transport, storage, and framework imports.
- Use Pydantic v2 `BaseModel` for all domain, port, application, API, and adapter data models; do not introduce dataclasses for application data.
- Configure immutable Pydantic models with `ConfigDict(frozen=True)` and use tuple-typed collections for nested runtime immutability.
- Keep source files below 300 lines by splitting modules by responsibility.
- Do not silently invent missing sleep or recovery values, mutate plans on sync, or silently retry failed runs.
- Preserve existing data when authentication, MCP, storage, backup, or AI stages fail.
- Use TDD for each behavior: failing test, focused implementation, passing test, then commit.

---

## Scope and file map

The repository is currently a minimal `src` package with one smoke test and no runtime application. Keep the existing `garmin_dashboard` import path stable to avoid an unnecessary package migration, but remove source-provider behavior and update the project description to Garmin.

Create this focused structure:

```text
src/strava_dashboard/
  config.py
  domain/
    models.py
    plan_models.py
  ports/
    garmin.py
    storage.py
    coach.py
  application/
    sync.py
    metrics.py
    race_analysis.py
    planning.py
    dashboard.py
  adapters/
    garmin_mcp/
      session.py
      mapping.py
      adapter.py
    sqlite/
      connection.py
      schema.py
      activity_store.py
      sleep_store.py
      recovery_store.py
      planning_store.py
      sync_store.py
      backup.py
  api/
    app.py
    dependencies.py
    routes_dashboard.py
    routes_dev.py
  worker.py

tests/
  conftest.py
  contracts/
    test_storage_contract.py
  fixtures/
    garmin_activity.json
    garmin_sleep.json
    garmin_recovery.json
  test_config.py
  test_domain_models.py
  test_garmin_mcp_adapter.py
  test_sqlite_stores.py
  test_sync.py
  test_metrics.py
  test_planning.py
  test_api.py
  test_operations.py

Dockerfile
compose.yaml
.dockerignore
AGENTS.md
scripts/garmin-auth.sh
```

`domain` owns immutable business data, `ports` owns stable interfaces, `application` owns workflows, `adapters` owns external details, and `api`/`worker.py` are delivery entrypoints. No file may combine MCP protocol parsing, persistence SQL, and business rules.

## Task 1: Establish validated configuration and container workflow

**Files:**
- Modify: `../../pyproject.toml`
- Modify: `../../README.md`
- Create: `../../src/strava_dashboard/config.py`
- Create: `../../tests/test_config.py`
- Create: `../../Dockerfile`
- Create: `../../compose.yaml`
- Create: `../../.dockerignore`
- Create: `../../AGENTS.md`

**Interfaces:**
- Produces `Settings` for all runtime wiring.
- Produces a reproducible image containing the app and Garmin MCP command.

- [ ] **Step 1: Add the runtime dependencies and metadata.**

Update `../../pyproject.toml` dependencies with `pydantic>=2.0`, `pydantic-settings>=2.0`, `mcp>=1.0`, `fastapi>=0.100`, `uvicorn[standard]>=0.20`, and `httpx>=0.20`. Keep existing dev tools. Change the project description and README title from Strava to Garmin training dashboard. Regenerate `../../uv.lock` using the project’s uv workflow; do not hand-edit the lock file.

- [ ] **Step 2: Write failing configuration tests.**

Add tests for required environment values, secret redaction, forbidden extra settings, and missing credentials:

```python
def test_settings_reads_required_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("GARMIN_EMAIL", "athlete@example.test")
    monkeypatch.setenv("GARMIN_PASSWORD", "secret")
    monkeypatch.setenv("GARMIN_TOKEN_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "dashboard.sqlite3"))
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("GARMIN_MCP_COMMAND", "garmin-mcp")
    monkeypatch.setenv("MCP_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("BACKUP_RETENTION_COUNT", "7")
    monkeypatch.setenv("BACKUP_RETENTION_DAYS", "31")

    settings = Settings()

    assert settings.garmin_email == "athlete@example.test"
    assert settings.garmin_password.get_secret_value() == "secret"
    assert "secret" not in repr(settings)


def test_settings_rejects_missing_garmin_password(monkeypatch, tmp_path):
    monkeypatch.setenv("GARMIN_EMAIL", "athlete@example.test")
    monkeypatch.setenv("GARMIN_TOKEN_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "dashboard.sqlite3"))
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("GARMIN_MCP_COMMAND", "garmin-mcp")
    monkeypatch.setenv("MCP_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("BACKUP_RETENTION_COUNT", "7")
    monkeypatch.setenv("BACKUP_RETENTION_DAYS", "31")

    with pytest.raises(ValidationError):
        Settings()
```

Run: `docker compose run --rm app uv run pytest tests/test_config.py -q`.
Expected: FAIL because `Settings` does not exist.

- [ ] **Step 3: Implement `Settings` with explicit environment aliases.**

Create `../../src/strava_dashboard/config.py`:

```python
from pathlib import Path

from pydantic import Field, PositiveInt, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="forbid", case_sensitive=False)

    garmin_email: str = Field(min_length=1, validation_alias="GARMIN_EMAIL")
    garmin_password: SecretStr = Field(validation_alias="GARMIN_PASSWORD")
    garmin_token_dir: Path = Field(validation_alias="GARMIN_TOKEN_DIR")
    database_path: Path = Field(validation_alias="DATABASE_PATH")
    backup_dir: Path = Field(validation_alias="BACKUP_DIR")
    garmin_mcp_command: str = Field(min_length=1, validation_alias="GARMIN_MCP_COMMAND")
    mcp_timeout_seconds: PositiveInt = Field(validation_alias="MCP_TIMEOUT_SECONDS")
    backup_retention_count: PositiveInt = Field(validation_alias="BACKUP_RETENTION_COUNT")
    backup_retention_days: PositiveInt = Field(validation_alias="BACKUP_RETENTION_DAYS")

    @field_validator("garmin_password")
    @classmethod
    def reject_empty_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("GARMIN_PASSWORD must not be empty")
        return value
```

Run the focused test again. Expected: PASS.

- [ ] **Step 4: Add the minimal container and Compose services.**

Use one application image with separate `app` and `scheduler` commands. Install both Garmin commands at image-build time so scheduled syncs do not depend on runtime package downloads:

```dockerfile
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.10.3 /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
RUN uv tool install --python 3.14 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp
RUN uv tool install --python 3.14 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth

COPY src ./src
RUN uv sync --frozen --no-dev
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"
```

Use one application image with separate `app` and `scheduler` commands. Mount SQLite/backups and Garmin token state as named volumes. Bind the web port to loopback only. Do not define a `garmin-mcp` HTTP service or publish port 8000. Add `../../.dockerignore` entries for `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `../../.env`, and local database/backup files.

`../../compose.yaml` must provide the settings explicitly:

```yaml
services:
  app:
    build: .
    command: uv run uvicorn garmin_dashboard.api.app:app --host 0.0.0.0 --port 8000
    env_file: .env
    environment:
      GARMIN_TOKEN_DIR: /var/lib/garminconnect
      DATABASE_PATH: /var/lib/dashboard/dashboard.sqlite3
      BACKUP_DIR: /var/lib/dashboard/backups
      GARMIN_MCP_COMMAND: garmin-mcp
      MCP_TIMEOUT_SECONDS: "30"
      BACKUP_RETENTION_COUNT: "7"
      BACKUP_RETENTION_DAYS: "31"
    volumes:
      - dashboard_data:/var/lib/dashboard
      - garmin_tokens:/var/lib/garminconnect
    ports:
      - "127.0.0.1:8000:8000"

  scheduler:
    build: .
    command: uv run python -m garmin_dashboard.worker
    env_file: .env
    environment:
      GARMIN_TOKEN_DIR: /var/lib/garminconnect
      DATABASE_PATH: /var/lib/dashboard/dashboard.sqlite3
      BACKUP_DIR: /var/lib/dashboard/backups
      GARMIN_MCP_COMMAND: garmin-mcp
      MCP_TIMEOUT_SECONDS: "30"
      BACKUP_RETENTION_COUNT: "7"
      BACKUP_RETENTION_DAYS: "31"
    volumes:
      - dashboard_data:/var/lib/dashboard
      - garmin_tokens:/var/lib/garminconnect

volumes:
  dashboard_data:
  garmin_tokens:
```

Document `.env` creation without printing its values. Add `.env` to `.gitignore` if it is not already ignored. Run: `docker compose config`. Expected: valid configuration with no exposed MCP service.

- [ ] **Step 5: Commit the baseline.**

Run `git status --short`, stage only Task 1 files, then run `git commit -m "build: add Garmin dashboard runtime configuration"`.

## Task 2: Define domain models and replaceable ports

**Files:**
- Create: `../../../src/garmin_dashboard/domain/models.py`
- Create: `../../../src/garmin_dashboard/domain/plan_models.py`
- Create: `../../../src/garmin_dashboard/ports/garmin.py`
- Create: `../../../src/garmin_dashboard/ports/storage.py`
- Create: `../../../src/garmin_dashboard/ports/coach.py`
- Create: `tests/test_domain_models.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces immutable `Activity`, `SleepSession`, `RecoverySignal`, `SyncWindow`, `SyncCursor`, `SyncRun`, `Goal`, `Workout`, and `PlanProposal` models.
- Produces `GarminDataSource`, storage, backup, and `CoachProvider` protocols.

- [ ] **Step 1: Write model validation tests.**

Test that IDs and activity types are non-empty, durations are non-negative, timestamps preserve timezone information, sleep windows end after they start, recovery values carry metric identity and units, and a sync cursor belongs to exactly one data family. Use UTC-aware datetimes in fixtures.

- [ ] **Step 2: Implement immutable Pydantic domain models.**

Use Pydantic v2 `BaseModel` with `ConfigDict(frozen=True, extra="forbid")`. Use standard-library field types, `@field_validator` for scalar checks, `@model_validator` for cross-field checks, and typed tuples for nested collections. Define `TrainingSummary`, `HealthSummary`, `TrainingBlock`, `DashboardSnapshot`, `TrendBucket`, and `TrendSnapshot` in this module alongside the core records. Define `Goal`, `Workout`, `PlanConstraints`, `PlanProposal`, `ValidatedPlan`, and `CoachContext` in `plan_models.py`. The core signatures are:

```python
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


DataFamily = Literal["activities", "sleep", "recovery"]
SyncStatus = Literal["succeeded", "failed"]


class SyncWindow(DomainModel):
    start: datetime | None
    end: datetime


class Activity(DomainModel):
    external_id: str
    activity_type: str
    started_at: datetime
    local_date: date
    duration_seconds: int
    distance_meters: float | None
    elevation_meters: float | None
    average_heart_rate: float | None
    max_heart_rate: float | None
    calories: float | None


class SleepSession(DomainModel):
    external_id: str
    started_at: datetime
    ended_at: datetime
    local_date: date
    duration_seconds: int
    score: float | None


class RecoverySignal(DomainModel):
    external_id: str
    local_date: date
    measured_at: datetime
    metric_name: str
    value: float
    unit: str


class SyncCursor(DomainModel):
    data_family: DataFamily
    watermark: datetime


class SyncStageResult(DomainModel):
    data_family: DataFamily
    status: SyncStatus
    record_count: int
    error_code: str | None


class SyncRun(DomainModel):
    run_id: str
    started_at: datetime
    ended_at: datetime | None
    stages: tuple[SyncStageResult, ...]
```

Use `@field_validator` for non-empty identifiers, finite non-negative integer durations/counts, and timezone-aware datetimes. Use `@model_validator(mode="after")` for ordering rules such as sleep end after start and sync end after start. Do not coerce malformed source data to defaults. All nested collections use typed tuples and are rejected or normalized by Pydantic before the frozen model is returned.

- [ ] **Step 3: Define storage and source ports.**

Keep protocols free of SQLite, MCP, and FastAPI types:

```python
class GarminDataSource(Protocol):
    async def fetch_activities(self, window: SyncWindow) -> Sequence[Activity]: ...
    async def fetch_sleep(self, window: SyncWindow) -> Sequence[SleepSession]: ...
    async def fetch_recovery(self, window: SyncWindow) -> Sequence[RecoverySignal]: ...


class ActivityStore(Protocol):
    def cursor(self) -> SyncCursor | None: ...
    def upsert_batch(self, records: Sequence[Activity], cursor: SyncCursor) -> int: ...
    def between(self, start: datetime, end: datetime) -> Sequence[Activity]: ...


class SleepStore(Protocol):
    def cursor(self) -> SyncCursor | None: ...
    def upsert_batch(self, records: Sequence[SleepSession], cursor: SyncCursor) -> int: ...
    def between(self, start: datetime, end: datetime) -> Sequence[SleepSession]: ...


class RecoveryStore(Protocol):
    def cursor(self) -> SyncCursor | None: ...
    def upsert_batch(self, records: Sequence[RecoverySignal], cursor: SyncCursor) -> int: ...
    def between(self, start: datetime, end: datetime) -> Sequence[RecoverySignal]: ...
```

Add `SyncRunStore`, `GoalStore`, `PlanStore`, `BackupStore`, and `CoachProvider` with the same explicit behavior. `upsert_batch` must persist records and advance that data family’s cursor atomically.

- [ ] **Step 4: Add domain tests and commit.**

Run `docker compose run --rm app uv run pytest tests/test_domain_models.py -q`. Expected: PASS. Commit only Task 2 files with `git commit -m "feat: define Garmin dashboard domain ports"`.

## Task 3: Build the Garmin MCP stdio adapter

**Files:**
- Create: `../../../src/garmin_dashboard/adapters/garmin_mcp/session.py`
- Create: `../../../src/garmin_dashboard/adapters/garmin_mcp/mapping.py`
- Create: `../../../src/garmin_dashboard/adapters/garmin_mcp/adapter.py`
- Create: `tests/fixtures/garmin_activity.json`
- Create: `tests/fixtures/garmin_sleep.json`
- Create: `tests/fixtures/garmin_recovery.json`
- Create: `tests/test_garmin_mcp_adapter.py`

**Interfaces:**
- Consumes: `Settings`, `SyncWindow`, and domain models from Task 2.
- Produces: `GarminDataSource` implemented by `GarminMcpAdapter`.

- [ ] **Step 1: Discover and record the upstream MCP tool schema.**

In the container, run the supplied server command and inspect its advertised tools through an MCP client:

```bash
uvx --python 3.14 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp --help
```

Use the official Python MCP client’s `list_tools` operation in a temporary diagnostic program. Record the exact tool names and argument shapes in `adapters/garmin_mcp/mapping.py`; do not guess names or persist diagnostic output containing health data. The task is complete only when each mapped tool is covered by a fixture-backed adapter test.

- [ ] **Step 2: Write adapter tests against a fake session.**

Define a fake session that returns the three committed JSON fixtures. Test that the adapter maps required IDs, timestamps, local dates, durations, and metric values; rejects a missing required field; closes the session; and maps an MCP exception to a typed adapter error without including payload contents in the error string.

- [ ] **Step 3: Implement the MCP session boundary.**

Wrap the official MCP stdio client in an internal protocol so the rest of the application does not import SDK types:

```python
class McpSession(Protocol):
    async def call_tool(self, name: str, arguments: Mapping[str, object]) -> Mapping[str, object]: ...
    async def close(self) -> None: ...


class StdioMcpSessionFactory:
    def __init__(self, command: str, token_dir: Path, timeout_seconds: int) -> None: ...

    async def open(self) -> McpSession: ...
```

Start the child process with the configured token directory and inherited environment. Enforce the configured timeout around each tool call. Close the process in an async context manager and terminate it if graceful close fails.

- [ ] **Step 4: Implement mapping and `GarminMcpAdapter`.**

`GarminMcpAdapter` receives a session factory and exposes the three `GarminDataSource` methods. Keep tool names and payload parsing in `mapping.py`; keep no MCP response object in domain models. Convert source timestamps to timezone-aware `datetime`, retain Garmin-local dates, and raise `GarminDataError` for malformed required fields. Never log full tool arguments or responses.

- [ ] **Step 5: Run focused adapter tests and commit.**

Run `docker compose run --rm app uv run pytest tests/test_garmin_mcp_adapter.py -q`. Expected: PASS. Commit with `git commit -m "feat: add Garmin MCP stdio adapter"`.

## Task 4: Implement the SQLite adapter behind storage ports

**Files:**
- Create: `../../../src/garmin_dashboard/adapters/sqlite/connection.py`
- Create: `../../../src/garmin_dashboard/adapters/sqlite/schema.py`
- Create: `../../../src/garmin_dashboard/adapters/sqlite/activity_store.py`
- Create: `../../../src/garmin_dashboard/adapters/sqlite/sleep_store.py`
- Create: `../../../src/garmin_dashboard/adapters/sqlite/recovery_store.py`
- Create: `../../../src/garmin_dashboard/adapters/sqlite/planning_store.py`
- Create: `../../../src/garmin_dashboard/adapters/sqlite/sync_store.py`
- Create: `tests/contracts/test_storage_contract.py`
- Create: `tests/test_sqlite_stores.py`

**Interfaces:**
- Consumes: domain models and storage ports from Task 2.
- Produces: SQLite implementations with atomic batch/cursor behavior.

- [ ] **Step 1: Write storage contract tests.**

The contract must verify: empty store has no cursor; an upsert inserts records and advances the cursor atomically; repeating the same batch does not duplicate records; date-range queries return deterministic order; an exception rolls back both records and cursor; and separate data families have independent cursors.

- [ ] **Step 2: Implement connection and schema migrations.**

Use stdlib `sqlite3`, `sqlite3.Row`, `PRAGMA foreign_keys = ON`, `PRAGMA journal_mode = WAL`, and a bounded busy timeout. Create a schema-version table and migrations for `activities`, `sleep_sessions`, `recovery_signals`, `sync_cursors`, `sync_runs`, `goals`, `plans`, and `plan_workouts`. Store timestamps as UTC ISO-8601 text and dates as ISO-8601 text; store metric values as numeric columns.

- [ ] **Step 3: Implement stores with transaction boundaries.**

Each `upsert_batch(records, cursor)` must use one transaction:

```python
with connection:
    for record in records:
        connection.execute(upsert_sql, record_values(record))
    connection.execute(cursor_upsert_sql, cursor_values(cursor))
```

Use Garmin IDs as unique keys. Never advance a cursor before its records are durable. Keep SQL in adapter modules and return domain models from all read methods.

- [ ] **Step 4: Run the contract against SQLite.**

Instantiate the contract with a temporary database path and run `docker compose run --rm app uv run pytest tests/contracts/test_storage_contract.py tests/test_sqlite_stores.py -q`. Expected: PASS. The contract must be written so a future filesystem store can be added as another fixture without changing assertions.

- [ ] **Step 5: Commit the storage adapter.**

Stage only SQLite adapter and storage tests. Commit with `git commit -m "feat: add transactional SQLite storage adapter"`.

## Task 5: Implement synchronization and scheduler orchestration

**Files:**
- Create: `../../../src/garmin_dashboard/application/sync.py`
- Create: `../../../src/garmin_dashboard/adapters/sqlite/sync_store.py` implementation additions if needed
- Create: `../../../src/garmin_dashboard/worker.py`
- Create: `tests/test_sync.py`

**Interfaces:**
- Consumes: `GarminDataSource`, the three data-family stores, `SyncRunStore`, `Settings`, and `SyncWindow`.
- Produces: `SyncService.run(window) -> SyncRun` and a scheduler entrypoint that exits non-zero on run failure.

- [ ] **Step 1: Write failing orchestration tests.**

Use fake source and in-memory port implementations. Test first-run import, cursor-based incremental windows, idempotent rerun, independent activity/sleep/recovery progress, auth failure, malformed response, and preservation of existing plans. Assert that a failed family does not advance its cursor and that diagnostics contain only stage/error code/counts.

- [ ] **Step 2: Implement `SyncService`.**

Use this stable interface:

```python
class SyncService:
    def __init__(
        self,
        source: GarminDataSource,
        activities: ActivityStore,
        sleep: SleepStore,
        recovery: RecoveryStore,
        runs: SyncRunStore,
        clock: Callable[[], datetime],
    ) -> None: ...

    async def run(self, window: SyncWindow) -> SyncRun: ...
```

For each data family, read its cursor, fetch through the source, call the family store’s atomic upsert, and record a redacted stage result. Catch only typed adapter/storage errors; let programming errors fail loudly. Do not implement an unbounded retry loop.

- [ ] **Step 3: Wire the worker with dependency injection.**

`worker.py` loads `Settings`, opens SQLite, creates the MCP session factory and adapter, builds `SyncService`, computes an explicit nightly window, and runs one async sync. Keep all concrete construction in `build_sync_service(settings)` so tests can replace every adapter.

- [ ] **Step 4: Run sync tests and commit.**

Run `docker compose run --rm app uv run pytest tests/test_sync.py -q`. Expected: PASS. Commit with `git commit -m "feat: add Garmin incremental sync workflow"`.

## Task 6: Add metrics and race-block analysis

**Files:**
- Create: `../../../src/garmin_dashboard/application/metrics.py`
- Create: `../../../src/garmin_dashboard/application/race_analysis.py`
- Create: `tests/test_metrics.py`

**Interfaces:**
- Consumes: domain records through storage ports.
- Produces: pure metric functions and structured race-analysis inputs.

- [ ] **Step 1: Write fixture-backed metric tests.**

Test daily and aggregate volume, duration, elevation, sport mix, rolling load, trend direction, sleep context, recovery context, and explicit missing-data status. Test race-block selection by choosing the bounded training period before an outcome activity. Assert that metrics never replace missing sleep/recovery with zero or a healthy default.

- [ ] **Step 2: Implement pure calculations.**

Keep functions deterministic and independent of storage:

```python
def summarize_training(activities: Sequence[Activity], start: date, end: date) -> TrainingSummary: ...


def summarize_health(
    sleep: Sequence[SleepSession],
    recovery: Sequence[RecoverySignal],
    start: date,
    end: date,
) -> HealthSummary: ...


def select_preceding_block(
    activities: Sequence[Activity], outcome: Activity, weeks: int
) -> TrainingBlock: ...
```

Return typed values with `available: bool` or an explicit status object where source data is absent. Do not add provider-specific logic to these functions.

- [ ] **Step 3: Run tests and commit.**

Run `docker compose run --rm app uv run pytest tests/test_metrics.py -q`. Expected: PASS. Commit with `git commit -m "feat: calculate training and recovery summaries"`.

## Task 7: Add goals, plan validation, and the coach port

**Files:**
- Modify: `../../../src/garmin_dashboard/domain/plan_models.py`
- Create: `../../../src/garmin_dashboard/application/planning.py`
- Create: `../../../src/garmin_dashboard/ports/coach.py`
- Create: `tests/test_planning.py`

**Interfaces:**
- Consumes: metric summaries, goals, constraints, and `CoachProvider`.
- Produces: validated `PlanProposal` objects and unchanged-plan failure behavior.

- [ ] **Step 1: Write plan-validation tests.**

Test valid plans, malformed provider responses, duration/time-budget violations, unavailable-day violations, explicit user constraints, accept/edit/skip behavior, and preservation of the current plan when validation fails. Test that health data is passed as context and never converted into medical advice.

- [ ] **Step 2: Implement typed plan models and validator.**

Use Pydantic `BaseModel` throughout the domain, application, provider, and API boundaries. Define `PlanConstraints`, `ValidatedPlan`, and `CoachContext` in `domain/plan_models.py`. Provider/API payload models may remain separate from domain models, but all are Pydantic models. The validator interface is:

```python
class PlanValidator:
    def validate(self, proposal: PlanProposal, constraints: PlanConstraints) -> ValidatedPlan: ...


class CoachProvider(Protocol):
    async def propose(self, context: CoachContext) -> PlanProposal: ...
```

Reject unknown workout fields, negative durations, invalid dates, duplicate scheduled days, and explicit constraint violations. No fallback plan is generated when the provider fails.

- [ ] **Step 3: Keep provider selection explicit.**

Wire a provider through `CoachProvider`; do not import a provider SDK into planning or dashboard code. Until a concrete provider is selected, use a test fake only and expose the coach as unavailable in production rather than silently selecting a provider or returning a fabricated plan. Record the selected provider and key configuration only through redacted health metadata.

- [ ] **Step 4: Run planning tests and commit.**

Run `docker compose run --rm app uv run pytest tests/test_planning.py -q`. Expected: PASS. Commit with `git commit -m "feat: validate editable training plans"`.

## Task 8: Add application API and provisional dashboard delivery

**Files:**
- Create: `../../../src/garmin_dashboard/application/dashboard.py`
- Create: `../../../src/garmin_dashboard/api/app.py`
- Create: `../../../src/garmin_dashboard/api/dependencies.py`
- Create: `../../../src/garmin_dashboard/api/routes_dashboard.py`
- Create: `../../../src/garmin_dashboard/api/routes_dev.py`
- Create: `tests/test_api.py`

**Interfaces:**
- Consumes: application services and ports through constructor-injected dependencies.
- Produces: dashboard read models and the predefined read-only inspection endpoints.

- [ ] **Step 1: Write API tests.**

Use fake application services and FastAPI’s test client. Test dashboard data includes fitness, activity, sleep, recovery, goals, plans, and missing-data status. Test the six inspection endpoints, read-only behavior, redaction of secret fields, and rejection of arbitrary SQL/MCP requests.

- [ ] **Step 2: Implement dashboard query service.**

Define a read-only service:

```python
class DashboardService:
    def __init__(self, activities: ActivityStore, sleep: SleepStore, recovery: RecoveryStore, ...): ...

    def current(self, today: date) -> DashboardSnapshot: ...
    def trends(self, start: date, end: date, bucket: TrendBucket) -> TrendSnapshot: ...
```

Return API DTOs from domain/application models. Keep query composition out of route functions.

- [ ] **Step 3: Implement routes and dependency wiring.**

Create `GET /api/dashboard`, `GET /api/dashboard/trends`, and the approved `/api/dev/*` endpoints. Routes may call services but may not execute SQL, call MCP, or expose raw exception text. `api.app` builds the dependency graph once through a composition-root function.

- [ ] **Step 4: Add the provisional dashboard shell.**

Serve one intentionally minimal page that renders current fitness, sleep/recovery availability, goal, weekly plan, and recent activities from the API. Keep markup and styling isolated so a later dashboard redesign changes templates/static assets without touching domain, storage, or sync modules.

- [ ] **Step 5: Run API tests and commit.**

Run `docker compose run --rm app uv run pytest tests/test_api.py -q`. Expected: PASS. Commit with `git commit -m "feat: add dashboard and inspection API"`.

## Task 9: Add backups, health reporting, and Garmin bootstrap operations

**Files:**
- Create: `../../../src/garmin_dashboard/adapters/sqlite/backup.py`
- Create: `../../../src/garmin_dashboard/application/operations.py`
- Create: `scripts/garmin-auth.sh`
- Create: `tests/test_operations.py`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: `Settings`, SQLite connection, `BackupStore`, and sync/health stores.
- Produces: compressed backup operation, redacted health summaries, and documented bootstrap workflow.

- [ ] **Step 1: Write backup and health tests.**

Test that a backup is created atomically, compressed, retained according to explicit count/age settings, and reported as failed when the destination cannot be written. Test storage health reports database size, backup size, disk status, and backup freshness without exposing paths containing credentials.

- [ ] **Step 2: Implement backup and operations services.**

Use SQLite’s backup API into a temporary file, compress the completed file, then atomically rename it into the backup directory. Delete only backups that match the configured retention rule. Report backup failure separately from database health.

- [ ] **Step 3: Add the interactive authentication script.**

Create `scripts/garmin-auth.sh` with `set -euo pipefail`, validate that `GARMIN_EMAIL` and `GARMIN_PASSWORD` are present without echoing them, and execute:

```bash
uvx --python 3.14 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth
```

Mount the same token directory used by Compose. Do not run this script from the nightly scheduler.

- [ ] **Step 4: Document setup and operational checks.**

README must document: copying a local env file, running the auth bootstrap with MFA, starting Compose, checking `/api/dev/garmin/health`, triggering a manual sync, restoring the SQLite backup, and keeping the token volume protected. `AGENTS.md` must document Docker-first commands and the no-secret-output rule.

- [ ] **Step 5: Run operations tests and commit.**

Run `docker compose run --rm app uv run pytest tests/test_operations.py -q`. Expected: PASS. Commit with `git commit -m "feat: add backups and Garmin operations"`.

## Task 10: Run full verification and finish the MVP branch

**Files:**
- Modify only files required by failing checks.

- [ ] **Step 1: Run the complete test suite.**

Run `docker compose run --rm app uv run pytest -q`. Expected: all tests pass, including contract tests, fixture tests, API tests, and operation tests.

- [ ] **Step 2: Run formatting, lint, and type checks.**

Run each command separately:

```bash
docker compose run --rm app uv run ruff format --check .
docker compose run --rm app uv run ruff check .
docker compose run --rm app uv run ty check .
```

Expected: each command exits 0. Fix errors in the responsible module; do not weaken the rule set or add blanket ignores.

- [ ] **Step 3: Run deployment checks.**

Run:

```bash
docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose down
```

Expected: both app and scheduler start, no MCP HTTP service exists, the app port is loopback-bound, and shutdown preserves named volumes.

- [ ] **Step 4: Run security and scope checks.**

Run `rtk rg -n "Strava|strava|GARMIN_PASSWORD|GARMIN_EMAIL|SecretStr|raw MCP|arbitrary SQL" src tests README.md AGENTS.md pyproject.toml`. Confirm no source behavior references the removed provider, secret values are never printed, and diagnostics do not expose raw payloads. Run `rtk git diff --check`.

- [ ] **Step 5: Commit the verified MVP slice.**

Stage only intended source, test, configuration, and documentation files. Commit with `git commit -m "feat: deliver Garmin training dashboard MVP"`.

## Self-review checklist

- Garmin authentication, token persistence, stdio MCP lifecycle, tool mapping, and failure behavior are covered by Tasks 1, 3, and 5.
- Activities, sleep, recovery, timestamps, missing-data semantics, metrics, and race analysis are covered by Tasks 2, 3, 5, and 6.
- SQLite storage, atomic cursors, backups, storage health, and a future filesystem adapter contract are covered by Tasks 2, 4, and 9.
- SOLID boundaries are enforced by domain/ports/application/adapters split and composition-root wiring in Tasks 2, 5, and 8.
- Goals, plans, coach validation, secret redaction, and unchanged-plan failures are covered by Tasks 2, 7, and 8.
- Dashboard delivery is intentionally provisional and isolated in Task 8.
- No task relies on an unspecified default fallback; unavailable authentication, provider, data, and backup states are explicit failures.
