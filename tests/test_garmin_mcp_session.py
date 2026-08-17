import asyncio
import json
import traceback
from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from mcp.types import CallToolResult, TextContent

from strava_dashboard.adapters.garmin_mcp import session as session_module
from strava_dashboard.adapters.garmin_mcp.session import McpSessionError, StdioMcpSessionFactory


class FakeSdkSession:
    response: object = SimpleNamespace(is_error=False, content=[], structured_content={"ok": True})
    initialize_error: BaseException | None = None
    close_error: Exception | None = None
    captured: dict[str, Any]

    def __init__(self, *streams: object) -> None:
        self.captured["streams"] = streams

    async def __aenter__(self) -> FakeSdkSession:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        self.captured["sdk_closed"] = True
        if self.close_error is not None:
            raise self.close_error

    async def initialize(self) -> None:
        self.captured["initialized"] = True
        if self.initialize_error is not None:
            raise self.initialize_error

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        return self.response


def install_stdio_fakes(monkeypatch: pytest.MonkeyPatch, captured: dict[str, Any]) -> None:
    @asynccontextmanager
    async def fake_stdio(parameters: object, errlog: object):
        captured["parameters"] = parameters
        captured["errlog"] = errlog
        try:
            yield "read", "write"
        finally:
            captured["transport_closed"] = True

    FakeSdkSession.captured = captured
    FakeSdkSession.response = SimpleNamespace(is_error=False, content=[], structured_content={"ok": True})
    FakeSdkSession.initialize_error = None
    FakeSdkSession.close_error = None
    monkeypatch.setattr(session_module, "stdio_client", fake_stdio)
    monkeypatch.setattr(session_module, "ClientSession", FakeSdkSession)


def test_stdio_factory_forces_transport_and_closes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    install_stdio_fakes(monkeypatch, captured)
    monkeypatch.setenv("TASK3_PARENT_SENTINEL", "inherited")
    monkeypatch.setenv("GARMIN_MCP_TRANSPORT", "streamable-http")

    async def exercise() -> Mapping[str, object]:
        session = await StdioMcpSessionFactory("garmin-mcp", tmp_path / "tokens", 30).open()
        result = await session.call_tool("fixture_tool", {})
        await session.close()
        return cast(Mapping[str, object], result)

    assert asyncio.run(exercise()) == {"ok": True}
    parameters = captured["parameters"]
    assert parameters.command == "garmin-mcp"
    assert parameters.env["TASK3_PARENT_SENTINEL"] == "inherited"
    assert parameters.env["GARMINTOKENS"] == str(tmp_path / "tokens")
    assert parameters.env["GARMIN_MCP_TRANSPORT"] == "stdio"
    assert captured["initialized"]
    assert captured["sdk_closed"]
    assert captured["transport_closed"]


def test_stdio_session_parses_actual_json_text_envelope(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    install_stdio_fakes(monkeypatch, captured)
    FakeSdkSession.response = CallToolResult(
        content=[TextContent(type="text", text=json.dumps({"activities": [], "has_more": False}))]
    )

    async def exercise() -> Mapping[str, object]:
        session = await StdioMcpSessionFactory("garmin-mcp", tmp_path / "tokens", 30).open()
        try:
            return cast(Mapping[str, object], await session.call_tool("fixture_tool", {}))
        finally:
            await session.close()

    assert asyncio.run(exercise()) == {"activities": [], "has_more": False}


def test_stdio_session_redacts_json_parse_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    install_stdio_fakes(monkeypatch, captured)
    FakeSdkSession.response = CallToolResult(content=[TextContent(type="text", text="RAW-HEALTH-SECRET{")])

    async def exercise() -> None:
        session = await StdioMcpSessionFactory("garmin-mcp", tmp_path / "tokens", 30).open()
        try:
            await session.call_tool("fixture_tool", {})
        finally:
            await session.close()

    with pytest.raises(McpSessionError) as error:
        asyncio.run(exercise())

    assert "RAW-HEALTH-SECRET" not in str(error.value)
    assert error.value.__cause__ is None


def test_close_terminates_transport_when_graceful_close_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    install_stdio_fakes(monkeypatch, captured)
    FakeSdkSession.close_error = RuntimeError("RAW-HEALTH-SECRET")

    async def exercise() -> None:
        session = await StdioMcpSessionFactory("garmin-mcp", tmp_path / "tokens", 30).open()
        await session.close()

    with pytest.raises(McpSessionError) as error:
        asyncio.run(exercise())

    assert captured["transport_closed"]
    assert "RAW-HEALTH-SECRET" not in str(error.value)


def test_startup_error_wins_when_cleanup_also_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    install_stdio_fakes(monkeypatch, captured)
    initialize_error = RuntimeError("RAW-INITIALIZE-ERROR")
    FakeSdkSession.initialize_error = initialize_error
    FakeSdkSession.close_error = RuntimeError("RAW-CLEANUP-ERROR")

    with pytest.raises(McpSessionError) as error:
        asyncio.run(StdioMcpSessionFactory("garmin-mcp", tmp_path / "tokens", 30).open())

    assert str(error.value) == "MCP session startup failed"
    assert error.value.__cause__ is initialize_error
    assert "RAW-CLEANUP-ERROR" not in "".join(traceback.format_exception(error.value))
    assert captured["transport_closed"]


def test_startup_cancellation_closes_transport_and_preserves_cancellation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}
    install_stdio_fakes(monkeypatch, captured)
    FakeSdkSession.initialize_error = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(StdioMcpSessionFactory("garmin-mcp", tmp_path / "tokens", 30).open())

    assert captured["sdk_closed"]
    assert captured["transport_closed"]


def test_stdio_session_times_out_without_exposing_sdk_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    install_stdio_fakes(monkeypatch, captured)

    async def slow_call(name: str, arguments: dict[str, object]) -> object:
        await asyncio.sleep(1)
        raise RuntimeError("RAW-HEALTH-SECRET")

    monkeypatch.setattr(FakeSdkSession, "call_tool", slow_call)

    async def exercise() -> None:
        session = await StdioMcpSessionFactory("garmin-mcp", tmp_path / "tokens", 0).open()
        try:
            await session.call_tool("fixture_tool", {})
        finally:
            await session.close()

    with pytest.raises(McpSessionError) as error:
        asyncio.run(exercise())

    assert "RAW-HEALTH-SECRET" not in str(error.value)
