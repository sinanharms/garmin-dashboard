from typing import Protocol

from fastapi import Request

from strava_dashboard.application.dashboard import DashboardView, InspectionService
from strava_dashboard.application.operations import BackupOperation, OperationsHealth
from strava_dashboard.domain.models import TrendBucket, TrendSnapshot


class DashboardQuery(Protocol):
    def current(self, today) -> DashboardView: ...

    def trends(self, start, end, bucket: TrendBucket) -> TrendSnapshot: ...


class OperationsQuery(Protocol):
    def health(self) -> OperationsHealth: ...

    def backup(self) -> BackupOperation: ...


class AppServices:
    def __init__(
        self,
        dashboard: DashboardQuery,
        inspection: InspectionService,
        operations: OperationsQuery | None = None,
        close=None,
    ) -> None:
        self.dashboard = dashboard
        self.inspection = inspection
        self.operations = operations
        self._close = close

    def close(self) -> None:
        if self._close is not None:
            self._close()


def get_dashboard_service(request: Request) -> DashboardQuery:
    return request.app.state.services.dashboard


def get_inspection_service(request: Request) -> InspectionService:
    return request.app.state.services.inspection


def get_operations_service(request: Request) -> OperationsQuery:
    operations = request.app.state.services.operations
    if operations is None:
        raise RuntimeError("operations service is not configured")
    return operations
