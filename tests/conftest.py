from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from strava_dashboard.adapters.sqlite.activity_store import SQLiteActivityStore
from strava_dashboard.adapters.sqlite.connection import open_connection
from strava_dashboard.adapters.sqlite.recovery_store import SQLiteRecoveryStore
from strava_dashboard.adapters.sqlite.sleep_store import SQLiteSleepStore


@pytest.fixture
def utc_now() -> datetime:
    return datetime(2026, 8, 16, 6, 30, tzinfo=UTC)


class SQLiteStorageBundle(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    activity: SQLiteActivityStore
    sleep: SQLiteSleepStore
    recovery: SQLiteRecoveryStore


@contextmanager
def sqlite_storage_factory(path: Path) -> Iterator[SQLiteStorageBundle]:
    connection = open_connection(path)
    try:
        yield SQLiteStorageBundle(
            activity=SQLiteActivityStore(connection),
            sleep=SQLiteSleepStore(connection),
            recovery=SQLiteRecoveryStore(connection),
        )
    finally:
        connection.close()


@pytest.fixture
def storage_factory() -> Callable[[Path], AbstractContextManager[SQLiteStorageBundle]]:
    return sqlite_storage_factory
