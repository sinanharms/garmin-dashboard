from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol, cast

import pytest

from strava_dashboard.domain.models import (
    Activity,
    ActivityCursor,
    RecoveryCursor,
    RecoverySignal,
    SleepCursor,
    SleepSession,
)
from strava_dashboard.ports.storage import ActivityStore, RecoveryStore, SleepStore


class StorageBundle(Protocol):
    activity: ActivityStore
    sleep: SleepStore
    recovery: RecoveryStore


StorageFactory = Callable[[Path], AbstractContextManager[StorageBundle]]


class FailingCursor:
    @property
    def watermark(self) -> datetime:
        raise RuntimeError("injected cursor failure")


def _activity(identifier: str, started_at: datetime) -> Activity:
    return Activity(
        external_id=identifier,
        activity_type="running",
        started_at=started_at,
        local_date=started_at.date(),
        duration_seconds=1800,
        distance_meters=5000.0,
        elevation_meters=30.0,
        average_heart_rate=145.0,
        max_heart_rate=170.0,
        calories=350.0,
    )


def _sleep(identifier: str, started_at: datetime) -> SleepSession:
    return SleepSession(
        external_id=identifier,
        started_at=started_at,
        ended_at=started_at + timedelta(hours=8),
        local_date=started_at.date(),
        duration_seconds=8 * 60 * 60,
        score=82.0,
    )


def _recovery(identifier: str, measured_at: datetime) -> RecoverySignal:
    return RecoverySignal(
        external_id=identifier,
        local_date=measured_at.date(),
        measured_at=measured_at,
        metric_name="body_battery",
        value=75.0,
        unit="percent",
    )


@pytest.fixture
def stores(storage_factory: StorageFactory, tmp_path: Path) -> Iterator[StorageBundle]:
    with storage_factory(tmp_path / "contract.sqlite") as value:
        yield value


def test_empty_store_has_no_cursor(stores: StorageBundle) -> None:
    assert stores.activity.cursor() is None
    assert stores.sleep.cursor() is None
    assert stores.recovery.cursor() is None


def test_activity_upsert_is_idempotent_and_advances_cursor_atomically(stores: StorageBundle) -> None:
    started_at = datetime(2026, 8, 16, 6, 30, tzinfo=UTC)
    record = _activity("a-1", started_at)
    cursor = ActivityCursor(watermark=started_at)

    assert stores.activity.upsert_batch((record,), cursor) == 1
    assert stores.activity.upsert_batch((record,), cursor) == 1

    assert stores.activity.cursor() == cursor
    assert stores.activity.between(started_at, started_at + timedelta(days=1)) == (record,)


@pytest.mark.parametrize("family", ("sleep", "recovery"))
def test_sleep_and_recovery_round_trip_complete_models_and_order(stores: StorageBundle, family: str) -> None:
    start = datetime(2026, 8, 16, tzinfo=UTC)
    if family == "sleep":
        records = (_sleep("s-2", start + timedelta(hours=2)), _sleep("s-1", start + timedelta(hours=1)))
        cursor = SleepCursor(watermark=start + timedelta(hours=2))
        stores.sleep.upsert_batch(records, cursor)
        assert stores.sleep.cursor() == cursor
        assert stores.sleep.between(start, start + timedelta(days=1)) == (records[1], records[0])
    else:
        records = (_recovery("r-2", start + timedelta(hours=2)), _recovery("r-1", start + timedelta(hours=1)))
        cursor = RecoveryCursor(watermark=start + timedelta(hours=2))
        stores.recovery.upsert_batch(records, cursor)
        assert stores.recovery.cursor() == cursor
        assert stores.recovery.between(start, start + timedelta(days=1)) == (records[1], records[0])


@pytest.mark.parametrize("family", ("sleep", "recovery"))
def test_record_and_cursor_rollback_together(stores: StorageBundle, family: str) -> None:
    start = datetime(2026, 8, 16, 6, 30, tzinfo=UTC)
    if family == "sleep":
        record = _sleep("s-1", start)
        failing_cursor = cast(SleepCursor, FailingCursor())
        with pytest.raises(RuntimeError, match="injected cursor failure"):
            stores.sleep.upsert_batch((record,), failing_cursor)
        assert stores.sleep.cursor() is None
        assert stores.sleep.between(start, start + timedelta(days=1)) == ()
    else:
        record = _recovery("r-1", start)
        failing_cursor = cast(RecoveryCursor, FailingCursor())
        with pytest.raises(RuntimeError, match="injected cursor failure"):
            stores.recovery.upsert_batch((record,), failing_cursor)
        assert stores.recovery.cursor() is None
        assert stores.recovery.between(start, start + timedelta(days=1)) == ()


def test_data_families_have_independent_cursors(stores: StorageBundle) -> None:
    moment = datetime(2026, 8, 16, 6, 30, tzinfo=UTC)

    stores.activity.upsert_batch((_activity("a-1", moment),), ActivityCursor(watermark=moment))
    stores.sleep.upsert_batch((_sleep("s-1", moment),), SleepCursor(watermark=moment + timedelta(minutes=1)))
    stores.recovery.upsert_batch((_recovery("r-1", moment),), RecoveryCursor(watermark=moment + timedelta(minutes=2)))

    activity_cursor = stores.activity.cursor()
    sleep_cursor = stores.sleep.cursor()
    recovery_cursor = stores.recovery.cursor()
    assert activity_cursor is not None
    assert sleep_cursor is not None
    assert recovery_cursor is not None
    assert activity_cursor.watermark == moment
    assert sleep_cursor.watermark == moment + timedelta(minutes=1)
    assert recovery_cursor.watermark == moment + timedelta(minutes=2)
