import shutil
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from garmin_dashboard.application.metrics import summarize_health, summarize_training, summarize_trends
from garmin_dashboard.domain.models import Activity, HealthSummary, SyncRun, TrainingSummary, TrendBucket, TrendSnapshot
from garmin_dashboard.domain.plan_models import Goal, ValidatedPlan
from garmin_dashboard.ports.storage import (
    ActivityStore,
    GoalStore,
    PlanStore,
    RecoveryStore,
    SleepStore,
    SyncRunStore,
)

Status = Literal["ok", "degraded", "unavailable"]


class ReadModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DashboardView(ReadModel):
    generated_at: datetime
    training: TrainingSummary
    health: HealthSummary
    health_status: Literal["available", "missing"]
    goal: Goal | None
    plan: ValidatedPlan | None
    recent_activities: tuple[Activity, ...]


class HealthReport(ReadModel):
    status: Status
    detail: str | None


class GarminHealth(ReadModel):
    status: Status
    authenticated: bool
    last_mcp_check: datetime | None
    last_sync: SyncRun | None


class SyncRunList(ReadModel):
    runs: tuple[SyncRun, ...]


class SyncRunDetail(ReadModel):
    run: SyncRun
    failure_detail: str | None


class StorageHealth(ReadModel):
    status: Status
    database_size_bytes: int | None
    backup_size_bytes: int | None
    disk_available_bytes: int | None


class CoachHealth(ReadModel):
    status: Status
    last_call_status: str | None
    schema_validation_failures: int


class InspectionService(Protocol):
    def health(self) -> HealthReport: ...

    def garmin_health(self) -> GarminHealth: ...

    def recent_sync_runs(self, limit: int) -> SyncRunList: ...

    def sync_run(self, run_id: str) -> SyncRunDetail | None: ...

    def storage_health(self) -> StorageHealth: ...

    def coach_health(self) -> CoachHealth: ...


class DashboardService:
    def __init__(
        self,
        activities: ActivityStore,
        sleep: SleepStore,
        recovery: RecoveryStore,
        goals: GoalStore,
        plans: PlanStore,
        clock: Callable[[], datetime],
    ) -> None:
        self._activities = activities
        self._sleep = sleep
        self._recovery = recovery
        self._goals = goals
        self._plans = plans
        self._clock = clock

    def current(self, today: date) -> DashboardView:
        start = today - timedelta(days=7)
        end = today + timedelta(days=1)
        activities, sleep, recovery = self._records(start, end)
        training = summarize_training(activities, start, end)
        health = summarize_health(sleep, recovery, start, end)
        return DashboardView(
            generated_at=self._clock(),
            training=training,
            health=health,
            health_status="available" if health.available else "missing",
            goal=self._goals.current(),
            plan=self._plans.current(),
            recent_activities=tuple(
                sorted(activities, key=lambda item: (item.started_at, item.external_id), reverse=True)[:10]
            ),
        )

    def trends(self, start: date, end: date, bucket: TrendBucket) -> TrendSnapshot:
        activities, sleep, recovery = self._records(start, end)
        return summarize_trends(activities, sleep, recovery, start, end, bucket)

    def _records(self, start: date, end: date) -> tuple[tuple[Activity, ...], tuple, tuple]:
        start_at = datetime.combine(start, time.min, tzinfo=UTC)
        end_at = datetime.combine(end, time.min, tzinfo=UTC)
        return (
            tuple(self._activities.between(start_at, end_at)),
            tuple(self._sleep.between(start_at, end_at)),
            tuple(self._recovery.between(start_at, end_at)),
        )


class SQLiteInspectionService:
    def __init__(self, runs: SyncRunStore, database_path: Path, backup_dir: Path) -> None:
        self._runs = runs
        self._database_path = database_path
        self._backup_dir = backup_dir

    def health(self) -> HealthReport:
        return HealthReport(status="ok", detail=None)

    def garmin_health(self) -> GarminHealth:
        latest = self._runs.recent(1)
        return GarminHealth(
            status="unavailable",
            authenticated=False,
            last_mcp_check=None,
            last_sync=latest[0] if latest else None,
        )

    def recent_sync_runs(self, limit: int) -> SyncRunList:
        return SyncRunList(runs=tuple(self._runs.recent(limit)))

    def sync_run(self, run_id: str) -> SyncRunDetail | None:
        run = self._runs.get(run_id)
        return None if run is None else SyncRunDetail(run=run, failure_detail=None)

    def storage_health(self) -> StorageHealth:
        database_size = self._database_path.stat().st_size if self._database_path.exists() else 0
        backup_size = (
            sum(path.stat().st_size for path in self._backup_dir.glob("*") if path.is_file())
            if self._backup_dir.exists()
            else 0
        )
        disk_available = shutil.disk_usage(self._database_path.parent).free
        return StorageHealth(
            status="ok",
            database_size_bytes=database_size,
            backup_size_bytes=backup_size,
            disk_available_bytes=disk_available,
        )

    def coach_health(self) -> CoachHealth:
        return CoachHealth(status="unavailable", last_call_status=None, schema_validation_failures=0)
