from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from strava_dashboard.domain.models import Activity, RecoverySignal, SleepSession, SyncCursor, SyncRun
from strava_dashboard.domain.plan_models import Goal, ValidatedPlan


class ActivityStore(Protocol):
    def cursor(self) -> SyncCursor | None: ...

    def upsert_batch(self, records: Sequence[Activity], cursor: SyncCursor) -> int:
        """Persist records and advance their cursor atomically."""
        ...

    def between(self, start: datetime, end: datetime) -> Sequence[Activity]: ...


class SleepStore(Protocol):
    def cursor(self) -> SyncCursor | None: ...

    def upsert_batch(self, records: Sequence[SleepSession], cursor: SyncCursor) -> int:
        """Persist records and advance their cursor atomically."""
        ...

    def between(self, start: datetime, end: datetime) -> Sequence[SleepSession]: ...


class RecoveryStore(Protocol):
    def cursor(self) -> SyncCursor | None: ...

    def upsert_batch(self, records: Sequence[RecoverySignal], cursor: SyncCursor) -> int:
        """Persist records and advance their cursor atomically."""
        ...

    def between(self, start: datetime, end: datetime) -> Sequence[RecoverySignal]: ...


class SyncRunStore(Protocol):
    def save(self, run: SyncRun) -> None: ...

    def get(self, run_id: str) -> SyncRun | None: ...

    def recent(self, limit: int) -> Sequence[SyncRun]: ...


class GoalStore(Protocol):
    def save(self, goal: Goal) -> None: ...

    def current(self) -> Goal | None: ...


class PlanStore(Protocol):
    def save(self, plan: ValidatedPlan) -> None: ...

    def current(self) -> ValidatedPlan | None: ...


class BackupStore(Protocol):
    def create(self) -> str: ...

    def restore(self, backup_id: str) -> None: ...

    def delete(self, backup_id: str) -> None: ...
