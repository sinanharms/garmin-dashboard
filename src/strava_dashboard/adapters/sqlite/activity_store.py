import sqlite3
from collections.abc import Sequence
from datetime import datetime

from strava_dashboard.domain.models import Activity, ActivityCursor
from strava_dashboard.ports.storage import StorageError

from ._common import SQLiteStore, cursor_for, date_text, parse_timestamp, save_cursor, timestamp_text


class SQLiteActivityStore(SQLiteStore):
    def cursor(self) -> ActivityCursor | None:
        return cursor_for(self.connection, "activities", ActivityCursor)

    def upsert_batch(self, records: Sequence[Activity], cursor: ActivityCursor) -> int:
        try:
            with self.connection:
                for record in records:
                    self.connection.execute(
                        """
                    INSERT INTO activities(
                        external_id, activity_type, started_at, local_date, duration_seconds,
                        distance_meters, elevation_meters, average_heart_rate, max_heart_rate, calories
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(external_id) DO UPDATE SET
                        activity_type = excluded.activity_type,
                        started_at = excluded.started_at,
                        local_date = excluded.local_date,
                        duration_seconds = excluded.duration_seconds,
                        distance_meters = excluded.distance_meters,
                        elevation_meters = excluded.elevation_meters,
                        average_heart_rate = excluded.average_heart_rate,
                        max_heart_rate = excluded.max_heart_rate,
                        calories = excluded.calories
                    """,
                        (
                            record.external_id,
                            record.activity_type,
                            timestamp_text(record.started_at),
                            date_text(record.local_date),
                            record.duration_seconds,
                            record.distance_meters,
                            record.elevation_meters,
                            record.average_heart_rate,
                            record.max_heart_rate,
                            record.calories,
                        ),
                    )
                save_cursor(self.connection, "activities", cursor)
        except sqlite3.Error as error:
            raise StorageError("SQLite activity write failed") from error
        return len(records)

    def between(self, start: datetime, end: datetime) -> tuple[Activity, ...]:
        rows = self.connection.execute(
            """
            SELECT * FROM activities
            WHERE started_at >= ? AND started_at < ?
            ORDER BY started_at ASC, external_id ASC
            """,
            (timestamp_text(start), timestamp_text(end)),
        ).fetchall()
        return tuple(
            Activity(
                external_id=row["external_id"],
                activity_type=row["activity_type"],
                started_at=parse_timestamp(row["started_at"]),
                local_date=datetime.fromisoformat(row["local_date"]).date(),
                duration_seconds=row["duration_seconds"],
                distance_meters=row["distance_meters"],
                elevation_meters=row["elevation_meters"],
                average_heart_rate=row["average_heart_rate"],
                max_heart_rate=row["max_heart_rate"],
                calories=row["calories"],
            )
            for row in rows
        )
