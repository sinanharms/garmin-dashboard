from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Literal

DataFamily = Literal["activities", "sleep", "recovery"]
SyncStatus = Literal["succeeded", "failed"]

_DATA_FAMILIES = frozenset({"activities", "sleep", "recovery"})
_SYNC_STATUSES = frozenset({"succeeded", "failed"})


def _require_text(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty")


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _require_non_negative(name: str, value: int | float) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True, slots=True)
class SyncWindow:
    start: datetime | None
    end: datetime

    def __post_init__(self) -> None:
        if self.start is not None:
            _require_aware("start", self.start)
            if self.end <= self.start:
                raise ValueError("end must be after start")
        _require_aware("end", self.end)


@dataclass(frozen=True, slots=True)
class Activity:
    external_id: str
    activity_type: str
    started_at: datetime
    local_date: date
    duration_seconds: int
    distance_meters: float | None
    elevation_meters: float | None
    average_heart_rate: float | None
    max_heart_rate: float | None
    calories: float | None

    def __post_init__(self) -> None:
        _require_text("external_id", self.external_id)
        _require_text("activity_type", self.activity_type)
        _require_aware("started_at", self.started_at)
        _require_non_negative("duration_seconds", self.duration_seconds)


@dataclass(frozen=True, slots=True)
class SleepSession:
    external_id: str
    started_at: datetime
    ended_at: datetime
    local_date: date
    duration_seconds: int
    score: float | None

    def __post_init__(self) -> None:
        _require_text("external_id", self.external_id)
        _require_aware("started_at", self.started_at)
        _require_aware("ended_at", self.ended_at)
        _require_non_negative("duration_seconds", self.duration_seconds)
        if self.ended_at <= self.started_at:
            raise ValueError("ended_at must be after started_at")


@dataclass(frozen=True, slots=True)
class RecoverySignal:
    external_id: str
    local_date: date
    measured_at: datetime
    metric_name: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        _require_text("external_id", self.external_id)
        _require_text("metric_name", self.metric_name)
        _require_text("unit", self.unit)
        _require_aware("measured_at", self.measured_at)


@dataclass(frozen=True, slots=True)
class SyncCursor:
    data_family: DataFamily
    watermark: datetime

    def __post_init__(self) -> None:
        if self.data_family not in _DATA_FAMILIES:
            raise ValueError("data_family must identify exactly one supported family")
        _require_aware("watermark", self.watermark)


@dataclass(frozen=True, slots=True)
class SyncStageResult:
    data_family: DataFamily
    status: SyncStatus
    record_count: int
    error_code: str | None

    def __post_init__(self) -> None:
        if self.data_family not in _DATA_FAMILIES:
            raise ValueError("data_family must identify exactly one supported family")
        if self.status not in _SYNC_STATUSES:
            raise ValueError("status must be succeeded or failed")
        _require_non_negative("record_count", self.record_count)


@dataclass(frozen=True, slots=True)
class SyncRun:
    run_id: str
    started_at: datetime
    ended_at: datetime | None
    stages: tuple[SyncStageResult, ...]

    def __post_init__(self) -> None:
        _require_text("run_id", self.run_id)
        _require_aware("started_at", self.started_at)
        if self.ended_at is not None:
            _require_aware("ended_at", self.ended_at)
            if self.ended_at < self.started_at:
                raise ValueError("ended_at must not be before started_at")


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    start: date
    end: date
    activity_count: int
    duration_seconds: int
    distance_meters: float
    elevation_meters: float
    sport_counts: tuple[tuple[str, int], ...]
    training_load: float | None


@dataclass(frozen=True, slots=True)
class HealthSummary:
    start: date
    end: date
    available: bool
    average_sleep_seconds: float | None
    average_sleep_score: float | None
    recovery_metrics: tuple[tuple[str, float, str], ...]


@dataclass(frozen=True, slots=True)
class TrainingBlock:
    start: date
    end: date
    outcome: Activity
    activities: tuple[Activity, ...]
    summary: TrainingSummary


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    generated_at: datetime
    training: TrainingSummary
    health: HealthSummary
    recent_activities: tuple[Activity, ...]

    def __post_init__(self) -> None:
        _require_aware("generated_at", self.generated_at)


class TrendBucket(StrEnum):
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass(frozen=True, slots=True)
class TrendSnapshot:
    start: date
    end: date
    bucket: TrendBucket
    training: tuple[TrainingSummary, ...]
    health: tuple[HealthSummary, ...]
