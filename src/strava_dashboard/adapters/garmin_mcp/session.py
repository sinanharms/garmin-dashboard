import asyncio
import json
import os
import sys
from collections.abc import Mapping
from contextlib import AsyncExitStack, suppress
from pathlib import Path
from typing import Protocol, cast

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class McpSessionError(RuntimeError):
    """Raised when MCP transport or tool execution fails."""


class McpSession(Protocol):
    async def call_tool(self, name: str, arguments: Mapping[str, object]) -> Mapping[str, object] | str: ...

    async def close(self) -> None: ...


class StdioMcpSessionFactory:
    def __init__(self, command: str, token_dir: Path, timeout_seconds: int) -> None:
        self._command = command
        self._token_dir = token_dir
        self._timeout_seconds = timeout_seconds

    async def open(self) -> McpSession:
        stack = AsyncExitStack()
        try:
            parameters = StdioServerParameters(
                command=self._command,
                args=[],
                env={
                    **os.environ,
                    "GARMINTOKENS": str(self._token_dir),
                    "GARMIN_MCP_TRANSPORT": "stdio",
                },
            )
            read_stream, write_stream = await stack.enter_async_context(stdio_client(parameters, errlog=sys.stderr))
            sdk_session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await sdk_session.initialize()
            return _SdkMcpSession(stack, sdk_session, self._timeout_seconds)
        except Exception as error:
            startup_error = McpSessionError("MCP session startup failed")
            with suppress(Exception):
                await stack.aclose()
            raise startup_error from error


class _SdkMcpSession:
    def __init__(self, stack: AsyncExitStack, sdk_session: ClientSession, timeout_seconds: int) -> None:
        self._stack = stack
        self._sdk_session = sdk_session
        self._timeout_seconds = timeout_seconds
        self._closed = False

    async def call_tool(self, name: str, arguments: Mapping[str, object]) -> Mapping[str, object] | str:
        try:
            response = await asyncio.wait_for(
                self._sdk_session.call_tool(name, arguments=dict(arguments)),
                timeout=self._timeout_seconds,
            )
            if getattr(response, "is_error", False):
                raise McpSessionError("MCP tool returned an error")
            return _result_mapping(response, name)
        except McpSessionError:
            raise
        except Exception as error:
            raise McpSessionError("MCP tool call failed") from error

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                # AsyncExitStack keeps unwinding after ClientSession close errors.
                # stdio_client then runs its bounded process termination fallback.
                await self._stack.aclose()
            except Exception as error:
                raise McpSessionError("MCP session close failed") from error


def _result_mapping(response: object, tool_name: str) -> Mapping[str, object] | str:
    structured = getattr(response, "structured_content", None)
    if isinstance(structured, Mapping):
        return _validated_mapping(structured)

    content = getattr(response, "content", None)
    if not isinstance(content, list) or len(content) != 1:
        raise McpSessionError("MCP tool returned malformed content")
    item = content[0]
    if getattr(item, "type", None) != "text" or not isinstance(getattr(item, "text", None), str):
        raise McpSessionError("MCP tool returned malformed content")
    try:
        decoded = json.loads(item.text)
    except TypeError, json.JSONDecodeError:
        if tool_name == "get_sleep_summary" and item.text.startswith("No sleep summary found"):
            return item.text
        if tool_name == "get_hrv_data" and item.text.startswith("No HRV data found"):
            return item.text
        raise McpSessionError("MCP tool returned malformed JSON content") from None
    return _validated_mapping(decoded)


def _validated_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise McpSessionError("MCP tool returned malformed content")
    return cast(Mapping[str, object], value)
