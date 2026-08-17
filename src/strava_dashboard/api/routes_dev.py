from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from strava_dashboard.api.dependencies import OperationsQuery, get_inspection_service, get_operations_service
from strava_dashboard.application.dashboard import (
    CoachHealth,
    GarminHealth,
    HealthReport,
    InspectionService,
    SyncRunDetail,
    SyncRunList,
)
from strava_dashboard.application.operations import BackupOperation, OperationsHealth

router = APIRouter(prefix="/api/dev", tags=["inspection"])


@router.get("/health", response_model=HealthReport)
def application_health(service: Annotated[InspectionService, Depends(get_inspection_service)]) -> HealthReport:
    return service.health()


@router.get("/garmin/health", response_model=GarminHealth)
def garmin_health(service: Annotated[InspectionService, Depends(get_inspection_service)]) -> GarminHealth:
    return service.garmin_health()


@router.get("/sync/runs", response_model=SyncRunList)
def sync_runs(
    service: Annotated[InspectionService, Depends(get_inspection_service)],
    limit: int = Query(default=20, ge=1, le=100),
) -> SyncRunList:
    return service.recent_sync_runs(limit)


@router.get("/sync/runs/{run_id}", response_model=SyncRunDetail)
def sync_run(run_id: str, service: Annotated[InspectionService, Depends(get_inspection_service)]) -> SyncRunDetail:
    result = service.sync_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="sync run not found")
    return result


@router.get("/storage/health", response_model=OperationsHealth)
def storage_health(service: Annotated[OperationsQuery, Depends(get_operations_service)]) -> OperationsHealth:
    return service.health()


@router.post("/storage/backup", response_model=BackupOperation)
def create_backup(service: Annotated[OperationsQuery, Depends(get_operations_service)]) -> BackupOperation:
    return service.backup()


@router.get("/coach/health", response_model=CoachHealth)
def coach_health(service: Annotated[InspectionService, Depends(get_inspection_service)]) -> CoachHealth:
    return service.coach_health()
