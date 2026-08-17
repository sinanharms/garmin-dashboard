import sqlite3
from pathlib import Path

from .schema import apply_schema

DEFAULT_BUSY_TIMEOUT_SECONDS = 5.0


def open_connection(path: Path, busy_timeout_seconds: float = DEFAULT_BUSY_TIMEOUT_SECONDS) -> sqlite3.Connection:
    if busy_timeout_seconds <= 0:
        raise ValueError("busy_timeout_seconds must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=busy_timeout_seconds)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(f"PRAGMA busy_timeout = {int(busy_timeout_seconds * 1000)}")
    apply_schema(connection)
    return connection
