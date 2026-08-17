import sqlite3
from collections.abc import Sequence
from datetime import UTC, date, datetime

from strava_dashboard.domain.models import (
    ActivityCursor,
    DataFamily,
    RecoveryCursor,
    SleepCursor,
)
from strava_dashboard.ports.storage import StorageError


class SQLiteStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection


def timestamp_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored timestamp must be timezone-aware")
    return parsed


def cursor_for[CursorType: (ActivityCursor, SleepCursor, RecoveryCursor)](
    connection: sqlite3.Connection, family: DataFamily, cursor_type: type[CursorType]
) -> CursorType | None:
    try:
        row = connection.execute("SELECT watermark FROM sync_cursors WHERE data_family = ?", (family,)).fetchone()
    except sqlite3.Error as error:
        raise StorageError("SQLite cursor read failed") from error
    if row is None:
        return None
    return cursor_type(watermark=parse_timestamp(row["watermark"]))


def save_cursor[CursorType: (ActivityCursor, SleepCursor, RecoveryCursor)](
    connection: sqlite3.Connection, family: DataFamily, cursor: CursorType
) -> None:
    connection.execute(
        """
        INSERT INTO sync_cursors(data_family, watermark) VALUES (?, ?)
        ON CONFLICT(data_family) DO UPDATE SET watermark = excluded.watermark
        WHERE excluded.watermark > sync_cursors.watermark
        """,
        (family, timestamp_text(cursor.watermark)),
    )


def date_text(value: date) -> str:
    return value.isoformat()


def require_limit(limit: int) -> int:
    if limit < 1:
        raise ValueError("limit must be positive")
    return limit


def rows_to_tuple(rows: Sequence[sqlite3.Row]) -> tuple[sqlite3.Row, ...]:
    return tuple(rows)
