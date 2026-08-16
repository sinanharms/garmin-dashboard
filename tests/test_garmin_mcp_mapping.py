from strava_dashboard.adapters.garmin_mcp import mapping


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
