import asyncio
import json
from collections.abc import Mapping
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from strava_dashboard.adapters.garmin_mcp import session as session_module
from strava_dashboard.adapters.garmin_mcp.adapter import GarminMcpAdapter
from strava_dashboard.adapters.garmin_mcp.mapping import GarminDataError
from strava_dashboard.adapters.garmin_mcp.session import McpSessionError, StdioMcpSessionFactory
from strava_dashboard.domain.models import Activity, RecoverySignal, SleepSession, SyncWindow

FIXTURE_DIR = Path(__file__).parent / "fixtures"
BERLIN_OFFSET = timezone(timedelta(hours=2))


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text())


class FakeSession:
    def __init__(
        self,
        responses: Mapping[str, Mapping[str, object]],
        error: Exception | None = None,
    ) -> None:
        self.responses = responses
        self.error = error
        self.calls: list[tuple[str, Mapping[str, object]]] = []
        self.closed = False

    async def call_tool(self, name: str, arguments: Mapping[str, object]) -> Mapping[str, object]:
        self.calls.append((name, arguments))
        if self.error is not None:
            raise self.error
        return self.responses[name]

    async def close(self) -> None:
        self.closed = True


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def open(self) -> FakeSession:
        return self.session


def sync_window() -> SyncWindow:
    return SyncWindow(
        start=datetime(2024, 1, 15, tzinfo=BERLIN_OFFSET),
        end=datetime(2024, 1, 15, 23, 59, tzinfo=BERLIN_OFFSET),
    )


def test_fetch_activities_maps_fixture_and_exact_tool_arguments() -> None:
    session = FakeSession({"get_activities_by_date": load_fixture("garmin_activity.json")})
    adapter = GarminMcpAdapter(FakeSessionFactory(session))

    activities = asyncio.run(adapter.fetch_activities(sync_window()))

    assert activities == (
        Activity(
            external_id="12345678901",
            activity_type="running",
            started_at=datetime(2024, 1, 15, 7, tzinfo=BERLIN_OFFSET),
            local_date=datetime(2024, 1, 15).date(),
            duration_seconds=1800,
            distance_meters=5000.0,
            elevation_meters=42.5,
            average_heart_rate=145.0,
            max_heart_rate=165.0,
            calories=350.0,
        ),
    )
    assert session.calls == [
        (
            "get_activities_by_date",
            {
                "start_date": "2024-01-15",
                "end_date": "2024-01-15",
                "page": 0,
                "page_size": 200,
            },
        )
    ]
    assert session.closed


def test_fetch_sleep_maps_fixture_and_exact_tool_arguments() -> None:
    session = FakeSession({"get_sleep_summary": load_fixture("garmin_sleep.json")})
    adapter = GarminMcpAdapter(FakeSessionFactory(session))

    sleep = asyncio.run(adapter.fetch_sleep(sync_window()))

    assert sleep == (
        SleepSession(
            external_id="sleep:2024-01-15",
            started_at=datetime(2024, 1, 15, tzinfo=UTC),
            ended_at=datetime(2024, 1, 15, 8, tzinfo=UTC),
            local_date=datetime(2024, 1, 15).date(),
            duration_seconds=28800,
            score=85.0,
        ),
    )
    assert session.calls == [("get_sleep_summary", {"date": "2024-01-15"})]
    assert session.closed


def test_fetch_recovery_maps_each_fixture_metric() -> None:
    session = FakeSession({"get_hrv_data": load_fixture("garmin_recovery.json")})
    adapter = GarminMcpAdapter(FakeSessionFactory(session))

    signals = asyncio.run(adapter.fetch_recovery(sync_window()))

    assert all(isinstance(signal, RecoverySignal) for signal in signals)
    assert {signal.metric_name: signal.value for signal in signals} == {
        "last_night_avg_hrv_ms": 48.0,
        "last_night_5min_high_hrv_ms": 52.0,
        "weekly_avg_hrv_ms": 45.0,
        "baseline_balanced_low_ms": 40.0,
        "baseline_balanced_upper_ms": 55.0,
        "baseline_low_upper_ms": 35.0,
    }
    assert {signal.external_id for signal in signals} == {
        f"hrv:2024-01-15:{metric_name}" for metric_name in {signal.metric_name for signal in signals}
    }
    assert {signal.measured_at for signal in signals} == {datetime(2024, 1, 15, 7, 30, tzinfo=BERLIN_OFFSET)}
    assert {signal.local_date.isoformat() for signal in signals} == {"2024-01-15"}
    assert {signal.unit for signal in signals} == {"ms"}
    assert session.calls == [("get_hrv_data", {"date": "2024-01-15", "return_timeseries": False})]
    assert session.closed


