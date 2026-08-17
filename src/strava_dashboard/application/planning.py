from datetime import UTC, datetime, timedelta

from strava_dashboard.domain.plan_models import CoachContext, PlanConstraints, PlanProposal, ValidatedPlan
from strava_dashboard.ports.coach import CoachProvider
from strava_dashboard.ports.storage import PlanStore


class PlanValidationError(ValueError):
    """Raised when a provider proposal violates user-editable plan rules."""


class PlanValidator:
    def validate(self, proposal: PlanProposal, constraints: PlanConstraints) -> ValidatedPlan:
        normalized = PlanProposal.model_validate(proposal)
        self._validate_week(normalized)
        self._validate_workouts(normalized, constraints)
        return ValidatedPlan(proposal=normalized, validated_at=datetime.now(UTC))

    @staticmethod
    def _validate_week(proposal: PlanProposal) -> None:
        if proposal.week_start.weekday() != 0:
            raise PlanValidationError("week_start must be a Monday")
        week_end = proposal.week_start + timedelta(days=7)
        if any(not proposal.week_start <= workout.scheduled_date < week_end for workout in proposal.workouts):
            raise PlanValidationError("workout date must be inside proposal week")
        scheduled_days = tuple(workout.scheduled_date for workout in proposal.workouts)
        if len(set(scheduled_days)) != len(scheduled_days):
            raise PlanValidationError("duplicate scheduled day")

    @staticmethod
    def _validate_workouts(proposal: PlanProposal, constraints: PlanConstraints) -> None:
        total_seconds = sum(workout.duration_seconds for workout in proposal.workouts)
        if total_seconds > constraints.weekly_time_budget_seconds:
            raise PlanValidationError("plan exceeds weekly time budget")
        for workout in proposal.workouts:
            if workout.scheduled_date.weekday() not in constraints.available_weekdays:
                raise PlanValidationError("workout uses unavailable weekday")
            if constraints.activity_preferences and workout.activity_type not in constraints.activity_preferences:
                raise PlanValidationError("workout violates activity preference")
        plan_text = " ".join(
            (
                proposal.explanation,
                *(workout.purpose for workout in proposal.workouts),
                *(workout.explanation for workout in proposal.workouts),
            )
        ).casefold()
        missing = tuple(requirement for requirement in constraints.requirements if requirement.casefold() not in plan_text)
        if missing:
            raise PlanValidationError(f"plan does not address requirement: {missing[0]}")


class PlanningService:
    def __init__(self, provider: CoachProvider, plans: PlanStore, validator: PlanValidator | None = None) -> None:
        self._provider = provider
        self._plans = plans
        self._validator = validator or PlanValidator()

    async def propose(self, context: CoachContext) -> ValidatedPlan:
        response = await self._provider.propose(context)
        proposal = self._validate_provider_response(response)
        return self._validator.validate(proposal, context.constraints)

    def accept(self, plan: ValidatedPlan) -> ValidatedPlan:
        self._plans.save(plan)
        return plan

    def edit(self, proposal: PlanProposal, constraints: PlanConstraints) -> ValidatedPlan:
        plan = self._validator.validate(proposal, constraints)
        self._plans.save(plan)
        return plan

    def skip(self) -> ValidatedPlan | None:
        return self._plans.current()

    @staticmethod
    def _validate_provider_response(response: object) -> PlanProposal:
        return PlanProposal.model_validate(response)
