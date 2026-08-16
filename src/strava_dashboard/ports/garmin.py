from collections.abc import Sequence
from typing import Protocol

from strava_dashboard.domain.models import Activity, RecoverySignal, SleepSession, SyncWindow


class GarminDataSource(Protocol):
    async def fetch_activities(self, window: SyncWindow) -> Sequence[Activity]: ...

    async def fetch_sleep(self, window: SyncWindow) -> Sequence[SleepSession]: ...

    async def fetch_recovery(self, window: SyncWindow) -> Sequence[RecoverySignal]: ...
