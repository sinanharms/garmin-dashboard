import asyncio
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from garmin_dashboard import worker
from garmin_dashboard.config.settings import Settings
from garmin_dashboard.domain.models import SyncRun


class FakeService:
    def __init__(self, failure: BaseException | None = None) -> None:
        self.failure = failure

    async def run(self, _window: object) -> SyncRun:
        if self.failure is not None:
            raise self.failure
        now = datetime(2026, 8, 17, tzinfo=UTC)
        return SyncRun(run_id="run-1", started_at=now, ended_at=now + timedelta(seconds=1), stages=())


def test_sync_window_includes_initial_history() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)

    window = worker.sync_window(now)

    assert window.start == now - timedelta(days=30)
    assert window.end == now


@pytest.mark.parametrize("failure", [None, RuntimeError("sync failed")])
def test_run_once_closes_connection_on_success_and_failure(monkeypatch, failure: BaseException | None) -> None:
    connection = sqlite3.connect(":memory:")
    service = FakeService(failure)
    settings = cast(Settings, SimpleNamespace(database_path=Path("unused.sqlite")))
    monkeypatch.setattr(worker, "open_connection", lambda _path: connection)
    monkeypatch.setattr(worker, "build_sync_service", lambda _settings, *, connection: service)

    if failure is None:
        assert asyncio.run(worker.run_once(settings)).run_id == "run-1"
    else:
        with pytest.raises(RuntimeError, match="sync failed"):
            asyncio.run(worker.run_once(settings))

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")
