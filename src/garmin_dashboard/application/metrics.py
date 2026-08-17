from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Literal

from garmin_dashboard.domain.models import (
    Activity,
    HealthSummary,
    RecoverySignal,
    SleepSession,
    TrainingSummary,
    TrendBucket,
    TrendSnapshot,
)

TrendDirection = Literal["up", "down", "flat"]


def summarize_training(activities: Sequence[Activity], start: date, end: date) -> TrainingSummary:
    _validate_range(start, end)
    selected = _activities_between(activities, start, end)
    sport_counts: defaultdict[str, int] = defaultdict(int)
    for activity in selected:
        sport_counts[activity.activity_type] += 1
    return TrainingSummary(
        start=start,
        end=end,
        activity_count=len(selected),
        duration_seconds=sum(item.duration_seconds for item in selected),
        distance_meters=sum(item.distance_meters or 0.0 for item in selected),
        elevation_meters=sum(item.elevation_meters or 0.0 for item in selected),
        sport_counts=tuple(sorted(sport_counts.items())),
        training_load=sum(_load(item) for item in selected),
    )


def daily_summaries(activities: Sequence[Activity], start: date, end: date) -> tuple[TrainingSummary, ...]:
    _validate_range(start, end)
    return tuple(summarize_training(activities, day, day + timedelta(days=1)) for day in _dates_between(start, end))


def rolling_training_load(activities: Sequence[Activity], end: date, days: int) -> float:
    if days <= 0:
        raise ValueError("days must be positive")
    return summarize_training(activities, end - timedelta(days=days), end).training_load or 0.0


def summarize_health(
    sleep: Sequence[SleepSession],
    recovery: Sequence[RecoverySignal],
    start: date,
    end: date,
) -> HealthSummary:
    _validate_range(start, end)
    sleep_records = tuple(item for item in sleep if start <= item.local_date < end)
    recovery_records = tuple(item for item in recovery if start <= item.local_date < end)
    scores = tuple(item.score for item in sleep_records if item.score is not None)
    grouped_recovery: defaultdict[tuple[str, str], list[float]] = defaultdict(list)
    for item in recovery_records:
        grouped_recovery[(item.metric_name, item.unit)].append(item.value)
    recovery_metrics = tuple(
        (metric_name, sum(values) / len(values), unit) for (metric_name, unit), values in sorted(grouped_recovery.items())
    )
    return HealthSummary(
        start=start,
        end=end,
        available=bool(sleep_records or recovery_records),
        average_sleep_seconds=(
            sum(item.duration_seconds for item in sleep_records) / len(sleep_records) if sleep_records else None
        ),
        average_sleep_score=sum(scores) / len(scores) if scores else None,
        recovery_metrics=recovery_metrics,
    )


def trend_direction(previous: TrainingSummary, current: TrainingSummary) -> TrendDirection:
    if previous.training_load is None or current.training_load is None:
        return "flat"
    if current.training_load > previous.training_load:
        return "up"
    if current.training_load < previous.training_load:
        return "down"
    return "flat"


def summarize_trends(
    activities: Sequence[Activity],
    sleep: Sequence[SleepSession],
    recovery: Sequence[RecoverySignal],
    start: date,
    end: date,
    bucket: TrendBucket = TrendBucket.WEEK,
) -> TrendSnapshot:
    _validate_range(start, end)
    periods = tuple(_periods(start, end, bucket))
    return TrendSnapshot(
        start=start,
        end=end,
        bucket=bucket,
        training=tuple(summarize_training(activities, period_start, period_end) for period_start, period_end in periods),
        health=tuple(summarize_health(sleep, recovery, period_start, period_end) for period_start, period_end in periods),
    )


def _activities_between(activities: Sequence[Activity], start: date, end: date) -> tuple[Activity, ...]:
    return tuple(
        sorted(
            (item for item in activities if start <= item.local_date < end),
            key=lambda item: (item.started_at, item.external_id),
        )
    )


def _dates_between(start: date, end: date):
    current = start
    while current < end:
        yield current
        current += timedelta(days=1)


def _periods(start: date, end: date, bucket: TrendBucket):
    current = start
    step = timedelta(days=7 if bucket is TrendBucket.WEEK else 30 if bucket is TrendBucket.MONTH else 365)
    while current < end:
        period_end = min(current + step, end)
        yield current, period_end
        current = period_end


def _load(activity: Activity) -> float:
    return activity.duration_seconds / 60.0


def _validate_range(start: date, end: date) -> None:
    if start >= end:
        raise ValueError("start must be before end")
