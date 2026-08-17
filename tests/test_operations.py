import gzip
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from garmin_dashboard.adapters.sqlite import backup as backup_module
from garmin_dashboard.adapters.sqlite.backup import SQLiteBackupStore
from garmin_dashboard.adapters.sqlite.connection import SQLiteConnection, open_connection
from garmin_dashboard.application.operations import OperationsService
from garmin_dashboard.config.settings import Settings
from garmin_dashboard.ports.storage import StorageError

NOW = datetime(2026, 8, 17, 12, tzinfo=UTC)


def settings(tmp_path: Path, retention_days: int = 30) -> Settings:
    return Settings.model_construct(
        garmin_email="athlete@example.test",
        garmin_password=SecretStr("not-a-real-password"),
        garmin_token_dir=tmp_path / "tokens",
        database_path=tmp_path / "dashboard.sqlite3",
        backup_dir=tmp_path / "backups",
        garmin_mcp_command="garmin-mcp",
        mcp_timeout_seconds=30,
        backup_retention_count=2,
        backup_retention_days=retention_days,
    )


def create_store(tmp_path: Path, clock=lambda: NOW) -> tuple[SQLiteConnection, SQLiteBackupStore]:
    database = open_connection(tmp_path / "dashboard.sqlite3")
    database.execute("CREATE TABLE IF NOT EXISTS sentinel (value TEXT NOT NULL)")
    database.execute("INSERT INTO sentinel(value) VALUES ('preserve-me')")
    database.commit()
    store = SQLiteBackupStore(database, tmp_path / "backups", retention_count=2, retention_days=30, clock=clock)
    return database, store


