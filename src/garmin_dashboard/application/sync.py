from collections.abc import Callable
from datetime import datetime

from garmin_dashboard.domain.models import (
    ActivityCursor,
    DataFamily,
    RecoveryCursor,
    SleepCursor,
    SyncRun,
    SyncStageResult,
    SyncWindow,
)
from garmin_dashboard.ports.garmin import GarminDataSource, GarminSourceError
from garmin_dashboard.ports.storage import (
    ActivityStore,
    RecoveryStore,
    SleepStore,
    StorageError,
    SyncRunStore,
)


class SyncService:
    def __init__(
        self,
        source: GarminDataSource,
        activities: ActivityStore,
        sleep: SleepStore,
        recovery: RecoveryStore,
        runs: SyncRunStore,
        clock: Callable[[], datetime],
    ) -> None:
        self._source = source
        self._activities = activities
        self._sleep = sleep
        self._recovery = recovery
        self._runs = runs
        self._clock = clock

    async def run(self, window: SyncWindow) -> SyncRun:
        started_at = self._clock()
        stages = (
            await self._sync_activities(window),
            await self._sync_sleep(window),
            await self._sync_recovery(window),
        )
        ended_at = self._clock()
        run = SyncRun(
            run_id=f"sync-{started_at.isoformat()}",
            started_at=started_at,
            ended_at=ended_at,
            stages=stages,
        )
        self._runs.save(run)
        return run

    async def _sync_activities(self, window: SyncWindow) -> SyncStageResult:
        try:
            cursor = self._activities.cursor()
            effective = _effective_window(window, cursor.watermark if cursor else None)
            if effective is None:
                return _success("activities", 0)
            records = await self._source.fetch_activities(effective)
            count = self._activities.upsert_batch(records, ActivityCursor(watermark=window.end))
            return _success("activities", count)
        except (GarminSourceError, StorageError) as error:
            return _failure("activities", _error_code(error))

    async def _sync_sleep(self, window: SyncWindow) -> SyncStageResult:
        try:
            cursor = self._sleep.cursor()
            effective = _effective_window(window, cursor.watermark if cursor else None)
            if effective is None:
                return _success("sleep", 0)
            records = await self._source.fetch_sleep(effective)
            count = self._sleep.upsert_batch(records, SleepCursor(watermark=window.end))
            return _success("sleep", count)
        except (GarminSourceError, StorageError) as error:
            return _failure("sleep", _error_code(error))

    async def _sync_recovery(self, window: SyncWindow) -> SyncStageResult:
        try:
            cursor = self._recovery.cursor()
            effective = _effective_window(window, cursor.watermark if cursor else None)
            if effective is None:
                return _success("recovery", 0)
            records = await self._source.fetch_recovery(effective)
            count = self._recovery.upsert_batch(records, RecoveryCursor(watermark=window.end))
            return _success("recovery", count)
        except (GarminSourceError, StorageError) as error:
            return _failure("recovery", _error_code(error))


def _effective_window(window: SyncWindow, cursor: datetime | None) -> SyncWindow | None:
    start = cursor or window.start
    if start is not None and start >= window.end:
        return None
    return SyncWindow(start=start, end=window.end)


def _success(family: DataFamily, count: int) -> SyncStageResult:
    return SyncStageResult(data_family=family, status="succeeded", record_count=count, error_code=None)


def _failure(family: DataFamily, error_code: str) -> SyncStageResult:
    return SyncStageResult(data_family=family, status="failed", record_count=0, error_code=error_code)


def _error_code(error: GarminSourceError | StorageError) -> str:
    if isinstance(error, GarminSourceError):
        return "garmin_source_error"
    return "storage_error"
