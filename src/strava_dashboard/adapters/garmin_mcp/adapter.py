from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import date, timedelta, tzinfo
from typing import Protocol, TypeVar, cast

from strava_dashboard.domain.models import Activity, RecoverySignal, SleepSession, SyncWindow
from strava_dashboard.ports.garmin import GarminDataSource

from .mapping import (
    ACTIVITIES_TOOL,
    HRV_TOOL,
    SLEEP_TOOL,
    GarminDataError,
    activity_arguments,
    map_activities,
    map_recovery,
    map_sleep,
    next_activity_page,
    recovery_arguments,
    sleep_arguments,
)
from .session import McpSession, McpSessionError


class McpSessionFactory(Protocol):
    async def open(self) -> McpSession: ...


Record = TypeVar("Record")


class GarminMcpAdapter(GarminDataSource):
    def __init__(self, session_factory: McpSessionFactory) -> None:
        self._session_factory = session_factory

    async def fetch_activities(self, window: SyncWindow) -> Sequence[Activity]:
        async def fetch(session: McpSession) -> tuple[Activity, ...]:
            start_date, end_date = _window_dates(window)
            page = 0
            activities: list[Activity] = []
            while True:
                payload = await session.call_tool(ACTIVITIES_TOOL, activity_arguments(start_date, end_date, page))
                if not isinstance(payload, Mapping):
                    raise GarminDataError("Garmin MCP activities response was malformed")
                mapping = cast(Mapping[str, object], payload)
                activities.extend(map_activities(mapping, _window_timezone(window)))
                next_page = next_activity_page(mapping, page)
                if next_page is None:
                    return tuple(activities)
                page = next_page

        return await self._run(fetch)

    async def fetch_sleep(self, window: SyncWindow) -> Sequence[SleepSession]:
        async def fetch(session: McpSession) -> tuple[SleepSession, ...]:
            timezone = _window_timezone(window)
            records: list[SleepSession] = []
            for day in _window_days(window):
                payload = await session.call_tool(SLEEP_TOOL, sleep_arguments(day))
                if isinstance(payload, str) and payload.startswith("No sleep summary found"):
                    continue
                if not isinstance(payload, Mapping):
                    raise GarminDataError("Garmin MCP sleep response was malformed")
                records.extend(map_sleep(cast(Mapping[str, object], payload), day, timezone))
            return tuple(records)

        return await self._run(fetch)

    async def fetch_recovery(self, window: SyncWindow) -> Sequence[RecoverySignal]:
        async def fetch(session: McpSession) -> tuple[RecoverySignal, ...]:
            records: list[RecoverySignal] = []
            for day in _window_days(window):
                payload = await session.call_tool(HRV_TOOL, recovery_arguments(day))
                if isinstance(payload, str) and payload.startswith("No HRV data found"):
                    continue
                if not isinstance(payload, Mapping):
                    raise GarminDataError("Garmin MCP HRV response was malformed")
                records.extend(map_recovery(cast(Mapping[str, object], payload), _window_timezone(window)))
            return tuple(records)

        return await self._run(fetch)

    async def _run(
        self,
        fetch: Callable[[McpSession], Awaitable[tuple[Record, ...]]],
    ) -> tuple[Record, ...]:
        try:
            session = await self._session_factory.open()
        except McpSessionError as error:
            raise GarminDataError("Garmin MCP session startup failed") from error
        primary_error: BaseException | None = None
        try:
            return await fetch(session)
        except (GarminDataError, McpSessionError) as error:
            if isinstance(error, GarminDataError):
                primary_error = error
                raise
            primary_error = GarminDataError("Garmin MCP request failed")
            raise primary_error from error
        except Exception as error:
            primary_error = error
            raise
        except BaseException as error:
            primary_error = error
            raise
        finally:
            try:
                await session.close()
            except McpSessionError as error:
                if primary_error is None:
                    raise GarminDataError("Garmin MCP session close failed") from error


def _window_timezone(window: SyncWindow) -> tzinfo:
    timezone = (window.start or window.end).tzinfo
    assert timezone is not None
    return timezone


def _window_dates(window: SyncWindow) -> tuple[date, date]:
    timezone = _window_timezone(window)
    start = (window.start or window.end).astimezone(timezone).date()
    end = window.end.astimezone(timezone).date()
    return start, end


def _window_days(window: SyncWindow) -> tuple[date, ...]:
    start, end = _window_dates(window)
    return tuple(start + timedelta(days=offset) for offset in range((end - start).days + 1))
