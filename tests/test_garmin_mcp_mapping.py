import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from strava_dashboard.adapters.garmin_mcp import mapping
from strava_dashboard.adapters.garmin_mcp.mapping import GarminDataError

SCHEMA_SNAPSHOT = Path(__file__).parent / "fixtures" / "garmin_mcp_list_tools_schema.json"


def test_tool_contracts_match_verified_upstream_schema() -> None:
    snapshot = cast(dict[str, dict[str, Any]], json.loads(SCHEMA_SNAPSHOT.read_text()))
    contracts = (mapping.ACTIVITIES_CONTRACT, mapping.SLEEP_CONTRACT, mapping.HRV_CONTRACT)

    assert mapping.GARMIN_MCP_SCHEMA_COMMIT == "3610be6feed93088d85b0f35aba9d7d07c2505a7"
    assert set(snapshot) == {contract.name for contract in contracts}
    for contract in contracts:
        schema = snapshot[contract.name]
        properties = cast(dict[str, dict[str, object]], schema["properties"])
        required = cast(list[str], schema["required"])
        discovered = {
            name: {
                "name": name,
                "json_type": definition["type"],
                "required": name in required,
                "default": definition.get("default"),
            }
            for name, definition in properties.items()
        }
        assert discovered == {argument.name: argument.model_dump() for argument in contract.arguments}


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


def test_map_recovery_skips_metrics_without_measurement_timestamp() -> None:
    payload = {
        "date": "2024-01-15",
        "last_night_avg_hrv_ms": 48,
        "weekly_avg_hrv_ms": 45,
    }

    assert mapping.map_recovery(payload, UTC) == ()


def test_map_activities_normalizes_fractional_duration_seconds() -> None:
    payload = {
        "activities": [
            {
                "id": 1,
                "type": "running",
                "start_time": "2024-01-15T07:30:00",
                "duration_seconds": 123.75,
            }
        ]
    }

    activities = mapping.map_activities(payload, UTC)

    assert activities[0].duration_seconds == 123
