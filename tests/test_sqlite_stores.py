import sqlite3
from datetime import UTC, date, datetime, timedelta

import pytest

from garmin_dashboard.adapters.sqlite.activity_store import SQLiteActivityStore
from garmin_dashboard.adapters.sqlite.connection import open_connection
from garmin_dashboard.adapters.sqlite.planning_store import SQLiteGoalStore, SQLitePlanStore
from garmin_dashboard.adapters.sqlite.schema import SCHEMA_VERSION, apply_schema
from garmin_dashboard.adapters.sqlite.sync_store import SQLiteSyncRunStore
from garmin_dashboard.domain.models import SyncRun, SyncStageResult
from garmin_dashboard.domain.plan_models import Goal, PlanProposal, ValidatedPlan, Workout
from garmin_dashboard.ports.storage import StorageError


def test_connection_applies_required_sqlite_pragmas(tmp_path) -> None:
    connection = open_connection(tmp_path / "pragmas.sqlite")

    assert connection.row_factory is not None
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert connection.execute("PRAGMA busy_timeout").fetchone()[0] > 0
    assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == SCHEMA_VERSION

    connection.close()


def test_legacy_schema_upgrades_sequentially_without_losing_data(tmp_path) -> None:
    database = tmp_path / "legacy.sqlite"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_version(version) VALUES (0)")
    connection.execute("CREATE TABLE legacy_records (external_id TEXT PRIMARY KEY)")
    connection.execute("INSERT INTO legacy_records(external_id) VALUES ('legacy-activity')")
    connection.commit()

    apply_schema(connection)

    assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == SCHEMA_VERSION
    assert connection.execute("SELECT external_id FROM legacy_records").fetchone()[0] == "legacy-activity"
    assert connection.execute("SELECT name FROM sqlite_master WHERE name = 'activities'").fetchone()[0] == "activities"
    connection.close()


def test_future_schema_version_fails_without_destructive_changes(tmp_path) -> None:
    connection = sqlite3.connect(tmp_path / "future.sqlite")
    connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION + 1,))
    connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
    connection.execute("INSERT INTO sentinel(value) VALUES ('preserve-me')")
    connection.commit()

    with pytest.raises(RuntimeError, match="Unsupported SQLite schema version"):
        apply_schema(connection)

    assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == SCHEMA_VERSION + 1
    assert connection.execute("SELECT value FROM sentinel").fetchone()[0] == "preserve-me"
    connection.close()


def test_sqlite_cursor_read_failure_is_redacted_storage_error(tmp_path) -> None:
    connection = open_connection(tmp_path / "closed.sqlite")
    connection.close()

    with pytest.raises(StorageError, match="SQLite cursor read failed"):
        SQLiteActivityStore(connection).cursor()


def test_sync_run_store_round_trips_typed_models(tmp_path) -> None:
    connection = open_connection(tmp_path / "sync.sqlite")
    store = SQLiteSyncRunStore(connection)
    started = datetime(2026, 8, 16, 6, 30, tzinfo=UTC)
    run = SyncRun(
        run_id="run-1",
        started_at=started,
        ended_at=started + timedelta(minutes=2),
        stages=(SyncStageResult(data_family="activities", status="succeeded", record_count=2, error_code=None),),
    )

    store.save(run)

    assert store.get("run-1") == run
    assert store.recent(10) == (run,)
    connection.close()


def test_goal_and_plan_stores_preserve_current_models(tmp_path) -> None:
    connection = open_connection(tmp_path / "planning.sqlite")
    goals = SQLiteGoalStore(connection)
    plans = SQLitePlanStore(connection)
    goal = Goal(goal_id="goal-1", description="Run 10 km", target_date=date(2026, 10, 1))
    workout = Workout(
        workout_id="workout-1",
        scheduled_date=date(2026, 8, 17),
        activity_type="running",
        duration_seconds=2400,
        intensity="easy",
        purpose="Aerobic base",
        explanation="Build volume safely",
    )
    proposal = PlanProposal(
        proposal_id="proposal-1",
        goal_id=goal.goal_id,
        week_start=date(2026, 8, 17),
        workouts=(workout,),
        explanation="One easy session",
        created_at=datetime(2026, 8, 16, 6, 30, tzinfo=UTC),
    )
    plan = ValidatedPlan(proposal=proposal, validated_at=datetime(2026, 8, 16, 7, tzinfo=UTC))

    goals.save(goal)
    plans.save(plan)

    assert goals.current() == goal
    assert plans.current() == plan
    connection.close()
