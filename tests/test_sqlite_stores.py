from datetime import UTC, date, datetime, timedelta

from strava_dashboard.adapters.sqlite.connection import open_connection
from strava_dashboard.adapters.sqlite.planning_store import SQLiteGoalStore, SQLitePlanStore
from strava_dashboard.adapters.sqlite.sync_store import SQLiteSyncRunStore
from strava_dashboard.domain.models import SyncRun, SyncStageResult
from strava_dashboard.domain.plan_models import Goal, PlanProposal, ValidatedPlan, Workout


def test_connection_applies_required_sqlite_pragmas(tmp_path) -> None:
    connection = open_connection(tmp_path / "pragmas.sqlite")

    assert connection.row_factory is not None
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert connection.execute("PRAGMA busy_timeout").fetchone()[0] > 0
    assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == 1

    connection.close()


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
