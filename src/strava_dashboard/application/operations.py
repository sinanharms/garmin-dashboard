import shutil
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from strava_dashboard.config import Settings
from strava_dashboard.ports.storage import BackupStore, StorageError

HealthStatus = Literal["ok", "degraded", "unavailable"]
OperationStatus = Literal["succeeded", "failed"]


class OperationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ComponentHealth(OperationModel):
    status: HealthStatus
    detail: str | None = None


class DatabaseHealth(ComponentHealth):
    size_bytes: int | None = None


class BackupHealth(ComponentHealth):
    size_bytes: int | None = None
    failure_code: str | None = None


class DiskHealth(ComponentHealth):
    available_bytes: int | None = None


class FreshnessHealth(ComponentHealth):
    latest_at: datetime | None = None
    age_seconds: int | None = None


class OperationsHealth(OperationModel):
    status: HealthStatus
    database: DatabaseHealth
    backup: BackupHealth
    disk: DiskHealth
    freshness: FreshnessHealth


class BackupOperation(OperationModel):
    status: OperationStatus
    backup_id: str | None = None
    failure_code: str | None = None


class OperationsService:
    def __init__(
        self,
        settings: Settings,
        connection: sqlite3.Connection,
        backup_store: BackupStore,
        clock: Callable[[], datetime],
    ) -> None:
        self._settings = settings
        self._connection = connection
        self._backup_store = backup_store
        self._clock = clock
        self._last_backup_failure: str | None = None

    def backup(self) -> BackupOperation:
        try:
            backup_id = self._backup_store.create()
        except StorageError:
            self._last_backup_failure = "backup_failed"
            return BackupOperation(status="failed", failure_code=self._last_backup_failure)
        self._last_backup_failure = None
        return BackupOperation(status="succeeded", backup_id=backup_id)

    def health(self) -> OperationsHealth:
        database = self._database_health()
        backups, latest = self._backup_files()
        backup = self._backup_health(backups)
        disk = self._disk_health()
        freshness = self._freshness_health(latest)
        status = _overall_status((database.status, backup.status, disk.status, freshness.status))
        return OperationsHealth(status=status, database=database, backup=backup, disk=disk, freshness=freshness)

    def _database_health(self) -> DatabaseHealth:
        try:
            self._connection.execute("SELECT 1").fetchone()
            size = self._settings.database_path.stat().st_size if self._settings.database_path.exists() else 0
            return DatabaseHealth(status="ok", size_bytes=size)
        except OSError, sqlite3.Error:
            return DatabaseHealth(status="unavailable", detail="database_unavailable")

    def _backup_files(self) -> tuple[tuple[Path, ...], Path | None]:
        try:
            files = tuple(path for path in self._settings.backup_dir.glob("*.sqlite3.gz") if path.is_file())
        except OSError:
            return (), None
        latest = max(files, key=lambda path: path.stat().st_mtime, default=None)
        return files, latest

    def _backup_health(self, files: tuple[Path, ...]) -> BackupHealth:
        if self._last_backup_failure is not None:
            return BackupHealth(status="degraded", detail="backup_failed", failure_code=self._last_backup_failure)
        try:
            size = sum(path.stat().st_size for path in files)
        except OSError:
            return BackupHealth(status="unavailable", detail="backup_unavailable")
        if not files:
            return BackupHealth(status="degraded", detail="backup_missing", size_bytes=0)
        return BackupHealth(status="ok", size_bytes=size)

    def _disk_health(self) -> DiskHealth:
        try:
            available = shutil.disk_usage(self._settings.database_path.parent).free
        except OSError:
            return DiskHealth(status="unavailable", detail="disk_unavailable")
        return DiskHealth(status="ok" if available > 0 else "degraded", available_bytes=available)

    def _freshness_health(self, latest: Path | None) -> FreshnessHealth:
        if latest is None:
            return FreshnessHealth(status="unavailable", detail="backup_missing")
        try:
            latest_at = datetime.fromtimestamp(latest.stat().st_mtime, tz=UTC)
        except OSError:
            return FreshnessHealth(status="unavailable", detail="backup_unavailable")
        age = max(0, int((self._now() - latest_at).total_seconds()))
        threshold = self._settings.backup_retention_days * 86400
        status: HealthStatus = "ok" if age <= threshold else "degraded"
        return FreshnessHealth(status=status, latest_at=latest_at, age_seconds=age)

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("operations clock must be timezone-aware")
        return now.astimezone(UTC)


def _overall_status(statuses: tuple[HealthStatus, ...]) -> HealthStatus:
    if "unavailable" in statuses:
        return "unavailable"
    if "degraded" in statuses:
        return "degraded"
    return "ok"
