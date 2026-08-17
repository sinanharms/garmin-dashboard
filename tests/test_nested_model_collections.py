from datetime import UTC, date, datetime

from strava_dashboard.domain.models import (
    Activity,
    DashboardSnapshot,
    HealthSummary,
    SyncRun,
    SyncStageResult,
    TrainingBlock,
    TrainingSummary,
    TrendBucket,
    TrendSnapshot,
)
from strava_dashboard.domain.plan_models import PlanConstraints, PlanProposal, Workout


def activity(utc_now: datetime) -> Activity:
    return Activity(
        external_id="activity-1",
        activity_type="running",
        started_at=utc_now,
        local_date=utc_now.date(),
        duration_seconds=1800,
        distance_meters=5000.0,
        elevation_meters=30.0,
        average_heart_rate=145.0,
        max_heart_rate=165.0,
        calories=350.0,
    )


def test_frozen_collections_are_runtime_immutable() -> None:
    utc_now = datetime(2026, 8, 16, 6, tzinfo=UTC)
    stage = SyncStageResult(data_family="activities", status="succeeded", record_count=1, error_code=None)
    training = TrainingSummary(
        start=date(2026, 8, 1),
        end=date(2026, 8, 7),
        activity_count=1,
        duration_seconds=1800,
        distance_meters=5.0,
        elevation_meters=30.0,
        sport_counts=(("running", 1),),
        training_load=None,
    )
    health = HealthSummary(
        start=training.start,
        end=training.end,
        available=True,
        average_sleep_seconds=28800.0,
        average_sleep_score=82.0,
        recovery_metrics=(("body_battery", 75.0, "percent"),),
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
        available_weekdays=(0, 2),
        activity_preferences=("running",),
        requirements=("easy week",),
    )
    proposal = PlanProposal(
        proposal_id="proposal-1",
        goal_id="goal-1",
        week_start=training.start,
        workouts=(workout,),
        explanation="One easy session",
        created_at=utc_now,
    )
    run = SyncRun(run_id="run-1", started_at=utc_now, ended_at=None, stages=(stage,))
    block = TrainingBlock(
        start=training.start,
        end=training.end,
        outcome=activity(utc_now),
        activities=(activity(utc_now),),
        summary=training,
    )
    dashboard = DashboardSnapshot(
        generated_at=utc_now,
        training=training,
        health=health,
        recent_activities=(activity(utc_now),),
    )
    trend = TrendSnapshot(
        start=training.start,
        end=training.end,
        bucket=TrendBucket.WEEK,
        training=(training,),
        health=(health,),
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
