import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from strava_dashboard.adapters.garmin_mcp.mapping import GarminDataError
from strava_dashboard.application.sync import SyncService
from strava_dashboard.domain.models import (
    Activity,
    ActivityCursor,
    RecoveryCursor,
    RecoverySignal,
    SleepCursor,
    SleepSession,
    SyncRun,
    SyncWindow,
)
from strava_dashboard.ports.storage import StorageError

BASE = datetime(2026, 8, 16, 6, tzinfo=UTC)


def activity(number: int) -> Activity:
    return Activity(
        external_id=f"activity-{number}",
        activity_type="running",
        started_at=BASE + timedelta(hours=number),
        local_date=(BASE + timedelta(hours=number)).date(),
        duration_seconds=1800,
        distance_meters=5000.0,
        elevation_meters=40.0,
        average_heart_rate=145.0,
        max_heart_rate=165.0,
        calories=350.0,
    )


def sleep(number: int) -> SleepSession:
    started = BASE + timedelta(days=number)
    return SleepSession(
        external_id=f"sleep-{number}",
        started_at=started,
        ended_at=started + timedelta(hours=8),
        local_date=started.date(),
        duration_seconds=28800,
        score=85.0,
    )


def recovery(number: int) -> RecoverySignal:
    measured = BASE + timedelta(days=number)
    return RecoverySignal(
        external_id=f"recovery-{number}",
        local_date=measured.date(),
        measured_at=measured,
        metric_name="last_night_avg_hrv_ms",
        value=48.0,
        unit="ms",
    )


class FakeSource:
    def __init__(self) -> None:
        self.calls: list[tuple[str, SyncWindow]] = []
        self.responses: dict[str, Sequence[Any]] = {
            "activities": (activity(1),),
            "sleep": (sleep(0),),
            "recovery": (recovery(0),),
        }
        self.errors: dict[str, BaseException] = {}

    async def fetch_activities(self, window: SyncWindow) -> Sequence[Activity]:
        return cast(Sequence[Activity], await self._fetch("activities", window))

    async def fetch_sleep(self, window: SyncWindow) -> Sequence[SleepSession]:
        return cast(Sequence[SleepSession], await self._fetch("sleep", window))

    async def fetch_recovery(self, window: SyncWindow) -> Sequence[RecoverySignal]:
        return cast(Sequence[RecoverySignal], await self._fetch("recovery", window))

    async def _fetch(self, family: str, window: SyncWindow) -> Sequence[Any]:
        self.calls.append((family, window))
        if family in self.errors:
            raise self.errors[family]
        return self.responses[family]


class MemoryFamilyStore:
    def __init__(self, family: str) -> None:
        self.family = family
        self.saved: list[Any] = []
        self.saved_cursors: list[Any] = []
        self.current_cursor: Any = None
        self.error: BaseException | None = None

    def cursor(self) -> Any:
        return self.current_cursor

    def upsert_batch(self, records: Sequence[Any], cursor: Any) -> int:
        if self.error is not None:
            raise self.error
        self.saved.extend(records)
        self.saved_cursors.append(cursor)
        self.current_cursor = cursor
        return len(records)

    def between(self, start: datetime, end: datetime) -> Sequence[Any]:
        return tuple(self.saved)


class MemoryRuns:
    def __init__(self) -> None:
        self.saved: list[SyncRun] = []

    def save(self, run: SyncRun) -> None:
        self.saved.append(run)

    def get(self, run_id: str) -> SyncRun | None:
        return next((run for run in self.saved if run.run_id == run_id), None)

    def recent(self, limit: int) -> Sequence[SyncRun]:
        return tuple(self.saved[-limit:])


class Clock:
    def __init__(self) -> None:
        self.value = BASE

    def __call__(self) -> datetime:
        current = self.value
        self.value += timedelta(seconds=1)
        return current


def window() -> SyncWindow:
    return SyncWindow(start=BASE, end=BASE + timedelta(days=2))


def service(
    source: FakeSource,
    activities: MemoryFamilyStore,
    sleep_store: MemoryFamilyStore,
    recovery_store: MemoryFamilyStore,
    runs: MemoryRuns,
) -> SyncService:
    return SyncService(source, activities, sleep_store, recovery_store, runs, Clock())


