from collections.abc import Callable, Mapping, Sequence
from datetime import date, tzinfo
from typing import Protocol, TypeVar

from strava_dashboard.domain.models import Activity, RecoverySignal, SleepSession, SyncWindow
from strava_dashboard.ports.garmin import GarminDataSource

from .mapping import (
    ACTIVITIES_TOOL,
    HRV_TOOL,
    PAGE_SIZE,
    SLEEP_TOOL,
    GarminDataError,
    date_argument,
    map_activities,
    map_recovery,
    map_sleep,
)
from .session import McpSession, McpSessionError


class McpSessionFactory(Protocol):
    async def open(self) -> McpSession: ...


Record = TypeVar("Record")


class GarminMcpAdapter(GarminDataSource):
    def __init__(self, session_factory: McpSessionFactory) -> None:
        self._session_factory = session_factory

    async def fetch_activities(self, window: SyncWindow) -> Sequence[Activity]:
        return await self._fetch(window, ACTIVITIES_TOOL, self._activity_arguments, map_activities)

    async def fetch_sleep(self, window: SyncWindow) -> Sequence[SleepSession]:
        return await self._fetch(window, SLEEP_TOOL, self._sleep_arguments, lambda payload, _: map_sleep(payload))

    async def fetch_recovery(self, window: SyncWindow) -> Sequence[RecoverySignal]:
        return await self._fetch(window, HRV_TOOL, self._recovery_arguments, map_recovery)

    async def _fetch(
        self,
        window: SyncWindow,
        tool_name: str,
        arguments_builder: Callable[[date], dict[str, object]],
        mapper: Callable[[Mapping[str, object], tzinfo], tuple[Record, ...]],
    ) -> tuple[Record, ...]:
        session = await self._session_factory.open()
        try:
            payload = await session.call_tool(tool_name, arguments_builder(_window_date(window)))
            return mapper(payload, _window_timezone(window))
        except (GarminDataError, McpSessionError) as error:
            if isinstance(error, GarminDataError):
                raise
            raise GarminDataError("Garmin MCP request failed") from error
        except Exception as error:
            raise GarminDataError("Garmin MCP response mapping failed") from error
        finally:
            await session.close()

    @staticmethod
    def _activity_arguments(day: date) -> dict[str, object]:
        value = date_argument(day)
        return {"start_date": value, "end_date": value, "page": 0, "page_size": PAGE_SIZE}

    @staticmethod
    def _sleep_arguments(day: date) -> dict[str, object]:
        return {"date": date_argument(day)}

    @staticmethod
    def _recovery_arguments(day: date) -> dict[str, object]:
        return {"date": date_argument(day), "return_timeseries": False}


def _window_date(window: SyncWindow) -> date:
    return (window.start or window.end).date()


def _window_timezone(window: SyncWindow) -> tzinfo:
    timezone = (window.start or window.end).tzinfo
    assert timezone is not None
    return timezone
