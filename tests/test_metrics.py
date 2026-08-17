from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from garmin_dashboard.application.metrics import (
    daily_summaries,
    rolling_training_load,
    summarize_health,
    summarize_training,
    summarize_trends,
    trend_direction,
)
from garmin_dashboard.application.race_analysis import select_preceding_block
from garmin_dashboard.domain.models import Activity, RecoverySignal, SleepSession, TrainingSummary

BASE = datetime(2026, 8, 16, 6, tzinfo=UTC)


def activity(number: int, *, local_date: date | None = None, activity_type: str = "running") -> Activity:
    started = BASE + timedelta(days=number)
    return Activity(
        external_id=f"activity-{number}",
        activity_type=activity_type,
        started_at=started,
        local_date=local_date or started.date(),
        duration_seconds=1800 + number * 60,
        distance_meters=5000.0 + number * 100,
        elevation_meters=30.0 + number,
        average_heart_rate=145.0,
        max_heart_rate=170.0,
        calories=350.0,
    )


def sleep(number: int, *, score: float | None = 80.0) -> SleepSession:
    started = BASE + timedelta(days=number)
    return SleepSession(
        external_id=f"sleep-{number}",
        started_at=started,
        ended_at=started + timedelta(hours=8),
        local_date=started.date(),
        duration_seconds=28800,
        score=score,
    )


def recovery(number: int, metric_name: str = "body_battery") -> RecoverySignal:
    measured = BASE + timedelta(days=number)
    return RecoverySignal(
        external_id=f"recovery-{number}-{metric_name}",
        local_date=measured.date(),
        measured_at=measured,
        metric_name=metric_name,
        value=70.0 + number,
        unit="percent",
    )


def test_training_summary_uses_local_date_start_inclusive_end_exclusive() -> None:
    records = (activity(0), activity(1), activity(2))

    summary = summarize_training(records, BASE.date(), (BASE + timedelta(days=2)).date())

    assert summary.activity_count == 2
    assert summary.duration_seconds == 3660
    assert summary.distance_meters == 10100.0
    assert summary.elevation_meters == 61.0
    assert summary.sport_counts == (("running", 2),)
    assert summary.training_load == 61.0


def test_training_summary_uses_timezone_aware_local_attribution() -> None:
    local_zone = timezone(timedelta(hours=10))
    record = activity(0, local_date=date(2026, 8, 17))
    record = record.model_copy(update={"started_at": BASE.astimezone(local_zone)})

    summary = summarize_training((record,), date(2026, 8, 17), date(2026, 8, 18))

    assert summary.activity_count == 1


def test_daily_summaries_and_rolling_load_are_deterministic() -> None:
    records = (activity(2), activity(0, activity_type="cycling"), activity(1))

    daily = daily_summaries(records, BASE.date(), (BASE + timedelta(days=3)).date())

    assert [item.start for item in daily] == [BASE.date() + timedelta(days=i) for i in range(3)]
    assert [item.activity_count for item in daily] == [1, 1, 1]
    assert rolling_training_load(records, BASE.date() + timedelta(days=3), 2) == 63.0


def test_health_summary_keeps_missing_values_unavailable() -> None:
    summary = summarize_health((sleep(0, score=None),), (), BASE.date(), (BASE + timedelta(days=2)).date())

    assert summary.available is True
    assert summary.average_sleep_seconds == 28800.0
    assert summary.average_sleep_score is None
    assert summary.recovery_metrics == ()

    missing = summarize_health((), (), BASE.date(), (BASE + timedelta(days=2)).date())
    assert missing.available is False
    assert missing.average_sleep_seconds is None
    assert missing.average_sleep_score is None
    assert missing.recovery_metrics == ()


def test_health_summary_aggregates_recovery_metrics_in_stable_order() -> None:
    summary = summarize_health(
        (),
        (recovery(1, "hrv"), recovery(0, "body_battery"), recovery(0, "hrv")),
        BASE.date(),
        (BASE + timedelta(days=2)).date(),
    )

    assert summary.recovery_metrics == (("body_battery", 70.0, "percent"), ("hrv", 70.5, "percent"))


def test_trend_direction_is_deterministic() -> None:
    low = TrainingSummary(
        start=BASE.date(),
        end=BASE.date() + timedelta(days=1),
        activity_count=1,
        duration_seconds=60,
        distance_meters=1.0,
        elevation_meters=1.0,
        sport_counts=(("running", 1),),
        training_load=1.0,
    )
    high = low.model_copy(update={"training_load": 2.0})

    assert trend_direction(low, high) == "up"
    assert trend_direction(high, low) == "down"
    assert trend_direction(low, low) == "flat"


def test_trend_snapshot_is_stable_and_keeps_empty_health_unavailable() -> None:
    records = (activity(0), activity(1), activity(2))

    snapshot = summarize_trends(
        records,
        (),
        (),
        BASE.date(),
        (BASE + timedelta(days=14)).date(),
    )

    assert [summary.activity_count for summary in snapshot.training] == [3, 0]
    assert [summary.available for summary in snapshot.health] == [False, False]
    assert snapshot == summarize_trends(records, (), (), BASE.date(), (BASE + timedelta(days=14)).date())


def test_race_block_is_bounded_before_outcome_and_sorted() -> None:
    outcome = activity(4, activity_type="running")
    records = (outcome, activity(3), activity(0), activity(1), activity(2))

    block = select_preceding_block(records, outcome, weeks=1)

    assert block.start == outcome.local_date - timedelta(weeks=1)
    assert block.end == outcome.local_date
    assert [item.external_id for item in block.activities] == ["activity-0", "activity-1", "activity-2", "activity-3"]
    assert block.summary.activity_count == 4
    assert all(item.local_date < outcome.local_date for item in block.activities)


def test_metrics_reject_invalid_date_ranges_and_block_lengths() -> None:
    with pytest.raises(ValueError, match="start must be before end"):
        summarize_training((), BASE.date(), BASE.date())
    with pytest.raises(ValueError, match="weeks must be positive"):
        select_preceding_block((), activity(1), weeks=0)
