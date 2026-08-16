from datetime import UTC, datetime

import pytest

from strava_dashboard.adapters.garmin_mcp import mapping
from strava_dashboard.adapters.garmin_mcp.mapping import GarminDataError


def test_tool_contracts_match_verified_upstream_schema() -> None:
    assert mapping.GARMIN_MCP_SCHEMA_COMMIT == "3610be6feed93088d85b0f35aba9d7d07c2505a7"
    assert {
        contract.name: tuple(argument.model_dump() for argument in contract.arguments)
        for contract in (mapping.ACTIVITIES_CONTRACT, mapping.SLEEP_CONTRACT, mapping.HRV_CONTRACT)
    } == {
        "get_activities_by_date": (
            {"name": "start_date", "json_type": "string", "required": True, "default": None},
            {"name": "end_date", "json_type": "string", "required": True, "default": None},
            {"name": "activity_type", "json_type": "string", "required": False, "default": ""},
            {"name": "page", "json_type": "integer", "required": False, "default": 0},
            {"name": "page_size", "json_type": "integer", "required": False, "default": 100},
        ),
        "get_sleep_summary": ({"name": "date", "json_type": "string", "required": True, "default": None},),
        "get_hrv_data": (
            {"name": "date", "json_type": "string", "required": True, "default": None},
            {"name": "return_timeseries", "json_type": "boolean", "required": False, "default": False},
        ),
    }


def test_map_recovery_returns_only_present_numeric_metrics() -> None:
    payload = {
        "date": "2024-01-15",
        "sleep_end": "2024-01-15T07:30:00",
        "last_night_avg_hrv_ms": 48,
        "last_night_5min_high_hrv_ms": None,
        "weekly_avg_hrv_ms": None,
    }

    signals = mapping.map_recovery(payload, UTC)

    assert len(signals) == 1
    assert signals[0].metric_name == "last_night_avg_hrv_ms"
    assert signals[0].value == 48.0


def test_map_recovery_rejects_malformed_present_metric() -> None:
    payload = {
        "date": "2024-01-15",
        "sleep_end": datetime(2024, 1, 15, 7, 30).isoformat(),
        "last_night_avg_hrv_ms": "malformed",
    }

    with pytest.raises(GarminDataError, match="last_night_avg_hrv_ms"):
        mapping.map_recovery(payload, UTC)
