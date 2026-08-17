from typing import Protocol

from strava_dashboard.domain.plan_models import CoachContext, PlanProposal


class CoachProviderUnavailable(RuntimeError):
    """Raised when no concrete coach provider has been configured."""


class CoachProvider(Protocol):
    async def propose(self, context: CoachContext) -> PlanProposal: ...


class UnavailableCoachProvider:
    async def propose(self, context: CoachContext) -> PlanProposal:
        raise CoachProviderUnavailable("coach provider unavailable")
