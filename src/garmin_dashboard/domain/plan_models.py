from datetime import date, datetime

from pydantic import StrictInt, field_validator, model_validator

from garmin_dashboard.domain.models import DomainModel, HealthSummary, TrainingBlock, TrainingSummary


class Goal(DomainModel):
    goal_id: str
    description: str
    target_date: date

    @field_validator("goal_id", "description")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class Workout(DomainModel):
    workout_id: str
    scheduled_date: date
    activity_type: str
    duration_seconds: StrictInt
    intensity: str
    purpose: str
    explanation: str

    @field_validator("workout_id", "activity_type", "intensity", "purpose", "explanation")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("duration_seconds")
    @classmethod
    def require_non_negative(cls, value: StrictInt) -> StrictInt:
        if value < 0:
            raise ValueError("duration_seconds must be a non-negative integer")
        return value


class PlanConstraints(DomainModel):
    weekly_time_budget_seconds: StrictInt
    available_weekdays: tuple[StrictInt, ...]
    activity_preferences: tuple[str, ...]
    requirements: tuple[str, ...]

    @field_validator("weekly_time_budget_seconds")
    @classmethod
    def require_non_negative_budget(cls, value: StrictInt) -> StrictInt:
        if value < 0:
            raise ValueError("weekly_time_budget_seconds must be a non-negative integer")
        return value

    @field_validator("available_weekdays")
    @classmethod
    def validate_weekdays(cls, value: tuple[StrictInt, ...]) -> tuple[StrictInt, ...]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("available_weekdays must contain values from 0 through 6")
        return value

    @field_validator("activity_preferences", "requirements")
    @classmethod
    def require_text_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("constraint text must not be empty")
        return value

    @model_validator(mode="after")
    def reject_duplicate_weekdays(self) -> PlanConstraints:
        if len(set(self.available_weekdays)) != len(self.available_weekdays):
            raise ValueError("available_weekdays must not contain duplicates")
        return self


class PlanProposal(DomainModel):
    proposal_id: str
    goal_id: str
    week_start: date
    workouts: tuple[Workout, ...]
    explanation: str
    created_at: datetime

    @field_validator("proposal_id", "goal_id", "explanation")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class ValidatedPlan(DomainModel):
    proposal: PlanProposal
    validated_at: datetime

    @field_validator("validated_at")
    @classmethod
    def validated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("validated_at must be timezone-aware")
        return value


class CoachContext(DomainModel):
    goal: Goal
    constraints: PlanConstraints
    training: TrainingSummary
    health: HealthSummary
    preceding_block: TrainingBlock | None
