import asyncio
from datetime import UTC, datetime, timedelta

from strava_dashboard.adapters.garmin_mcp.adapter import GarminMcpAdapter
from strava_dashboard.adapters.garmin_mcp.session import StdioMcpSessionFactory
from strava_dashboard.adapters.sqlite.activity_store import SQLiteActivityStore
from strava_dashboard.adapters.sqlite.connection import SQLiteConnection, open_connection
from strava_dashboard.adapters.sqlite.recovery_store import SQLiteRecoveryStore
from strava_dashboard.adapters.sqlite.sleep_store import SQLiteSleepStore
from strava_dashboard.adapters.sqlite.sync_store import SQLiteSyncRunStore
from strava_dashboard.application.sync import SyncService
from strava_dashboard.config import Settings
from strava_dashboard.domain.models import SyncRun, SyncWindow


def build_sync_service(settings: Settings, connection: SQLiteConnection | None = None) -> SyncService:
    owns_connection = connection is None
    database = connection if connection is not None else open_connection(settings.database_path)
    try:
        session_factory = StdioMcpSessionFactory(
            command=settings.garmin_mcp_command,
            token_dir=settings.garmin_token_dir,
            timeout_seconds=settings.mcp_timeout_seconds,
        )
        return SyncService(
            source=GarminMcpAdapter(session_factory),
            activities=SQLiteActivityStore(database),
            sleep=SQLiteSleepStore(database),
            recovery=SQLiteRecoveryStore(database),
            runs=SQLiteSyncRunStore(database),
            clock=lambda: datetime.now(UTC),
        )
    except Exception:
        if owns_connection:
            database.close()
        raise


def nightly_window(now: datetime) -> SyncWindow:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("worker clock must be timezone-aware")
    return SyncWindow(start=now - timedelta(days=1), end=now)


async def run_once(settings: Settings) -> SyncRun:
    connection = open_connection(settings.database_path)
    try:
        service = build_sync_service(settings, connection=connection)
        return await service.run(nightly_window(datetime.now(UTC)))
    finally:
        connection.close()


def main() -> int:
    run = asyncio.run(run_once(Settings()))  # ty: ignore[missing-argument]
    return 0 if all(stage.status == "succeeded" for stage in run.stages) else 1


if __name__ == "__main__":
    raise SystemExit(main())
