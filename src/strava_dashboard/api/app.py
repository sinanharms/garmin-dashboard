from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from strava_dashboard.adapters.sqlite.activity_store import SQLiteActivityStore
from strava_dashboard.adapters.sqlite.connection import open_connection
from strava_dashboard.adapters.sqlite.planning_store import SQLiteGoalStore, SQLitePlanStore
from strava_dashboard.adapters.sqlite.recovery_store import SQLiteRecoveryStore
from strava_dashboard.adapters.sqlite.sleep_store import SQLiteSleepStore
from strava_dashboard.adapters.sqlite.sync_store import SQLiteSyncRunStore
from strava_dashboard.api.dependencies import AppServices
from strava_dashboard.api.routes_dashboard import router as dashboard_router
from strava_dashboard.api.routes_dev import router as dev_router
from strava_dashboard.application.dashboard import DashboardService, SQLiteInspectionService
from strava_dashboard.config import Settings
from strava_dashboard.ports.storage import StorageError

BASE_DIR = Path(__file__).parent


def build_production_services(settings: Settings) -> AppServices:
    connection = open_connection(settings.database_path)
    try:
        runs = SQLiteSyncRunStore(connection)
        dashboard = DashboardService(
            activities=SQLiteActivityStore(connection),
            sleep=SQLiteSleepStore(connection),
            recovery=SQLiteRecoveryStore(connection),
            goals=SQLiteGoalStore(connection),
            plans=SQLitePlanStore(connection),
            clock=lambda: datetime.now(UTC),
        )
        inspection = SQLiteInspectionService(runs, settings.database_path, settings.backup_dir)
        return AppServices(dashboard, inspection, close=connection.close)
    except Exception:
        connection.close()
        raise


def create_app(dashboard_service=None, inspection_service=None, settings: Settings | None = None) -> FastAPI:
    if (dashboard_service is None) != (inspection_service is None):
        raise ValueError("dashboard and inspection services must be injected together")
    if dashboard_service is None:
        injected = None
    elif inspection_service is None:
        raise ValueError("dashboard and inspection services must be injected together")
    else:
        injected = AppServices(dashboard_service, inspection_service)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        services = injected or build_production_services(settings or Settings())  # ty: ignore[missing-argument]
        application.state.services = services
        try:
            yield
        finally:
            if injected is None:
                services.close()

    application = FastAPI(title="Garmin Training Dashboard", lifespan=lifespan)
    if injected is not None:
        application.state.services = injected
    application.include_router(dashboard_router)
    application.include_router(dev_router)
    application.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

    @application.get("/", include_in_schema=False)
    def dashboard_shell() -> FileResponse:
        return FileResponse(BASE_DIR / "templates" / "index.html")

    @application.exception_handler(StorageError)
    async def storage_error(_request: Request, _error: StorageError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "storage unavailable"})

    @application.exception_handler(Exception)
    async def unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    return application


app = create_app()
