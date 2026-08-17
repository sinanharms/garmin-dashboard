from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from garmin_dashboard.adapters.sqlite.activity_store import SQLiteActivityStore
from garmin_dashboard.adapters.sqlite.backup import SQLiteBackupStore
from garmin_dashboard.adapters.sqlite.connection import open_connection
from garmin_dashboard.adapters.sqlite.planning_store import SQLiteGoalStore, SQLitePlanStore
from garmin_dashboard.adapters.sqlite.recovery_store import SQLiteRecoveryStore
from garmin_dashboard.adapters.sqlite.sleep_store import SQLiteSleepStore
from garmin_dashboard.adapters.sqlite.sync_store import SQLiteSyncRunStore
from garmin_dashboard.api.dependencies import AppServices
from garmin_dashboard.api.routes_dashboard import router as dashboard_router
from garmin_dashboard.api.routes_dev import router as dev_router
from garmin_dashboard.application.dashboard import DashboardService, SQLiteInspectionService
from garmin_dashboard.application.operations import OperationsService
from garmin_dashboard.config import Settings
from garmin_dashboard.ports.storage import StorageError

BASE_DIR = Path(__file__).parent


def build_production_services(settings: Settings) -> AppServices:
    connection = open_connection(settings.database_path)
    try:
        runs = SQLiteSyncRunStore(connection)
        backup_store = SQLiteBackupStore(
            connection,
            settings.backup_dir,
            settings.backup_retention_count,
            settings.backup_retention_days,
            lambda: datetime.now(UTC),
        )
        operations = OperationsService(settings, connection, backup_store, lambda: datetime.now(UTC))
        dashboard = DashboardService(
            activities=SQLiteActivityStore(connection),
            sleep=SQLiteSleepStore(connection),
            recovery=SQLiteRecoveryStore(connection),
            goals=SQLiteGoalStore(connection),
            plans=SQLitePlanStore(connection),
            clock=lambda: datetime.now(UTC),
        )
        inspection = SQLiteInspectionService(runs, settings.database_path, settings.backup_dir)
        return AppServices(dashboard, inspection, operations, close=connection.close)
    except Exception:
        connection.close()
        raise


def create_app(
    dashboard_service=None,
    inspection_service=None,
    operations_service=None,
    settings: Settings | None = None,
    *,
    frontend_dir: Path | None = None,
) -> FastAPI:
    if (dashboard_service is None) != (inspection_service is None):
        raise ValueError("dashboard and inspection services must be injected together")
    if dashboard_service is None:
        injected = None
    elif inspection_service is None:
        raise ValueError("dashboard and inspection services must be injected together")
    else:
        injected = AppServices(dashboard_service, inspection_service, operations_service)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        services = injected or build_production_services(settings or Settings())
        application.state.services = services
        try:
            yield
        finally:
            if injected is None:
                services.close()

    frontend_directory = frontend_dir or BASE_DIR / "static" / "app"
    application = FastAPI(title="Garmin Training Dashboard", lifespan=lifespan)
    if injected is not None:
        application.state.services = injected
    application.include_router(dashboard_router)
    application.include_router(dev_router)
    application.mount("/static/app", StaticFiles(directory=frontend_directory), name="frontend")

    @application.get("/", include_in_schema=False)
    def dashboard_shell() -> FileResponse:
        return FileResponse(frontend_directory / "index.html")

    @application.exception_handler(StorageError)
    async def storage_error(_request: Request, _error: StorageError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "storage unavailable"})

    @application.exception_handler(Exception)
    async def unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    return application


app = create_app()