def test_backup_is_gzip_and_replaced_atomically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database, store = create_store(tmp_path)
    replacements: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def record_replace(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
        replacements.append((Path(source), Path(target)))
        real_replace(source, target)

    monkeypatch.setattr(backup_module.os, "replace", record_replace)

    backup_id = store.create()

    backup_path = tmp_path / "backups" / backup_id
    assert backup_path.suffixes == [".sqlite3", ".gz"]
    assert replacements == [(replacements[0][0], backup_path)]
    assert replacements[0][0].name.startswith(f".{backup_id}.")
    assert not tuple((tmp_path / "backups").glob("*.tmp"))
    restored_path = tmp_path / "restored.sqlite3"
    with gzip.open(backup_path, "rb") as compressed, restored_path.open("wb") as restored_file:
        restored_file.write(compressed.read())
    restored = sqlite3.connect(restored_path)
    assert restored.execute("SELECT value FROM sentinel").fetchone()[0] == "preserve-me"
    restored.close()
    database.close()


def test_backup_retention_deletes_only_expired_or_excess_backups(tmp_path: Path) -> None:
    database, store = create_store(tmp_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    old = backup_dir / "dashboard-20260801T120000Z-11111111.sqlite3.gz"
    extra = backup_dir / "dashboard-20260815T120000Z-22222222.sqlite3.gz"
    unrelated = backup_dir / "old.sqlite3.gz"
    old.write_bytes(b"old")
    extra.write_bytes(b"extra")
    unrelated.write_bytes(b"keep")
    os.utime(old, (NOW.timestamp() - 31 * 86400, NOW.timestamp() - 31 * 86400))
    os.utime(extra, (NOW.timestamp() - 2 * 86400, NOW.timestamp() - 2 * 86400))

    store.create()
    remaining = {path.name for path in backup_dir.glob("*.sqlite3.gz")}

    assert old.name not in remaining
    assert extra.name in remaining
    assert unrelated.name in remaining
    assert len(remaining) == 3
    database.close()


def test_backup_rejects_traversal_and_symlink_targets(tmp_path: Path) -> None:
    database, store = create_store(tmp_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    valid_id = "dashboard-20260817T120000Z-12345678.sqlite3.gz"
    target = tmp_path / "outside.sqlite3.gz"
    target.write_bytes(b"not a backup")
    (backup_dir / valid_id).symlink_to(target)

    for backup_id in ("../outside.sqlite3.gz", valid_id):
        with pytest.raises(StorageError, match="invalid backup identifier"):
            store.restore(backup_id)
        with pytest.raises(StorageError, match="invalid backup identifier"):
            store.delete(backup_id)

    store.create()
    assert (backup_dir / valid_id).is_symlink()
    database.close()


def test_health_handles_backup_stat_race_without_raising(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database, store = create_store(tmp_path)
    backup_id = store.create()
    service = OperationsService(settings(tmp_path), database, store, clock=lambda: NOW)
    original_stat = Path.stat

    def race(path: Path, *args, **kwargs):
        if path.name == backup_id:
            raise OSError("backup disappeared")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", race)

    report = service.health()

    assert report.status == "unavailable"
    assert report.backup.status == "unavailable"
    assert report.freshness.status == "unavailable"
    database.close()


def test_backup_failure_is_typed_and_redacted(tmp_path: Path) -> None:
    database = open_connection(tmp_path / "dashboard.sqlite3")
    destination = tmp_path / "credential-secret"
    destination.write_text("not a directory")
    store = SQLiteBackupStore(database, destination, retention_count=2, retention_days=30, clock=lambda: NOW)

    with pytest.raises(StorageError, match="SQLite backup failed") as error:
        store.create()

    assert str(destination) not in str(error.value)
    database.close()


def test_operations_health_reports_components_and_redacts_paths(tmp_path: Path) -> None:
    database, store = create_store(tmp_path)
    store.create()
    service = OperationsService(settings(tmp_path), database, store, clock=lambda: NOW)

    report = service.health()

    assert report.status == "ok"
    assert report.database.status == "ok"
    assert report.database.size_bytes is not None
    assert report.backup.status == "ok"
    assert report.backup.size_bytes is not None
    assert report.disk.status == "ok"
    assert report.disk.available_bytes is not None
    assert report.freshness.status == "ok"
    assert "credential-secret" not in repr(report)
    database.close()


def test_backup_failure_is_separate_from_database_health(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database, store = create_store(tmp_path)
    service = OperationsService(settings(tmp_path), database, store, clock=lambda: NOW)

    def fail() -> str:
        raise StorageError("path=/private/password-token")

    monkeypatch.setattr(store, "create", fail)
    result = service.backup()
    report = service.health()

    assert result.status == "failed"
    assert result.backup_id is None
    assert result.failure_code == "backup_failed"
    assert report.database.status == "ok"
    assert report.backup.status == "degraded"
    assert report.backup.failure_code == "backup_failed"
    assert "/private/password-token" not in repr(report)
    database.close()


def test_stale_backup_is_reported_without_hiding_database_health(tmp_path: Path) -> None:
    database, store = create_store(tmp_path)
    backup_id = store.create()
    backup_path = tmp_path / "backups" / backup_id
    old_timestamp = (NOW - timedelta(days=2)).timestamp()
    os.utime(backup_path, (old_timestamp, old_timestamp))
    service = OperationsService(settings(tmp_path, retention_days=1), database, store, clock=lambda: NOW)

    report = service.health()

    assert report.database.status == "ok"
    assert report.backup.status == "ok"
    assert report.freshness.status == "degraded"
    assert report.freshness.latest_at is not None
    database.close()


def test_operation_models_reject_extra_fields_and_are_immutable(tmp_path: Path) -> None:
    database, store = create_store(tmp_path)
    report = OperationsService(settings(tmp_path), database, store, clock=lambda: NOW).health()

    with pytest.raises(ValidationError):
        report.__class__.model_validate({**report.model_dump(), "extra_field": "rejected"})
    with pytest.raises(ValidationError):
        report.status = "degraded"  # type: ignore
    database.close()


def test_auth_script_has_strict_mode_and_exact_command() -> None:
    script = Path("scripts/garmin-auth.sh").read_text()

    assert "set -euo pipefail" in script
    assert '[[ -n "${GARMIN_EMAIL:-}" ]]' in script
    assert '[[ -n "${GARMIN_PASSWORD:-}" ]]' in script
    assert "uvx --python 3.14 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth" in script
