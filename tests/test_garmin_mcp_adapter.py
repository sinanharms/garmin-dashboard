import asyncio
import json
from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from strava_dashboard.adapters.garmin_mcp.adapter import GarminMcpAdapter
from strava_dashboard.adapters.garmin_mcp.mapping import GarminDataError
from strava_dashboard.adapters.garmin_mcp.session import McpSessionError
from strava_dashboard.domain.models import Activity, RecoverySignal, SleepSession, SyncWindow

FIXTURE_DIR = Path(__file__).parent / "fixtures"
BERLIN_OFFSET = timezone(timedelta(hours=2))


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text())


class FakeSession:
    def __init__(
        self,
        responses: Mapping[str, Mapping[str, object] | str | list[Mapping[str, object]] | list[str]],
        error: BaseException | None = None,
        close_error: Exception | None = None,
    ) -> None:
        self.responses = responses
        self.error = error
        self.close_error = close_error
        self.calls: list[tuple[str, Mapping[str, object]]] = []
        self.response_indexes: dict[str, int] = {}
        self.closed = False

    async def call_tool(self, name: str, arguments: Mapping[str, object]) -> Mapping[str, object] | str:
        self.calls.append((name, arguments))
        if self.error is not None:
            raise self.error
        response = self.responses[name]
        if isinstance(response, list):
            index = self.response_indexes.get(name, 0)
            self.response_indexes[name] = index + 1
            return cast(Mapping[str, object] | str, response[index])
        return response

    async def close(self) -> None:
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def open(self) -> FakeSession:
        return self.session


def sync_window(end_day: int = 15) -> SyncWindow:
    return SyncWindow(
        start=datetime(2024, 1, 15, tzinfo=BERLIN_OFFSET),
        end=datetime(2024, 1, end_day, 23, 59, tzinfo=BERLIN_OFFSET),
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


def test_fetch_activities_uses_full_window_and_follows_pagination() -> None:
    first_page = load_fixture("garmin_activity.json")
    first_page["has_more"] = True
    first_page["next_page"] = 1
    second_page = deepcopy(first_page)
    second_page["has_more"] = False
    del second_page["next_page"]
    session = FakeSession({"get_activities_by_date": [first_page, second_page]})

    activities = asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_activities(sync_window(17)))

    assert len(activities) == 2
    assert session.calls == [
        (
            "get_activities_by_date",
            {"start_date": "2024-01-15", "end_date": "2024-01-17", "page": 0, "page_size": 200},
        ),
        (
            "get_activities_by_date",
            {"start_date": "2024-01-15", "end_date": "2024-01-17", "page": 1, "page_size": 200},
        ),
    ]
    assert session.closed


def test_fetch_sleep_requests_every_local_date_and_preserves_requested_date() -> None:
    session = FakeSession(
        {
            "get_sleep_summary": [
                load_fixture("garmin_sleep_boundary.json"),
                load_fixture("garmin_sleep.json"),
                load_fixture("garmin_sleep.json"),
            ]
        }
    )

    sleep = asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_sleep(sync_window(17)))

    assert tuple(item.local_date.isoformat() for item in sleep) == ("2024-01-15", "2024-01-16", "2024-01-17")
    assert sleep[0].started_at == datetime(2024, 1, 14, 23, 30, tzinfo=UTC)
    assert session.calls == [
        ("get_sleep_summary", {"date": "2024-01-15"}),
        ("get_sleep_summary", {"date": "2024-01-16"}),
        ("get_sleep_summary", {"date": "2024-01-17"}),
    ]
    assert session.closed


def test_fetch_sleep_treats_upstream_no_data_reply_as_empty() -> None:
    session = FakeSession({"get_sleep_summary": "No sleep summary found for 2024-01-15"})

    sleep = asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_sleep(sync_window()))

    assert sleep == ()
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


def test_fetch_recovery_requests_every_local_date() -> None:
    responses: list[Mapping[str, object]] = []
    for day in range(15, 18):
        response = load_fixture("garmin_recovery.json")
        response["date"] = f"2024-01-{day}"
        responses.append(response)
    session = FakeSession({"get_hrv_data": responses})

    signals = asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_recovery(sync_window(17)))

    assert {signal.local_date.isoformat() for signal in signals} == {"2024-01-15", "2024-01-16", "2024-01-17"}
    assert session.calls == [
        ("get_hrv_data", {"date": "2024-01-15", "return_timeseries": False}),
        ("get_hrv_data", {"date": "2024-01-16", "return_timeseries": False}),
        ("get_hrv_data", {"date": "2024-01-17", "return_timeseries": False}),
    ]
    assert session.closed


def test_fetch_recovery_treats_upstream_no_data_reply_as_empty() -> None:
    session = FakeSession({"get_hrv_data": "No HRV data found for 2024-01-15"})

    signals = asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_recovery(sync_window()))

    assert signals == ()
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


def test_typed_mcp_exception_becomes_redacted_data_error_and_closes() -> None:
    session = FakeSession({}, error=McpSessionError("RAW-HEALTH-SECRET"))
    adapter = GarminMcpAdapter(FakeSessionFactory(session))

    with pytest.raises(GarminDataError) as error:
        asyncio.run(adapter.fetch_sleep(sync_window()))

    assert "RAW-HEALTH-SECRET" not in str(error.value)
    assert session.closed


def test_unexpected_mcp_exception_propagates_and_closes() -> None:
    session = FakeSession({}, error=ValueError("programming bug"))

    with pytest.raises(ValueError, match="programming bug"):
        asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_sleep(sync_window()))

    assert session.closed


def test_session_close_error_becomes_redacted_data_error() -> None:
    session = FakeSession(
        {"get_sleep_summary": "No sleep summary found for 2024-01-15"},
        close_error=McpSessionError("RAW-SESSION-ERROR"),
    )

    with pytest.raises(GarminDataError) as error:
        asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_sleep(sync_window()))

    assert str(error.value) == "Garmin MCP session close failed"
    assert "RAW-SESSION-ERROR" not in str(error.value)


def test_session_close_error_does_not_replace_primary_error() -> None:
    session = FakeSession(
        {"get_sleep_summary": "No sleep summary found for 2024-01-15"},
        error=McpSessionError("RAW-FETCH-ERROR"),
        close_error=McpSessionError("RAW-SESSION-ERROR"),
    )

    with pytest.raises(GarminDataError) as error:
        asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_sleep(sync_window()))

    assert str(error.value) == "Garmin MCP request failed"


def test_session_close_error_does_not_replace_cancellation() -> None:
    cancellation = asyncio.CancelledError()
    session = FakeSession(
        {"get_sleep_summary": "No sleep summary found for 2024-01-15"},
        error=cancellation,
        close_error=McpSessionError("RAW-SESSION-ERROR"),
    )

    with pytest.raises(asyncio.CancelledError) as error:
        asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_sleep(sync_window()))

    assert error.value is cancellation
    assert session.closed
