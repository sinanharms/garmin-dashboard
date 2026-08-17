from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import SecretStr

from garmin_dashboard.adapters.sqlite.activity_store import SQLiteActivityStore
from garmin_dashboard.adapters.sqlite.backup import SQLiteBackupStore
from garmin_dashboard.adapters.sqlite.connection import open_connection
from garmin_dashboard.application.operations import OperationsService
from garmin_dashboard.config import Settings
from garmin_dashboard.domain.models import Activity, ActivityCursor

BASE = datetime(2026, 8, 17, tzinfo=UTC)


def _settings(tmp_path: Path) -> Settings:
    return Settings.model_construct(
        garmin_email="athlete@example.test",
        garmin_password=SecretStr("not-a-real-password"),
        garmin_token_dir=tmp_path / "tokens",
        database_path=tmp_path / "dashboard.sqlite3",
        backup_dir=tmp_path / "backups",
        garmin_mcp_command="garmin-mcp",
        mcp_timeout_seconds=30,
        backup_retention_count=20,
        backup_retention_days=30,
    )


def _activity(index: int) -> Activity:
    started_at = BASE + timedelta(seconds=index)
    return Activity(
        external_id=f"activity-{index}",
        activity_type="running",
        started_at=started_at,
        local_date=started_at.date(),
        duration_seconds=60,
        distance_meters=500.0,
        elevation_meters=5.0,
        average_heart_rate=140.0,
        max_heart_rate=155.0,
        calories=50.0,
    )


def test_shared_connection_serializes_concurrent_reads_writes_backup_and_health(tmp_path: Path) -> None:
    connection = open_connection(tmp_path / "dashboard.sqlite3")
    activities = SQLiteActivityStore(connection)
    backups = SQLiteBackupStore(connection, tmp_path / "backups", 20, 30, lambda: BASE)
    operations = OperationsService(_settings(tmp_path), connection, backups, lambda: BASE)

    def write(index: int) -> int:
        record = _activity(index)
        cursor = ActivityCursor(watermark=record.started_at)
        return activities.upsert_batch((record,), cursor)

    def read(_index: int) -> int:
        return len(activities.between(BASE - timedelta(seconds=1), BASE + timedelta(seconds=100)))

    def health(_index: int) -> str:
        return operations.health().database.status

    def backup(_index: int) -> str:
        return backups.create()

    jobs: list[tuple[Callable[[int], int | str], int]] = (
        [(write, index) for index in range(32)]
        + [(read, index) for index in range(32)]
        + [(health, index) for index in range(16)]
        + [(backup, index) for index in range(4)]
    )
    with ThreadPoolExecutor(max_workers=16) as executor:
        results = [executor.submit(function, index) for function, index in jobs]
        values = [future.result() for future in results]

    assert values
    assert len(activities.between(BASE - timedelta(seconds=1), BASE + timedelta(seconds=100))) == 32
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    connection.close()
