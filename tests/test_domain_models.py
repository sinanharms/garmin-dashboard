from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import get_args, get_type_hints

import pytest

from strava_dashboard.domain.models import (
    Activity,
    DashboardSnapshot,
    HealthSummary,
    RecoverySignal,
    SleepSession,
    SyncCursor,
    SyncRun,
    SyncStageResult,
    SyncWindow,
    TrainingBlock,
    TrainingSummary,
    TrendBucket,
    TrendSnapshot,
)
from strava_dashboard.domain.plan_models import Goal, PlanConstraints, PlanProposal, Workout


def activity(utc_now: datetime, **changes: object) -> Activity:
    values = {
        "external_id": "activity-1",
        "activity_type": "running",
        "started_at": utc_now,
        "local_date": utc_now.date(),
        "duration_seconds": 1800,
        "distance_meters": 5000.0,
        "elevation_meters": 30.0,
        "average_heart_rate": 145.0,
        "max_heart_rate": 170.0,
        "calories": 350.0,
    }
    values.update(changes)
    return Activity(**values)


def sleep(utc_now: datetime, **changes: object) -> SleepSession:
    values = {
        "external_id": "sleep-1",
        "started_at": utc_now,
        "ended_at": utc_now + timedelta(hours=8),
        "local_date": utc_now.date(),
        "duration_seconds": 8 * 60 * 60,
        "score": 82.0,
    }
    values.update(changes)
    return SleepSession(**values)


def recovery(utc_now: datetime, **changes: object) -> RecoverySignal:
    values = {
        "external_id": "recovery-1",
        "local_date": utc_now.date(),
        "measured_at": utc_now,
        "metric_name": "body_battery",
        "value": 75.0,
        "unit": "percent",
    }
    values.update(changes)
    return RecoverySignal(**values)


@pytest.mark.parametrize("field", ["external_id", "activity_type"])
@pytest.mark.parametrize("value", ["", "   "])
def test_activity_rejects_empty_identity_fields(utc_now: datetime, field: str, value: str) -> None:
    with pytest.raises(ValueError):
        activity(utc_now, **{field: value})


@pytest.mark.parametrize("factory", [activity, sleep])
def test_duration_must_be_non_negative(utc_now: datetime, factory) -> None:
    with pytest.raises(ValueError):
        factory(utc_now, duration_seconds=-1)


@pytest.mark.parametrize("value", [1.5, float("nan")])
@pytest.mark.parametrize("factory", [activity, sleep])
def test_duration_must_be_a_non_negative_integer(utc_now: datetime, factory, value: float) -> None:
    with pytest.raises(ValueError):
        factory(utc_now, duration_seconds=value)


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (activity, "started_at"),
        (sleep, "started_at"),
        (sleep, "ended_at"),
        (recovery, "measured_at"),
    ],
)
def test_source_timestamps_must_be_timezone_aware(utc_now: datetime, factory, field: str) -> None:
    with pytest.raises(ValueError):
        factory(utc_now, **{field: utc_now.replace(tzinfo=None)})


def test_source_timestamp_timezone_is_preserved(utc_now: datetime) -> None:
    source_timezone = timezone(timedelta(hours=5, minutes=30))
    started_at = utc_now.astimezone(source_timezone)

    record = activity(utc_now, started_at=started_at)

    assert record.started_at == started_at
    assert record.started_at.tzinfo is source_timezone


def test_sleep_must_end_after_it_starts(utc_now: datetime) -> None:
    with pytest.raises(ValueError):
        sleep(utc_now, ended_at=utc_now)


@pytest.mark.parametrize("field", ["external_id", "metric_name", "unit"])
@pytest.mark.parametrize("value", ["", "   "])
def test_recovery_requires_metric_identity_and_unit(utc_now: datetime, field: str, value: str) -> None:
    with pytest.raises(ValueError):
        recovery(utc_now, **{field: value})


@pytest.mark.parametrize("data_family", ["activities", "sleep", "recovery"])
def test_sync_cursor_belongs_to_one_supported_data_family(utc_now: datetime, data_family: str) -> None:
    cursor = SyncCursor(data_family=data_family, watermark=utc_now)  # ty: ignore[invalid-argument-type]

    assert cursor.data_family == data_family


def test_sync_cursor_rejects_unknown_or_combined_data_family(utc_now: datetime) -> None:
    with pytest.raises(ValueError):
        SyncCursor(data_family="activities,sleep", watermark=utc_now)  # ty: ignore[invalid-argument-type]


def test_sync_window_validates_timestamps_and_order(utc_now: datetime) -> None:
    with pytest.raises(ValueError):
        SyncWindow(start=utc_now, end=utc_now)
    with pytest.raises(ValueError):
        SyncWindow(start=None, end=utc_now.replace(tzinfo=None))


def test_sync_records_validate_counts_ids_and_timestamps(utc_now: datetime) -> None:
    with pytest.raises(ValueError):
        SyncStageResult(data_family="activities", status="succeeded", record_count=-1, error_code=None)
    with pytest.raises(ValueError):
        SyncRun(run_id=" ", started_at=utc_now, ended_at=None, stages=())
    with pytest.raises(ValueError):
        SyncRun(run_id="run-1", started_at=utc_now, ended_at=utc_now - timedelta(seconds=1), stages=())


