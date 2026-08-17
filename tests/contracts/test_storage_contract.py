import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from strava_dashboard.adapters.sqlite.activity_store import SQLiteActivityStore
from strava_dashboard.adapters.sqlite.connection import open_connection
from strava_dashboard.adapters.sqlite.recovery_store import SQLiteRecoveryStore
from strava_dashboard.adapters.sqlite.sleep_store import SQLiteSleepStore
from strava_dashboard.domain.models import (
    Activity,
    ActivityCursor,
    RecoveryCursor,
    RecoverySignal,
    SleepCursor,
    SleepSession,
)


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
def stores(tmp_path):
    connection = open_connection(tmp_path / "contract.sqlite")
    value = (
        SQLiteActivityStore(connection),
        SQLiteSleepStore(connection),
        SQLiteRecoveryStore(connection),
    )
    yield value
    connection.close()


def test_empty_store_has_no_cursor(stores) -> None:
    activities, sleep, recovery = stores

    assert activities.cursor() is None
    assert sleep.cursor() is None
    assert recovery.cursor() is None


def test_upsert_batch_persists_records_and_advances_cursor_atomically(stores) -> None:
    activities, _, _ = stores
    started_at = datetime(2026, 8, 16, 6, 30, tzinfo=UTC)
    cursor = ActivityCursor(watermark=started_at)

    assert activities.upsert_batch((_activity("a-1", started_at),), cursor) == 1

    assert activities.cursor() == cursor
    assert activities.between(started_at, started_at + timedelta(days=1)) == (_activity("a-1", started_at),)


def test_repeating_batch_is_idempotent(stores) -> None:
    activities, _, _ = stores
    started_at = datetime(2026, 8, 16, 6, 30, tzinfo=UTC)
    record = _activity("a-1", started_at)
    cursor = ActivityCursor(watermark=started_at)

    activities.upsert_batch((record,), cursor)
    activities.upsert_batch((record,), cursor)

    assert activities.between(started_at, started_at + timedelta(days=1)) == (record,)


def test_date_range_query_has_deterministic_order(stores) -> None:
    activities, _, _ = stores
    start = datetime(2026, 8, 16, tzinfo=UTC)
    records = (_activity("a-2", start + timedelta(hours=2)), _activity("a-1", start + timedelta(hours=1)))
    activities.upsert_batch(records, ActivityCursor(watermark=start + timedelta(hours=2)))

    assert activities.between(start, start + timedelta(days=1)) == (records[1], records[0])


def test_exception_rolls_back_records_and_cursor(stores) -> None:
    activities, _, _ = stores
    started_at = datetime(2026, 8, 16, 6, 30, tzinfo=UTC)
    connection = activities.connection
    connection.set_authorizer(
        lambda action, _arg1, _arg2, _database, _source: (
            sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_UPDATE and _arg1 == "sync_cursors" else sqlite3.SQLITE_OK
        )
    )

    with pytest.raises(sqlite3.DatabaseError):
        activities.upsert_batch((_activity("a-1", started_at),), ActivityCursor(watermark=started_at))

    connection.set_authorizer(None)
    assert activities.cursor() is None
    assert activities.between(started_at, started_at + timedelta(days=1)) == ()


def test_data_families_have_independent_cursors(stores) -> None:
    activities, sleep, recovery = stores
    moment = datetime(2026, 8, 16, 6, 30, tzinfo=UTC)

    activities.upsert_batch((_activity("a-1", moment),), ActivityCursor(watermark=moment))
    sleep.upsert_batch((_sleep("s-1", moment),), SleepCursor(watermark=moment + timedelta(minutes=1)))
    recovery.upsert_batch((_recovery("r-1", moment),), RecoveryCursor(watermark=moment + timedelta(minutes=2)))

    assert activities.cursor() is not None
    assert sleep.cursor() is not None
    assert recovery.cursor() is not None
    assert activities.cursor().watermark == moment
    assert sleep.cursor().watermark == moment + timedelta(minutes=1)
    assert recovery.cursor().watermark == moment + timedelta(minutes=2)
