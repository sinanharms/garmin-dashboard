import asyncio
from copy import deepcopy
from typing import cast

import pytest
from test_garmin_mcp_adapter import FakeSession, FakeSessionFactory, load_fixture, sync_window

from garmin_dashboard.adapters.garmin_mcp.adapter import GarminMcpAdapter
from garmin_dashboard.adapters.garmin_mcp.mapping import GarminDataError
from garmin_dashboard.adapters.garmin_mcp.session import McpSessionError


def test_missing_required_activity_field_raises_redacted_data_error_and_closes() -> None:
    payload = deepcopy(load_fixture("garmin_activity.json"))
    activity = cast(dict[str, object], cast(list[object], payload["activities"])[0])
    del activity["id"]
    activity["private_marker"] = "RAW-HEALTH-SECRET"
    session = FakeSession({"get_activities_by_date": payload})

    with pytest.raises(GarminDataError) as error:
        asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_activities(sync_window()))

    assert "RAW-HEALTH-SECRET" not in str(error.value)
    assert session.closed


def test_typed_mcp_exception_becomes_redacted_data_error_and_closes() -> None:
    session = FakeSession({}, error=McpSessionError("RAW-HEALTH-SECRET"))

    with pytest.raises(GarminDataError) as error:
        asyncio.run(GarminMcpAdapter(FakeSessionFactory(session)).fetch_sleep(sync_window()))

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