@pytest.mark.parametrize("value", [1.5, float("nan"), -1])
def test_sync_record_count_must_be_a_non_negative_integer(utc_now: datetime, value: float) -> None:
    with pytest.raises(ValueError):
        SyncStageResult(data_family="activities", status="succeeded", record_count=value, error_code=None)  # ty: ignore[invalid-argument-type]


def test_domain_records_are_frozen_and_slotted(utc_now: datetime) -> None:
    record = activity(utc_now)

    with pytest.raises(FrozenInstanceError):
        record.duration_seconds = 1  # ty: ignore[invalid-assignment]
    assert not hasattr(record, "__dict__")


def test_plan_records_validate_required_values(utc_now: datetime) -> None:
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
        created_at=utc_now,
    )

    assert proposal.workouts == (workout,)
    with pytest.raises(ValueError):
        Workout(
            workout_id="workout-2",
            scheduled_date=date(2026, 8, 18),
            activity_type="running",
            duration_seconds=-1,
            intensity="easy",
            purpose="Aerobic base",
            explanation="Invalid duration",
        )


def test_frozen_collections_are_runtime_immutable(utc_now: datetime) -> None:
    stage = SyncStageResult(data_family="activities", status="succeeded", record_count=1, error_code=None)
    training = TrainingSummary(  # type: ignore[call-arg]
        start=date(2026, 8, 1),
        end=date(2026, 8, 7),
        activity_count=1,
        duration_seconds=1800,
        distance_meters=5.0,
        elevation_meters=30.0,
        sport_counts=[["running", 1]],
        training_load=None,
    )
    health = HealthSummary(  # type: ignore[call-arg]
        start=training.start,
        end=training.end,
        available=True,
        average_sleep_seconds=28800.0,
        average_sleep_score=82.0,
        recovery_metrics=[["body_battery", 75.0, "percent"]],
    )
    workout = Workout(
        workout_id="workout-1",
        scheduled_date=date(2026, 8, 17),
        activity_type="running",
        duration_seconds=2400,
        intensity="easy",
        purpose="Aerobic base",
        explanation="Build volume safely",
    )
    constraints = PlanConstraints(6000, [0, 2], ["running"], ["easy week"])
    proposal = PlanProposal("proposal-1", "goal-1", training.start, [workout], "One easy session", utc_now)
    run = SyncRun("run-1", utc_now, None, [stage])
    block = TrainingBlock(training.start, training.end, activity(utc_now), [activity(utc_now)], training)
    dashboard = DashboardSnapshot(utc_now, training, health, [activity(utc_now)])
    trend = TrendSnapshot(training.start, training.end, TrendBucket.WEEK, [training], [health])

    assert all(
        isinstance(value, tuple)
        for value in (
            run.stages,
            training.sport_counts,
            health.recovery_metrics,
            constraints.available_weekdays,
            constraints.activity_preferences,
            constraints.requirements,
            proposal.workouts,
            block.activities,
            dashboard.recent_activities,
            trend.training,
            trend.health,
        )
    )


def test_ports_expose_replaceable_protocols() -> None:
    from strava_dashboard.ports.coach import CoachProvider
    from strava_dashboard.ports.garmin import GarminDataSource
    from strava_dashboard.ports.storage import (
        ActivityStore,
        BackupStore,
        GoalStore,
        PlanStore,
        RecoveryStore,
        SleepStore,
        SyncRunStore,
    )

    protocols = {
        GarminDataSource: {"fetch_activities", "fetch_sleep", "fetch_recovery"},
        ActivityStore: {"cursor", "upsert_batch", "between"},
        SleepStore: {"cursor", "upsert_batch", "between"},
        RecoveryStore: {"cursor", "upsert_batch", "between"},
        SyncRunStore: {"save", "get", "recent"},
        GoalStore: {"save", "current"},
        PlanStore: {"save", "current"},
        BackupStore: {"create", "restore", "delete"},
        CoachProvider: {"propose"},
    }

    for protocol, methods in protocols.items():
        assert protocol._is_protocol  # ty: ignore[unresolved-attribute]
        assert methods <= set(protocol.__dict__)


def test_storage_ports_own_their_cursor_family() -> None:
    from strava_dashboard.domain.models import ActivityCursor, RecoveryCursor, SleepCursor
    from strava_dashboard.ports.storage import ActivityStore, RecoveryStore, SleepStore

    assert ActivityCursor in get_args(get_type_hints(ActivityStore.cursor)["return"])
    assert get_type_hints(ActivityStore.upsert_batch)["cursor"] is ActivityCursor
    assert SleepCursor in get_args(get_type_hints(SleepStore.cursor)["return"])
    assert get_type_hints(SleepStore.upsert_batch)["cursor"] is SleepCursor
    assert RecoveryCursor in get_args(get_type_hints(RecoveryStore.cursor)["return"])
    assert get_type_hints(RecoveryStore.upsert_batch)["cursor"] is RecoveryCursor


def test_domain_and_ports_have_no_framework_provider_or_storage_imports() -> None:
    project_root = Path(__file__).parents[1]
    files = (
        project_root / "src/strava_dashboard/domain/models.py",
        project_root / "src/strava_dashboard/domain/plan_models.py",
        project_root / "src/strava_dashboard/ports/garmin.py",
        project_root / "src/strava_dashboard/ports/storage.py",
        project_root / "src/strava_dashboard/ports/coach.py",
    )
    forbidden = ("fastapi", "pydantic", "sqlite", "mcp", "openai", "anthropic")

    for path in files:
        source = path.read_text().lower()
        assert not any(name in source for name in forbidden), path
