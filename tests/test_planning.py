import asyncio
from datetime import UTC, date, datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError

from strava_dashboard.application.planning import PlanningService, PlanValidationError, PlanValidator
from strava_dashboard.domain.models import HealthSummary, TrainingSummary
from strava_dashboard.domain.plan_models import (
    CoachContext,
    Goal,
    PlanConstraints,
    PlanProposal,
    ValidatedPlan,
    Workout,
)
from strava_dashboard.ports.coach import CoachProviderUnavailable, UnavailableCoachProvider

NOW = datetime(2026, 8, 16, 8, tzinfo=UTC)


def constraints(**updates: Any) -> PlanConstraints:
    values: dict[str, Any] = {
        "weekly_time_budget_seconds": 7200,
        "available_weekdays": (0, 2, 4),
        "activity_preferences": ("running",),
        "requirements": ("easy week",),
    }
    values.update(updates)
    return PlanConstraints(**values)


def workout(identifier: str = "workout-1", *, scheduled_date: date = date(2026, 8, 17), duration: int = 3600) -> Workout:
    return Workout(
        workout_id=identifier,
        scheduled_date=scheduled_date,
        activity_type="running",
        duration_seconds=duration,
        intensity="easy",
        purpose="easy week",
        explanation="Build aerobic consistency",
    )


def proposal(*workouts: Workout, explanation: str = "easy week") -> PlanProposal:
    return PlanProposal(
        proposal_id="proposal-1",
        goal_id="goal-1",
        week_start=date(2026, 8, 17),
        workouts=workouts,
        explanation=explanation,
        created_at=NOW,
    )


def context(health: HealthSummary | None = None, **constraint_updates: Any) -> CoachContext:
    return CoachContext(
        goal=Goal(goal_id="goal-1", description="Run 10 km", target_date=date(2026, 10, 1)),
        constraints=constraints(**constraint_updates),
        training=TrainingSummary(
            start=date(2026, 8, 10),
            end=date(2026, 8, 17),
            activity_count=2,
            duration_seconds=5400,
            distance_meters=12_000.0,
            elevation_meters=100.0,
            sport_counts=(("running", 2),),
            training_load=90.0,
        ),
        health=health
        or HealthSummary(
            start=date(2026, 8, 10),
            end=date(2026, 8, 17),
            available=True,
            average_sleep_seconds=28_800.0,
            average_sleep_score=82.0,
            recovery_metrics=(("body_battery", 75.0, "percent"),),
        ),
        preceding_block=None,
    )


class FakeProvider:
    def __init__(self, response: object) -> None:
        self.response = response
        self.context: CoachContext | None = None

    async def propose(self, context: CoachContext) -> PlanProposal:
        self.context = context
        return cast(PlanProposal, self.response)


class FailingProvider:
    async def propose(self, context: CoachContext) -> PlanProposal:
        raise RuntimeError("provider unavailable")


class MemoryPlans:
    def __init__(self, current: ValidatedPlan | None = None) -> None:
        self.value = current

    def save(self, plan: ValidatedPlan) -> None:
        self.value = plan

    def current(self) -> ValidatedPlan | None:
        return self.value


def test_validator_accepts_valid_plan_and_rejects_duplicate_days() -> None:
    validator = PlanValidator()
    valid = validator.validate(proposal(workout(), workout("workout-2", scheduled_date=date(2026, 8, 19))), constraints())

    assert valid.proposal.workouts[0].activity_type == "running"
    with pytest.raises(PlanValidationError, match="duplicate scheduled day"):
        validator.validate(proposal(workout(), workout("workout-2")), constraints())


def test_provider_payload_is_validated_and_unknown_fields_are_rejected() -> None:
    raw = proposal(workout()).model_dump()
    raw["workouts"][0]["unexpected"] = "not allowed"
    service = PlanningService(FakeProvider(raw), MemoryPlans())

    with pytest.raises(ValidationError):
        asyncio.run(service.propose(context()))


def test_malformed_provider_date_is_rejected() -> None:
    raw = proposal(workout()).model_dump()
    raw["workouts"][0]["scheduled_date"] = "not-a-date"
    service = PlanningService(FakeProvider(raw), MemoryPlans())

    with pytest.raises(ValidationError, match="date"):
        asyncio.run(service.propose(context()))


def test_negative_duration_from_provider_is_rejected() -> None:
    raw = proposal(workout()).model_dump()
    raw["workouts"][0]["duration_seconds"] = -1
    service = PlanningService(FakeProvider(raw), MemoryPlans())

    with pytest.raises(ValidationError, match="duration_seconds"):
        asyncio.run(service.propose(context()))


def test_workout_outside_proposal_week_is_rejected() -> None:
    candidate = proposal(workout(scheduled_date=date(2026, 8, 24)))
    validator = PlanValidator()

    with pytest.raises(PlanValidationError, match="week"):
        validator.validate(candidate, constraints())


def test_time_budget_unavailable_day_and_explicit_activity_constraints_are_rejected() -> None:
    validator = PlanValidator()
    with pytest.raises(PlanValidationError, match="time budget"):
        validator.validate(proposal(workout(duration=7201)), constraints())
    with pytest.raises(PlanValidationError, match="unavailable weekday"):
        validator.validate(proposal(workout(scheduled_date=date(2026, 8, 18))), constraints())
    cycling = workout().model_copy(update={"activity_type": "cycling"})
    with pytest.raises(PlanValidationError, match="activity preference"):
        validator.validate(proposal(cycling), constraints())


def test_accept_edit_and_skip_preserve_plan_on_failure() -> None:
    current = PlanValidator().validate(proposal(workout("old")), constraints())
    plans = MemoryPlans(current)
    service = PlanningService(FakeProvider(proposal(workout())), plans)

    accepted = service.accept(current)
    edited = service.edit(proposal(workout("edited", scheduled_date=date(2026, 8, 19))), constraints())

    assert accepted == current
    assert edited.proposal.workouts[0].workout_id == "edited"
    assert service.skip() == edited
    with pytest.raises(PlanValidationError):
        service.edit(proposal(workout("invalid", duration=7201)), constraints())
    assert plans.current() == edited


def test_provider_failure_preserves_current_plan_and_health_is_context_only() -> None:
    current = PlanValidator().validate(proposal(workout("old")), constraints())
    plans = MemoryPlans(current)
    provider = FakeProvider(proposal(workout()))
    service = PlanningService(provider, plans)
    health = context().health

    result = asyncio.run(service.propose(context(health)))

    assert result.proposal.workouts[0].purpose == "easy week"
    assert provider.context is not None
    assert provider.context.health == health
    assert "medical" not in repr(provider.context).lower()
    assert plans.current() == current


def test_unavailable_provider_is_explicit_and_has_no_fallback() -> None:
    current = PlanValidator().validate(proposal(workout("old")), constraints())
    plans = MemoryPlans(current)
    service = PlanningService(UnavailableCoachProvider(), plans)

    with pytest.raises(CoachProviderUnavailable, match="unavailable"):
        asyncio.run(service.propose(context()))
    assert plans.current() == current


def test_provider_failure_preserves_current_plan() -> None:
    current = PlanValidator().validate(proposal(workout("old")), constraints())
    plans = MemoryPlans(current)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        asyncio.run(PlanningService(FailingProvider(), plans).propose(context()))
    assert plans.current() == current
