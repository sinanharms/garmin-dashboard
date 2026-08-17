import sqlite3

SCHEMA_VERSION = 1


def apply_schema(connection: sqlite3.Connection) -> None:
    with connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            );
            INSERT INTO schema_version(version)
            SELECT 1
            WHERE NOT EXISTS (SELECT 1 FROM schema_version);

            CREATE TABLE IF NOT EXISTS activities (
                external_id TEXT PRIMARY KEY,
                activity_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                local_date TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                distance_meters REAL,
                elevation_meters REAL,
                average_heart_rate REAL,
                max_heart_rate REAL,
                calories REAL
            );
            CREATE INDEX IF NOT EXISTS activities_started_at_idx ON activities(started_at, external_id);

            CREATE TABLE IF NOT EXISTS sleep_sessions (
                external_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                local_date TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                score REAL
            );
            CREATE INDEX IF NOT EXISTS sleep_sessions_started_at_idx ON sleep_sessions(started_at, external_id);

            CREATE TABLE IF NOT EXISTS recovery_signals (
                external_id TEXT PRIMARY KEY,
                local_date TEXT NOT NULL,
                measured_at TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS recovery_signals_measured_at_idx ON recovery_signals(measured_at, external_id);

            CREATE TABLE IF NOT EXISTS sync_cursors (
                data_family TEXT PRIMARY KEY,
                watermark TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sync_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                stages_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sync_runs_started_at_idx ON sync_runs(started_at DESC, run_id DESC);

            CREATE TABLE IF NOT EXISTS goals (
                goal_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                target_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS plans (
                proposal_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL REFERENCES goals(goal_id),
                week_start TEXT NOT NULL,
                explanation TEXT NOT NULL,
                created_at TEXT NOT NULL,
                validated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS plans_validated_at_idx ON plans(validated_at DESC, proposal_id DESC);

            CREATE TABLE IF NOT EXISTS plan_workouts (
                proposal_id TEXT NOT NULL REFERENCES plans(proposal_id) ON DELETE CASCADE,
                workout_id TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                intensity TEXT NOT NULL,
                purpose TEXT NOT NULL,
                explanation TEXT NOT NULL,
                PRIMARY KEY (proposal_id, workout_id)
            );
            """
        )
        version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
        if version != SCHEMA_VERSION:
            raise RuntimeError(f"Unsupported SQLite schema version: {version}")