def test_missing_required_activity_field_raises_redacted_data_error_and_closes() -> None:
    payload = deepcopy(load_fixture("garmin_activity.json"))
    activity = cast(dict[str, object], cast(list[object], payload["activities"])[0])
    del activity["id"]  # type: ignore[index]
    activity["private_marker"] = "RAW-HEALTH-SECRET"  # type: ignore[index]
    session = FakeSession({"get_activities_by_date": payload})
    adapter = GarminMcpAdapter(FakeSessionFactory(session))

    with pytest.raises(GarminDataError) as error:
        asyncio.run(adapter.fetch_activities(sync_window()))

    assert "RAW-HEALTH-SECRET" not in str(error.value)
    assert session.closed


def test_mcp_exception_becomes_redacted_data_error_and_closes() -> None:
    session = FakeSession({}, error=RuntimeError("RAW-HEALTH-SECRET"))
    adapter = GarminMcpAdapter(FakeSessionFactory(session))

    with pytest.raises(GarminDataError) as error:
        asyncio.run(adapter.fetch_sleep(sync_window()))

    assert "RAW-HEALTH-SECRET" not in str(error.value)
    assert session.closed


def test_stdio_factory_inherits_environment_sets_upstream_token_path_and_closes(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    @asynccontextmanager
    async def fake_stdio(parameters: object, errlog: object):
        captured["parameters"] = parameters
        captured["errlog"] = errlog
        yield "read", "write"

    class FakeSdkSession:
        def __init__(self, *streams: object) -> None:
            captured["streams"] = streams

        async def __aenter__(self) -> FakeSdkSession:
            return self

        async def __aexit__(self, *exc_info: object) -> None:
            captured["sdk_closed"] = True

        async def initialize(self) -> None:
            captured["initialized"] = True

        async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
            return SimpleNamespace(is_error=False, content=[], structured_content={"ok": True})

    monkeypatch.setenv("TASK3_PARENT_SENTINEL", "inherited")
    monkeypatch.setattr(session_module, "stdio_client", fake_stdio)
    monkeypatch.setattr(session_module, "ClientSession", FakeSdkSession)

    async def exercise() -> Mapping[str, object]:
        session = await StdioMcpSessionFactory("garmin-mcp", tmp_path / "tokens", 30).open()
        result = await session.call_tool("fixture_tool", {})
        await session.close()
        return result

    assert asyncio.run(exercise()) == {"ok": True}
    parameters = captured["parameters"]
    assert parameters.command == "garmin-mcp"
    assert parameters.env["TASK3_PARENT_SENTINEL"] == "inherited"
    assert parameters.env["GARMINTOKENS"] == str(tmp_path / "tokens")
    assert captured["initialized"]
    assert captured["sdk_closed"]


def test_stdio_session_times_out_without_exposing_sdk_error(monkeypatch, tmp_path: Path) -> None:
    @asynccontextmanager
    async def fake_stdio(parameters: object, errlog: object):
        yield "read", "write"

    class SlowSdkSession:
        def __init__(self, *streams: object) -> None:
            pass

        async def __aenter__(self) -> SlowSdkSession:
            return self

        async def __aexit__(self, *exc_info: object) -> None:
            pass

        async def initialize(self) -> None:
            pass

        async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
            await asyncio.sleep(1)
            raise RuntimeError("RAW-HEALTH-SECRET")

    monkeypatch.setattr(session_module, "stdio_client", fake_stdio)
    monkeypatch.setattr(session_module, "ClientSession", SlowSdkSession)

    async def exercise() -> None:
        session = await StdioMcpSessionFactory("garmin-mcp", tmp_path / "tokens", 0).open()
        try:
            await session.call_tool("fixture_tool", {})
        finally:
            await session.close()

    with pytest.raises(McpSessionError) as error:
        asyncio.run(exercise())

    assert "RAW-HEALTH-SECRET" not in str(error.value)
