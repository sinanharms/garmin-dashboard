from typing import Protocol

from fastapi import Request

from strava_dashboard.application.dashboard import DashboardView, InspectionService
from strava_dashboard.domain.models import TrendBucket, TrendSnapshot


class DashboardQuery(Protocol):
    def current(self, today) -> DashboardView: ...

    def trends(self, start, end, bucket: TrendBucket) -> TrendSnapshot: ...


class AppServices:
    def __init__(self, dashboard: DashboardQuery, inspection: InspectionService, close=None) -> None:
        self.dashboard = dashboard
        self.inspection = inspection
        self._close = close

    def close(self) -> None:
        if self._close is not None:
            self._close()


def get_dashboard_service(request: Request) -> DashboardQuery:
    return request.app.state.services.dashboard


def get_inspection_service(request: Request) -> InspectionService:
    return request.app.state.services.inspection
