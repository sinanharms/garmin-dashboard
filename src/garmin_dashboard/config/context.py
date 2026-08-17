from datetime import UTC, datetime

from garmin_dashboard.adapters.sqlite import open_connection
from garmin_dashboard.adapters.sqlite.activity_store import SQLiteActivityStore
from garmin_dashboard.adapters.sqlite.backup import SQLiteBackupStore
from garmin_dashboard.adapters.sqlite.connection import SQLiteConnection
from garmin_dashboard.adapters.sqlite.planning_store import SQLiteGoalStore, SQLitePlanStore
from garmin_dashboard.adapters.sqlite.recovery_store import SQLiteRecoveryStore
from garmin_dashboard.adapters.sqlite.sleep_store import SQLiteSleepStore
from garmin_dashboard.adapters.sqlite.sync_store import SQLiteSyncRunStore
from garmin_dashboard.application.dashboard import DashboardService, InspectionService, SQLiteInspectionService
from garmin_dashboard.application.operations import OperationsService
from garmin_dashboard.config.settings import Settings


class ApplicationContext:
    connection: SQLiteConnection
    runs: SQLiteSyncRunStore
    backups_store: SQLiteBackupStore
    operations: OperationsService
    dashboard: DashboardService
    inspection: InspectionService

    def __init__(
        self,
        connection: SQLiteConnection,
        runs: SQLiteSyncRunStore,
        backups_store: SQLiteBackupStore,
        operations: OperationsService,
        dashboard: DashboardService,
        inspection: InspectionService,
        close=None,
    ) -> None:
        self.connection = connection
        self.runs = runs
        self.backups_store = backups_store
        self.operations = operations
        self.dashboard = dashboard
        self.inspection = inspection
        self._close = close

    def close(self):
        if self._close is not None:
            self._close()


def create_context(settings: Settings) -> ApplicationContext:
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
        return ApplicationContext(
            connection=connection,
            runs=runs,
            backups_store=backup_store,
            operations=operations,
            dashboard=dashboard,
            inspection=inspection,
            close=connection.close,
        )
    except Exception:
        connection.close()
        raise
