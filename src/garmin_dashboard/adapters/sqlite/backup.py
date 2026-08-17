import gzip
import os
import shutil
import sqlite3
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from garmin_dashboard.ports.backups import is_generated_backup_id
from garmin_dashboard.ports.storage import BackupStore, StorageError

from .connection import SQLiteConnection

BACKUP_SUFFIX = ".sqlite3.gz"


class SQLiteBackupStore(BackupStore):
    def __init__(
        self,
        connection: SQLiteConnection,
        backup_dir: Path,
        retention_count: int,
        retention_days: int,
        clock: Callable[[], datetime],
    ) -> None:
        if retention_count <= 0 or retention_days <= 0:
            raise ValueError("backup retention values must be positive")
        self._connection = connection
        self._backup_dir = backup_dir
        self._retention_count = retention_count
        self._retention_days = retention_days
        self._clock = clock

    def create(self) -> str:
        with self._connection.locked():
            return self._create_locked()

    def _create_locked(self) -> str:
        backup_id = self._backup_id()
        plain_path: Path | None = None
        compressed_path: Path | None = None
        try:
            self._backup_dir.mkdir(parents=True, exist_ok=True)
            plain_path = self._temporary_path(backup_id, ".sqlite3.tmp")
            compressed_path = self._temporary_path(backup_id, ".gz.tmp")
            self._write_sqlite_backup(plain_path)
            self._compress(plain_path, compressed_path)
            final_path = self._backup_dir / backup_id
            os.replace(compressed_path, final_path)
            compressed_path = None
            self._apply_retention()
            return backup_id
        except (OSError, sqlite3.Error) as error:
            raise StorageError("SQLite backup failed") from error
        finally:
            self._cleanup(plain_path)
            self._cleanup(compressed_path)

    def restore(self, backup_id: str) -> None:
        backup_path = self._resolve(backup_id)
        temporary_path: Path | None = None
        source: sqlite3.Connection | None = None
        try:
            with self._connection.locked():
                temporary_path = self._temporary_path(backup_id, ".restore.tmp")
                with gzip.open(backup_path, "rb") as compressed, temporary_path.open("wb") as restored:
                    shutil.copyfileobj(compressed, restored)
                source = sqlite3.connect(temporary_path)
                self._connection.restore_from(source)
        except (OSError, sqlite3.Error, gzip.BadGzipFile) as error:
            raise StorageError("SQLite restore failed") from error
        finally:
            if source is not None:
                source.close()
            self._cleanup(temporary_path)

    def delete(self, backup_id: str) -> None:
        try:
            self._resolve(backup_id).unlink()
        except FileNotFoundError:
            return
        except OSError as error:
            raise StorageError("SQLite backup delete failed") from error

    def _write_sqlite_backup(self, destination_path: Path) -> None:
        destination = sqlite3.connect(destination_path)
        try:
            self._connection.backup(destination)
        finally:
            destination.close()

    @staticmethod
    def _compress(source_path: Path, destination_path: Path) -> None:
        with source_path.open("rb") as source, gzip.open(destination_path, "wb") as compressed:
            shutil.copyfileobj(source, compressed)

    def _apply_retention(self) -> None:
        backups = sorted(self._generated_backups(), key=self._mtime, reverse=True)
        cutoff = self._now() - timedelta(days=self._retention_days)
        for index, path in enumerate(backups):
            if index >= self._retention_count or self._mtime_datetime(path) < cutoff:
                path.unlink()

    def _generated_backups(self) -> tuple[Path, ...]:
        try:
            return tuple(
                path
                for path in self._backup_dir.iterdir()
                if is_generated_backup_id(path.name) and not path.is_symlink() and path.is_file()
            )
        except OSError as error:
            raise StorageError("SQLite backup retention failed") from error

    def _backup_id(self) -> str:
        timestamp = self._now().strftime("%Y%m%dT%H%M%SZ")
        return f"dashboard-{timestamp}-{uuid4().hex[:8]}{BACKUP_SUFFIX}"

    def _temporary_path(self, backup_id: str, suffix: str) -> Path:
        descriptor, name = tempfile.mkstemp(prefix=f".{backup_id}.", suffix=suffix, dir=self._backup_dir)
        os.close(descriptor)
        return self._backup_dir / name

    def _resolve(self, backup_id: str) -> Path:
        if not is_generated_backup_id(backup_id):
            raise StorageError("invalid backup identifier")
        path = self._backup_dir / backup_id
        if path.is_symlink() or not path.is_file():
            raise StorageError("invalid backup identifier")
        return path

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("backup clock must be timezone-aware")
        return now.astimezone(UTC)

    @staticmethod
    def _mtime(path: Path) -> float:
        return path.stat().st_mtime

    @classmethod
    def _mtime_datetime(cls, path: Path) -> datetime:
        return datetime.fromtimestamp(cls._mtime(path), tz=UTC)

    @staticmethod
    def _cleanup(path: Path | None) -> None:
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            return
