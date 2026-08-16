from dataclasses import dataclass
from datetime import date, datetime

from strava_dashboard.domain.models import (
    HealthSummary,
    TrainingBlock,
    TrainingSummary,
    _require_aware,
    _require_non_negative,
    _require_text,
)


@dataclass(frozen=True, slots=True)
class Goal:
    goal_id: str
    description: str
    target_date: date

    def __post_init__(self) -> None:
        _require_text("goal_id", self.goal_id)
        _require_text("description", self.description)


@dataclass(frozen=True, slots=True)
class Workout:
    workout_id: str
    scheduled_date: date
    activity_type: str
    duration_seconds: int
    intensity: str
    purpose: str
    explanation: str

    def __post_init__(self) -> None:
        _require_text("workout_id", self.workout_id)
        _require_text("activity_type", self.activity_type)
        _require_text("intensity", self.intensity)
        _require_text("purpose", self.purpose)
        _require_text("explanation", self.explanation)
        _require_non_negative("duration_seconds", self.duration_seconds)


@dataclass(frozen=True, slots=True)
class PlanConstraints:
    weekly_time_budget_seconds: int
    available_weekdays: tuple[int, ...]
    activity_preferences: tuple[str, ...]
    requirements: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_non_negative("weekly_time_budget_seconds", self.weekly_time_budget_seconds)
        if any(day < 0 or day > 6 for day in self.available_weekdays):
            raise ValueError("available_weekdays must contain values from 0 through 6")


@dataclass(frozen=True, slots=True)
class PlanProposal:
    proposal_id: str
    goal_id: str
    week_start: date
    workouts: tuple[Workout, ...]
    explanation: str
    created_at: datetime

    def __post_init__(self) -> None:
        _require_text("proposal_id", self.proposal_id)
        _require_text("goal_id", self.goal_id)
        _require_text("explanation", self.explanation)
        _require_aware("created_at", self.created_at)


@dataclass(frozen=True, slots=True)
class ValidatedPlan:
    proposal: PlanProposal
    validated_at: datetime

    def __post_init__(self) -> None:
        _require_aware("validated_at", self.validated_at)


@dataclass(frozen=True, slots=True)
class CoachContext:
    goal: Goal
    constraints: PlanConstraints
    training: TrainingSummary
    health: HealthSummary
    preceding_block: TrainingBlock | None
