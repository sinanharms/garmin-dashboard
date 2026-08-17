from collections.abc import Sequence
from typing import Protocol

from garmin_dashboard.domain.models import Activity, RecoverySignal, SleepSession, SyncWindow


class GarminSourceError(RuntimeError):
    """Raised when a Garmin source cannot return validated domain records."""


class GarminDataSource(Protocol):
    async def fetch_activities(self, window: SyncWindow) -> Sequence[Activity]: ...

    async def fetch_sleep(self, window: SyncWindow) -> Sequence[SleepSession]: ...

    async def fetch_recovery(self, window: SyncWindow) -> Sequence[RecoverySignal]: ...
