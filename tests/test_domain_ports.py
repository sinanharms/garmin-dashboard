from pathlib import Path
from typing import get_args, get_type_hints


def test_ports_expose_replaceable_protocols() -> None:
    from garmin_dashboard.ports.coach import CoachProvider
    from garmin_dashboard.ports.garmin import GarminDataSource
    from garmin_dashboard.ports.storage import (
        ActivityStore,
        BackupStore,
        GoalStore,
        PlanStore,
        RecoveryStore,
        SleepStore,
        SyncRunStore,
    )

    protocols = {
        GarminDataSource: {"fetch_activities", "fetch_sleep", "fetch_recovery"},
        ActivityStore: {"cursor", "upsert_batch", "between"},
        SleepStore: {"cursor", "upsert_batch", "between"},
        RecoveryStore: {"cursor", "upsert_batch", "between"},
        SyncRunStore: {"save", "get", "recent"},
        GoalStore: {"save", "current"},
        PlanStore: {"save", "current"},
        BackupStore: {"create", "restore", "delete"},
        CoachProvider: {"propose"},
    }

    for protocol, methods in protocols.items():
        assert protocol._is_protocol  # ty: ignore[unresolved-attribute]
        assert methods <= set(protocol.__dict__)


def test_storage_ports_own_their_cursor_family() -> None:
    from garmin_dashboard.domain.models import ActivityCursor, RecoveryCursor, SleepCursor
    from garmin_dashboard.ports.storage import ActivityStore, RecoveryStore, SleepStore

    assert ActivityCursor in get_args(get_type_hints(ActivityStore.cursor)["return"])
    assert get_type_hints(ActivityStore.upsert_batch)["cursor"] is ActivityCursor
    assert SleepCursor in get_args(get_type_hints(SleepStore.cursor)["return"])
    assert get_type_hints(SleepStore.upsert_batch)["cursor"] is SleepCursor
    assert RecoveryCursor in get_args(get_type_hints(RecoveryStore.cursor)["return"])
    assert get_type_hints(RecoveryStore.upsert_batch)["cursor"] is RecoveryCursor


def test_domain_and_ports_have_no_provider_or_storage_imports() -> None:
    project_root = Path(__file__).parents[1]
    files = (
        project_root / "src/garmin_dashboard/domain/models.py",
        project_root / "src/garmin_dashboard/domain/plan_models.py",
        project_root / "src/garmin_dashboard/ports/garmin.py",
        project_root / "src/garmin_dashboard/ports/storage.py",
        project_root / "src/garmin_dashboard/ports/coach.py",
    )
    forbidden = ("fastapi", "sqlite", "mcp", "openai", "anthropic")

    for path in files:
        source = path.read_text().lower()
        assert not any(name in source for name in forbidden), path
