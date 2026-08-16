import asyncio
import os
import sys
from collections.abc import Mapping
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Protocol, cast

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class McpSessionError(RuntimeError):
    """Raised when MCP transport or tool execution fails."""


class McpSession(Protocol):
    async def call_tool(self, name: str, arguments: Mapping[str, object]) -> Mapping[str, object]: ...

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
                env={**os.environ, "GARMINTOKENS": str(self._token_dir)},
            )
            read_stream, write_stream = await stack.enter_async_context(stdio_client(parameters, errlog=sys.stderr))
            sdk_session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await sdk_session.initialize()
            return _SdkMcpSession(stack, sdk_session, self._timeout_seconds)
        except Exception as error:
            await stack.aclose()
            raise McpSessionError("MCP session startup failed") from error


class _SdkMcpSession:
    def __init__(self, stack: AsyncExitStack, sdk_session: ClientSession, timeout_seconds: int) -> None:
        self._stack = stack
        self._sdk_session = sdk_session
        self._timeout_seconds = timeout_seconds
        self._closed = False

    async def call_tool(self, name: str, arguments: Mapping[str, object]) -> Mapping[str, object]:
        try:
            response = await asyncio.wait_for(
                self._sdk_session.call_tool(name, arguments=dict(arguments)),
                timeout=self._timeout_seconds,
            )
            if getattr(response, "is_error", False):
                raise McpSessionError("MCP tool returned an error")
            structured = getattr(response, "structured_content", None)
            if not isinstance(structured, Mapping):
                raise McpSessionError("MCP tool returned malformed content")
            return cast(Mapping[str, object], structured)
        except McpSessionError:
            raise
        except Exception as error:
            raise McpSessionError("MCP tool call failed") from error

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                await self._stack.aclose()
            except Exception as error:
                raise McpSessionError("MCP session close failed") from error
