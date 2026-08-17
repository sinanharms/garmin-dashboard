import sqlite3
from collections.abc import Sequence
from datetime import datetime

from strava_dashboard.domain.models import RecoveryCursor, RecoverySignal
from strava_dashboard.ports.storage import StorageError

from ._common import SQLiteStore, cursor_for, date_text, parse_timestamp, save_cursor, timestamp_text


class SQLiteRecoveryStore(SQLiteStore):
    def cursor(self) -> RecoveryCursor | None:
        return cursor_for(self.connection, "recovery", RecoveryCursor)

    def upsert_batch(self, records: Sequence[RecoverySignal], cursor: RecoveryCursor) -> int:
        try:
            with self.connection:
                for record in records:
                    self.connection.execute(
                        """
                    INSERT INTO recovery_signals(
                        external_id, local_date, measured_at, metric_name, value, unit
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(external_id) DO UPDATE SET
                        local_date = excluded.local_date,
                        measured_at = excluded.measured_at,
                        metric_name = excluded.metric_name,
                        value = excluded.value,
                        unit = excluded.unit
                    """,
                        (
                            record.external_id,
                            date_text(record.local_date),
                            timestamp_text(record.measured_at),
                            record.metric_name,
                            record.value,
                            record.unit,
                        ),
                    )
                save_cursor(self.connection, "recovery", cursor)
        except sqlite3.Error as error:
            raise StorageError("SQLite recovery write failed") from error
        return len(records)

    def between(self, start: datetime, end: datetime) -> tuple[RecoverySignal, ...]:
        try:
            with self.connection.locked():
                rows = self.connection.execute(
                    """
                    SELECT * FROM recovery_signals
                    WHERE measured_at >= ? AND measured_at < ?
                    ORDER BY measured_at ASC, external_id ASC
                    """,
                    (timestamp_text(start), timestamp_text(end)),
                ).fetchall()
        except sqlite3.Error as error:
            raise StorageError("SQLite recovery read failed") from error
        return tuple(
            RecoverySignal(
                external_id=row["external_id"],
                local_date=datetime.fromisoformat(row["local_date"]).date(),
                measured_at=parse_timestamp(row["measured_at"]),
                metric_name=row["metric_name"],
                value=row["value"],
                unit=row["unit"],
            )
            for row in rows
        )
