from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import BaseModel, ValidationError

from strava_dashboard.domain.models import (
    Activity,
    ActivityCursor,
    DashboardSnapshot,
    DomainModel,
    HealthSummary,
    RecoveryCursor,
    RecoverySignal,
    SleepCursor,
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
    return Activity.model_validate(values)


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
    return SleepSession.model_validate(values)


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
    return RecoverySignal.model_validate(values)


@pytest.mark.parametrize("field", ["external_id", "activity_type"])
@pytest.mark.parametrize("value", ["", "   "])
def test_activity_rejects_empty_identity_fields(utc_now: datetime, field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        activity(utc_now, **{field: value})


@pytest.mark.parametrize("factory", [activity, sleep])
def test_duration_must_be_non_negative(utc_now: datetime, factory) -> None:
    with pytest.raises(ValidationError):
        factory(utc_now, duration_seconds=-1)


@pytest.mark.parametrize("value", [True, 1.5, float("nan"), float("inf"), "1"])
@pytest.mark.parametrize("factory", [activity, sleep])
def test_duration_must_be_a_strict_finite_non_negative_integer(utc_now: datetime, factory, value: object) -> None:
    with pytest.raises(ValidationError):
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
    with pytest.raises(ValidationError):
        factory(utc_now, **{field: utc_now.replace(tzinfo=None)})


def test_source_timestamp_timezone_is_preserved(utc_now: datetime) -> None:
    source_timezone = timezone(timedelta(hours=5, minutes=30))
    started_at = utc_now.astimezone(source_timezone)

    record = activity(utc_now, started_at=started_at)

    assert record.started_at == started_at
    assert record.started_at.tzinfo is source_timezone


def test_sleep_must_end_after_it_starts(utc_now: datetime) -> None:
    with pytest.raises(ValidationError):
        sleep(utc_now, ended_at=utc_now)


@pytest.mark.parametrize("field", ["external_id", "metric_name", "unit"])
@pytest.mark.parametrize("value", ["", "   "])
def test_recovery_requires_metric_identity_and_unit(utc_now: datetime, field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        recovery(utc_now, **{field: value})


@pytest.mark.parametrize("data_family", ["activities", "sleep", "recovery"])
def test_sync_cursor_belongs_to_one_supported_data_family(utc_now: datetime, data_family: str) -> None:
    cursor = SyncCursor(data_family=data_family, watermark=utc_now)  # ty: ignore[invalid-argument-type]

    assert cursor.data_family == data_family


def test_sync_cursor_rejects_unknown_or_combined_data_family(utc_now: datetime) -> None:
    with pytest.raises(ValidationError):
        SyncCursor(data_family="activities,sleep", watermark=utc_now)  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize(
    ("cursor_type", "data_family"),
    [(ActivityCursor, "activities"), (SleepCursor, "sleep"), (RecoveryCursor, "recovery")],
)
def test_family_cursor_accepts_only_its_data_family(utc_now: datetime, cursor_type, data_family: str) -> None:
    cursor = cursor_type.model_validate({"data_family": data_family, "watermark": utc_now})

    assert cursor.data_family == data_family
    with pytest.raises(ValidationError):
        cursor_type.model_validate({"data_family": "wrong", "watermark": utc_now})


def test_sync_window_validates_timestamps_and_order(utc_now: datetime) -> None:
    with pytest.raises(ValidationError):
        SyncWindow(start=utc_now, end=utc_now)
    with pytest.raises(ValidationError):
        SyncWindow(start=None, end=utc_now.replace(tzinfo=None))


def test_sync_records_validate_counts_ids_and_timestamps(utc_now: datetime) -> None:
    with pytest.raises(ValidationError):
        SyncStageResult(data_family="activities", status="succeeded", record_count=-1, error_code=None)
    with pytest.raises(ValidationError):
        SyncRun(run_id=" ", started_at=utc_now, ended_at=None, stages=())
    with pytest.raises(ValidationError):
        SyncRun(run_id="run-1", started_at=utc_now, ended_at=utc_now - timedelta(seconds=1), stages=())


@pytest.mark.parametrize("value", [True, 1.5, float("nan"), float("inf"), "1", -1])
def test_sync_record_count_must_be_a_strict_finite_non_negative_integer(utc_now: datetime, value: object) -> None:
    with pytest.raises(ValidationError):
        SyncStageResult(data_family="activities", status="succeeded", record_count=value, error_code=None)  # ty: ignore[invalid-argument-type]


def test_domain_records_share_frozen_extra_forbid_pydantic_config(utc_now: datetime) -> None:
    record = activity(utc_now)

    assert isinstance(record, BaseModel)
    assert issubclass(Activity, DomainModel)
    assert record.model_config["frozen"] is True
    assert record.model_config["extra"] == "forbid"
    with pytest.raises(ValidationError):
        record.duration_seconds = 1
    with pytest.raises(ValidationError):
        Activity.model_validate({**record.model_dump(), "unexpected": "value"})


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
    with pytest.raises(ValidationError):
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
    training = TrainingSummary(
        start=date(2026, 8, 1),
        end=date(2026, 8, 7),
        activity_count=1,
        duration_seconds=1800,
        distance_meters=5.0,
        elevation_meters=30.0,
        sport_counts=[["running", 1]],  # ty: ignore[invalid-argument-type]
        training_load=None,
    )
    health = HealthSummary(
        start=training.start,
        end=training.end,
        available=True,
        average_sleep_seconds=28800.0,
        average_sleep_score=82.0,
        recovery_metrics=[["body_battery", 75.0, "percent"]],  # ty: ignore[invalid-argument-type]
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
    constraints = PlanConstraints(
        weekly_time_budget_seconds=6000,
        available_weekdays=[0, 2],  # ty: ignore[invalid-argument-type]
        activity_preferences=["running"],  # ty: ignore[invalid-argument-type]
        requirements=["easy week"],  # ty: ignore[invalid-argument-type]
    )
    proposal = PlanProposal(
        proposal_id="proposal-1",
        goal_id="goal-1",
        week_start=training.start,
        workouts=[workout],  # ty: ignore[invalid-argument-type]
        explanation="One easy session",
        created_at=utc_now,
    )
    run = SyncRun(run_id="run-1", started_at=utc_now, ended_at=None, stages=[stage])  # ty: ignore[invalid-argument-type]
    block = TrainingBlock(
        start=training.start,
        end=training.end,
        outcome=activity(utc_now),
        activities=[activity(utc_now)],  # ty: ignore[invalid-argument-type]
        summary=training,
    )
    dashboard = DashboardSnapshot(
        generated_at=utc_now,
        training=training,
        health=health,
        recent_activities=[activity(utc_now)],  # ty: ignore[invalid-argument-type]
    )
    trend = TrendSnapshot(
        start=training.start,
        end=training.end,
        bucket=TrendBucket.WEEK,
        training=[training],  # ty: ignore[invalid-argument-type]
        health=[health],  # ty: ignore[invalid-argument-type]
    )

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
