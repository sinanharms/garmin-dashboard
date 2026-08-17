import sqlite3
from collections.abc import Sequence
from datetime import datetime

from strava_dashboard.domain.models import SleepCursor, SleepSession
from strava_dashboard.ports.storage import StorageError

from ._common import SQLiteStore, cursor_for, date_text, parse_timestamp, save_cursor, timestamp_text


class SQLiteSleepStore(SQLiteStore):
    def cursor(self) -> SleepCursor | None:
        return cursor_for(self.connection, "sleep", SleepCursor)

    def upsert_batch(self, records: Sequence[SleepSession], cursor: SleepCursor) -> int:
        try:
            with self.connection:
                for record in records:
                    self.connection.execute(
                        """
                    INSERT INTO sleep_sessions(
                        external_id, started_at, ended_at, local_date, duration_seconds, score
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(external_id) DO UPDATE SET
                        started_at = excluded.started_at,
                        ended_at = excluded.ended_at,
                        local_date = excluded.local_date,
                        duration_seconds = excluded.duration_seconds,
                        score = excluded.score
                    """,
                        (
                            record.external_id,
                            timestamp_text(record.started_at),
                            timestamp_text(record.ended_at),
                            date_text(record.local_date),
                            record.duration_seconds,
                            record.score,
                        ),
                    )
                save_cursor(self.connection, "sleep", cursor)
        except sqlite3.Error as error:
            raise StorageError("SQLite sleep write failed") from error
        return len(records)

    def between(self, start: datetime, end: datetime) -> tuple[SleepSession, ...]:
        try:
            with self.connection.locked():
                rows = self.connection.execute(
                    """
                    SELECT * FROM sleep_sessions
                    WHERE started_at >= ? AND started_at < ?
                    ORDER BY started_at ASC, external_id ASC
                    """,
                    (timestamp_text(start), timestamp_text(end)),
                ).fetchall()
        except sqlite3.Error as error:
            raise StorageError("SQLite sleep read failed") from error
        return tuple(
            SleepSession(
                external_id=row["external_id"],
                started_at=parse_timestamp(row["started_at"]),
                ended_at=parse_timestamp(row["ended_at"]),
                local_date=datetime.fromisoformat(row["local_date"]).date(),
                duration_seconds=row["duration_seconds"],
                score=row["score"],
            )
            for row in rows
        )