def test_first_import_advances_each_family_and_records_redacted_counts() -> None:
    source = FakeSource()
    stores = (MemoryFamilyStore("activities"), MemoryFamilyStore("sleep"), MemoryFamilyStore("recovery"))
    runs = MemoryRuns()

    result = asyncio.run(service(source, *stores, runs).run(window()))

    assert [stage.data_family for stage in result.stages] == ["activities", "sleep", "recovery"]
    assert all(stage.status == "succeeded" for stage in result.stages)
    assert [stage.record_count for stage in result.stages] == [1, 1, 1]
    assert all(stage.error_code is None for stage in result.stages)
    assert all("secret" not in repr(stage) for stage in result.stages)
    assert all(store.current_cursor is not None for store in stores)


def test_cursor_based_incremental_windows_are_independent() -> None:
    source = FakeSource()
    activities = MemoryFamilyStore("activities")
    sleep_store = MemoryFamilyStore("sleep")
    recovery_store = MemoryFamilyStore("recovery")
    activities.current_cursor = ActivityCursor(watermark=BASE + timedelta(hours=6))
    sleep_store.current_cursor = SleepCursor(watermark=BASE + timedelta(hours=12))
    recovery_store.current_cursor = RecoveryCursor(watermark=BASE + timedelta(hours=18))

    asyncio.run(service(source, activities, sleep_store, recovery_store, MemoryRuns()).run(window()))

    assert [call[1].start for call in source.calls] == [
        BASE + timedelta(hours=6),
        BASE + timedelta(hours=12),
        BASE + timedelta(hours=18),
    ]


def test_idempotent_rerun_updates_same_records_without_duplicates() -> None:
    source = FakeSource()
    stores = (MemoryFamilyStore("activities"), MemoryFamilyStore("sleep"), MemoryFamilyStore("recovery"))
    runs = MemoryRuns()
    sync = service(source, *stores, runs)

    asyncio.run(sync.run(window()))
    asyncio.run(sync.run(window()))

    assert [len(store.saved) for store in stores] == [1, 1, 1]
    assert all(len(store.saved_cursors) == 1 for store in stores)


def test_failed_family_does_not_advance_cursor_or_block_other_families() -> None:
    source = FakeSource()
    source.errors["sleep"] = GarminDataError("RAW-HEALTH-SECRET")
    activities = MemoryFamilyStore("activities")
    sleep_store = MemoryFamilyStore("sleep")
    recovery_store = MemoryFamilyStore("recovery")
    runs = MemoryRuns()

    result = asyncio.run(service(source, activities, sleep_store, recovery_store, runs).run(window()))

    assert result.stages[0].status == "succeeded"
    assert result.stages[1].status == "failed"
    assert result.stages[1].error_code == "garmin_source_error"
    assert result.stages[1].record_count == 0
    assert sleep_store.current_cursor is None
    assert recovery_store.current_cursor is not None
    assert "RAW-HEALTH-SECRET" not in repr(result)
    assert runs.get(result.run_id) == result


def test_storage_failure_is_redacted_and_cursor_is_preserved() -> None:
    source = FakeSource()
    activities = MemoryFamilyStore("activities")
    activities.error = StorageError("/secret/database/path")
    sleep_store = MemoryFamilyStore("sleep")
    recovery_store = MemoryFamilyStore("recovery")

    result = asyncio.run(service(source, activities, sleep_store, recovery_store, MemoryRuns()).run(window()))

    assert result.stages[0].error_code == "storage_error"
    assert activities.current_cursor is None
    assert "/secret" not in repr(result)


def test_unknown_programming_errors_are_not_silently_caught() -> None:
    source = FakeSource()
    source.errors["activities"] = ValueError("programming bug")

    with pytest.raises(ValueError, match="programming bug"):
        asyncio.run(
            service(
                source, MemoryFamilyStore("activities"), MemoryFamilyStore("sleep"), MemoryFamilyStore("recovery"), MemoryRuns()
            ).run(window())
        )


def test_existing_plans_are_not_touched_by_sync() -> None:
    source = FakeSource()
    stores = (MemoryFamilyStore("activities"), MemoryFamilyStore("sleep"), MemoryFamilyStore("recovery"))
    runs = MemoryRuns()
    sentinel = SyncRun(
        run_id="existing-plan-sentinel",
        started_at=BASE,
        ended_at=BASE + timedelta(seconds=1),
        stages=(),
    )
    runs.saved.append(sentinel)

    asyncio.run(service(source, *stores, runs).run(window()))

    assert runs.saved[0] == sentinel
