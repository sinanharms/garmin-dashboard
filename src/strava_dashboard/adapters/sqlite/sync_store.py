import json
import sqlite3
from datetime import datetime

from strava_dashboard.domain.models import SyncRun, SyncStageResult
from strava_dashboard.ports.storage import StorageError

from ._common import SQLiteStore, require_limit, timestamp_text


class SQLiteSyncRunStore(SQLiteStore):
    def save(self, run: SyncRun) -> None:
        stages = json.dumps([stage.model_dump(mode="json") for stage in run.stages], sort_keys=True)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO sync_runs(run_id, started_at, ended_at, stages_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    stages_json = excluded.stages_json
                """,
                (run.run_id, timestamp_text(run.started_at), timestamp_text(run.ended_at) if run.ended_at else None, stages),
            )

    def get(self, run_id: str) -> SyncRun | None:
        try:
            with self.connection.locked():
                row = self.connection.execute("SELECT * FROM sync_runs WHERE run_id = ?", (run_id,)).fetchone()
        except sqlite3.Error as error:
            raise StorageError("SQLite sync-run read failed") from error
        return None if row is None else self._model_from_row(row)

    def recent(self, limit: int) -> tuple[SyncRun, ...]:
        bounded_limit = require_limit(limit)
        try:
            with self.connection.locked():
                rows = self.connection.execute(
                    "SELECT * FROM sync_runs ORDER BY started_at DESC, run_id DESC LIMIT ?", (bounded_limit,)
                ).fetchall()
        except sqlite3.Error as error:
            raise StorageError("SQLite sync-run read failed") from error
        return tuple(self._model_from_row(row) for row in rows)

    @staticmethod
    def _model_from_row(row) -> SyncRun:
        stages = tuple(SyncStageResult.model_validate(stage) for stage in json.loads(row["stages_json"]))
        return SyncRun(
            run_id=row["run_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            stages=stages,
        )
