from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from strava_dashboard.api.dependencies import DashboardQuery, get_dashboard_service
from strava_dashboard.application.dashboard import DashboardView
from strava_dashboard.domain.models import TrendBucket, TrendSnapshot

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardView)
def current_dashboard(
    service: Annotated[DashboardQuery, Depends(get_dashboard_service)],
    today: Annotated[date | None, Query()] = None,
) -> DashboardView:
    requested_day = today or date.today()
    return service.current(requested_day)


@router.get("/dashboard/trends", response_model=TrendSnapshot)
def dashboard_trends(
    service: Annotated[DashboardQuery, Depends(get_dashboard_service)],
    start: date,
    end: date,
    bucket: Annotated[TrendBucket, Query()] = TrendBucket.WEEK,
) -> TrendSnapshot:
    if end <= start:
        raise HTTPException(status_code=422, detail="start must be before end")
    return service.trends(start, end, bucket)
