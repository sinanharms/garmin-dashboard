import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from types import TracebackType
from typing import Any

from .schema import apply_schema

DEFAULT_BUSY_TIMEOUT_SECONDS = 5.0


class SQLiteConnection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = RLock()

    @property
    def row_factory(self) -> Any:
        return self._connection.row_factory

    @row_factory.setter
    def row_factory(self, value: Any) -> None:
        self._connection.row_factory = value

    @contextmanager
    def locked(self) -> Iterator[None]:
        with self._lock:
            yield

    def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._connection.execute(sql, parameters)

    def executemany(self, sql: str, parameters: Any) -> sqlite3.Cursor:
        with self._lock:
            return self._connection.executemany(sql, parameters)

    def commit(self) -> None:
        with self._lock:
            self._connection.commit()

    def rollback(self) -> None:
        with self._lock:
            self._connection.rollback()

    def backup(self, destination: sqlite3.Connection) -> None:
        with self._lock:
            self._connection.backup(destination)

    def restore_from(self, source: sqlite3.Connection) -> None:
        with self._lock:
            source.backup(self._connection)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> SQLiteConnection:
        self._lock.acquire()
        try:
            self._connection.__enter__()
        except BaseException:
            self._lock.release()
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        try:
            return self._connection.__exit__(exc_type, exc_value, traceback)
        finally:
            self._lock.release()


def open_connection(path: Path, busy_timeout_seconds: float = DEFAULT_BUSY_TIMEOUT_SECONDS) -> SQLiteConnection:
    if busy_timeout_seconds <= 0:
        raise ValueError("busy_timeout_seconds must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=busy_timeout_seconds, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(f"PRAGMA busy_timeout = {int(busy_timeout_seconds * 1000)}")
    apply_schema(connection)
    return SQLiteConnection(connection)
