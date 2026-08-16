from typing import Protocol

from strava_dashboard.domain.plan_models import CoachContext, PlanProposal


class CoachProvider(Protocol):
    async def propose(self, context: CoachContext) -> PlanProposal: ...
