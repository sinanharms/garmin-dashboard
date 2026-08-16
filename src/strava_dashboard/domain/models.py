from datetime import date, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, StrictInt, field_validator, model_validator

DataFamily = Literal["activities", "sleep", "recovery"]
SyncStatus = Literal["succeeded", "failed"]


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("external_id", "activity_type", "metric_name", "unit", "run_id", check_fields=False)
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("started_at", "ended_at", "measured_at", "watermark", check_fields=False)
    @classmethod
    def require_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("datetime must be timezone-aware")
        return value

    @field_validator("duration_seconds", "record_count", "activity_count", check_fields=False)
    @classmethod
    def require_non_negative_int(cls, value: StrictInt) -> StrictInt:
        if value < 0:
            raise ValueError("value must be a non-negative integer")
        return value


class SyncWindow(DomainModel):
    start: datetime | None
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("datetime must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.start is not None and self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class Activity(DomainModel):
    external_id: str
    activity_type: str
    started_at: datetime
    local_date: date
    duration_seconds: StrictInt
    distance_meters: float | None
    elevation_meters: float | None
    average_heart_rate: float | None
    max_heart_rate: float | None
    calories: float | None


class SleepSession(DomainModel):
    external_id: str
    started_at: datetime
    ended_at: datetime
    local_date: date
    duration_seconds: StrictInt
    score: float | None

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.ended_at <= self.started_at:
            raise ValueError("ended_at must be after started_at")
        return self


class RecoverySignal(DomainModel):
    external_id: str
    local_date: date
    measured_at: datetime
    metric_name: str
    value: float
    unit: str


class SyncCursor(DomainModel):
    data_family: DataFamily
    watermark: datetime


class ActivityCursor(DomainModel):
    data_family: Literal["activities"] = "activities"
    watermark: datetime


class SleepCursor(DomainModel):
    data_family: Literal["sleep"] = "sleep"
    watermark: datetime


class RecoveryCursor(DomainModel):
    data_family: Literal["recovery"] = "recovery"
    watermark: datetime


class SyncStageResult(DomainModel):
    data_family: DataFamily
    status: SyncStatus
    record_count: StrictInt
    error_code: str | None


class SyncRun(DomainModel):
    run_id: str
    started_at: datetime
    ended_at: datetime | None
    stages: tuple[SyncStageResult, ...]

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at must not be before started_at")
        return self


class TrainingSummary(DomainModel):
    start: date
    end: date
    activity_count: StrictInt
    duration_seconds: StrictInt
    distance_meters: float
    elevation_meters: float
    sport_counts: tuple[tuple[str | int, ...], ...]
    training_load: float | None


class HealthSummary(DomainModel):
    start: date
    end: date
    available: bool
    average_sleep_seconds: float | None
    average_sleep_score: float | None
    recovery_metrics: tuple[tuple[str | float, ...], ...]


class TrainingBlock(DomainModel):
    start: date
    end: date
    outcome: Activity
    activities: tuple[Activity, ...]
    summary: TrainingSummary


class DashboardSnapshot(DomainModel):
    generated_at: datetime
    training: TrainingSummary
    health: HealthSummary
    recent_activities: tuple[Activity, ...]

    @field_validator("generated_at")
    @classmethod
    def generated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        return value


class TrendBucket(StrEnum):
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class TrendSnapshot(DomainModel):
    start: date
    end: date
    bucket: TrendBucket
    training: tuple[TrainingSummary, ...]
    health: tuple[HealthSummary, ...]
