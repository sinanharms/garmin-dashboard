from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from strava_dashboard.api.app import create_app
from strava_dashboard.application.dashboard import (
    CoachHealth,
    DashboardView,
    GarminHealth,
    HealthReport,
    InspectionService,
    StorageHealth,
    SyncRunDetail,
    SyncRunList,
)
from strava_dashboard.domain.models import (
    Activity,
    HealthSummary,
    SyncRun,
    SyncStageResult,
    TrainingSummary,
    TrendBucket,
    TrendSnapshot,
)
from strava_dashboard.domain.plan_models import Goal

NOW = datetime(2026, 8, 17, 8, tzinfo=UTC)


def dashboard_view(*, health_available: bool = False) -> DashboardView:
    training = TrainingSummary(
        start=date(2026, 8, 10),
        end=date(2026, 8, 17),
        activity_count=1,
        duration_seconds=3600,
        distance_meters=10_000.0,
        elevation_meters=100.0,
        sport_counts=(("running", 1),),
        training_load=60.0,
    )
    health = HealthSummary(
        start=training.start,
        end=training.end,
        available=health_available,
        average_sleep_seconds=28_800.0 if health_available else None,
        average_sleep_score=82.0 if health_available else None,
        recovery_metrics=(("body_battery", 75.0, "percent"),) if health_available else (),
    )
    activity = Activity(
        external_id="activity-1",
        activity_type="running",
        started_at=NOW,
        local_date=NOW.date(),
        duration_seconds=3600,
        distance_meters=10_000.0,
        elevation_meters=100.0,
        average_heart_rate=145.0,
        max_heart_rate=170.0,
        calories=500.0,
    )
    goal = Goal(goal_id="goal-1", description="Run 10 km", target_date=date(2026, 10, 1))
    return DashboardView(
        generated_at=NOW,
        training=training,
        health=health,
        health_status="available" if health_available else "missing",
        goal=goal,
        plan=None,
        recent_activities=(activity,),
    )


class FakeDashboardService:
    def current(self, today: date) -> DashboardView:
        return dashboard_view()

    def trends(self, start: date, end: date, bucket: TrendBucket) -> TrendSnapshot:
        return TrendSnapshot(start=start, end=end, bucket=bucket, training=(), health=())


class FailingDashboardService(FakeDashboardService):
    def current(self, today: date) -> DashboardView:
        raise RuntimeError("secret database path and token")


class FakeInspectionService(InspectionService):
    def health(self) -> HealthReport:
        return HealthReport(status="degraded", detail="health data missing")

    def garmin_health(self) -> GarminHealth:
        return GarminHealth(status="unavailable", authenticated=False, last_mcp_check=None, last_sync=None)

    def recent_sync_runs(self, limit: int) -> SyncRunList:
        return SyncRunList(runs=(sync_detail().run,))

    def sync_run(self, run_id: str) -> SyncRunDetail | None:
        return sync_detail() if run_id == "run-1" else None

    def storage_health(self) -> StorageHealth:
        return StorageHealth(status="ok", database_size_bytes=12, backup_size_bytes=0, disk_available_bytes=100)

    def coach_health(self) -> CoachHealth:
        return CoachHealth(status="unavailable", last_call_status=None, schema_validation_failures=0)


def sync_detail() -> SyncRunDetail:
    run = SyncRun(
        run_id="run-1",
        started_at=NOW - timedelta(minutes=2),
        ended_at=NOW,
        stages=(SyncStageResult(data_family="activities", status="succeeded", record_count=1, error_code=None),),
    )
    return SyncRunDetail(run=run, failure_detail=None)


def client() -> TestClient:
    return TestClient(create_app(FakeDashboardService(), FakeInspectionService()))


def test_dashboard_contains_training_health_goal_and_recent_activity() -> None:
    response = client().get("/api/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["training"]["training_load"] == 60.0
    assert body["health"]["available"] is False
    assert body["health_status"] == "missing"
    assert body["goal"]["description"] == "Run 10 km"
    assert body["recent_activities"][0]["external_id"] == "activity-1"
    assert "GARMIN_PASSWORD" not in response.text


def test_dashboard_trends_uses_typed_query_parameters() -> None:
    response = client().get("/api/dashboard/trends?start=2026-08-01&end=2026-08-17&bucket=month")

    assert response.status_code == 200
    assert response.json()["bucket"] == "month"


def test_dashboard_trends_rejects_equal_dates_at_route_boundary() -> None:
    response = client().get("/api/dashboard/trends?start=2026-08-17&end=2026-08-17")

    assert response.status_code == 422
    assert response.json() == {"detail": "start must be before end"}


def test_dashboard_trends_rejects_inverted_dates_at_route_boundary() -> None:
    response = client().get("/api/dashboard/trends?start=2026-08-18&end=2026-08-17")

    assert response.status_code == 422
    assert response.json() == {"detail": "start must be before end"}


def test_six_read_only_inspection_endpoints_are_available_and_redacted() -> None:
    api = client()
    paths = (
        "/api/dev/health",
        "/api/dev/garmin/health",
        "/api/dev/sync/runs",
        "/api/dev/sync/runs/run-1",
        "/api/dev/storage/health",
        "/api/dev/coach/health",
    )

    responses = tuple(api.get(path) for path in paths)

    assert all(response.status_code == 200 for response in responses)
    assert all(secret not in response.text for response in responses for secret in ("password", "token", "prompt"))
    assert api.post("/api/dashboard").status_code == 405
    assert api.post("/api/dev/health").status_code == 405


def test_arbitrary_sql_and_mcp_requests_are_not_exposed() -> None:
    api = client()

    assert api.post("/api/dev/sql", json={"query": "DROP TABLE activities"}).status_code in (404, 405)
    assert api.post("/api/dev/mcp", json={"tool": "get_activities_by_date"}).status_code in (404, 405)


def test_missing_sync_run_is_a_safe_not_found() -> None:
    response = client().get("/api/dev/sync/runs/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "sync run not found"}


def test_unexpected_route_errors_are_redacted() -> None:
    api = TestClient(create_app(FailingDashboardService(), FakeInspectionService()), raise_server_exceptions=False)

    response = api.get("/api/dashboard")

    assert response.status_code == 500
    assert response.json() == {"detail": "internal server error"}
    assert "secret database path" not in response.text


def test_dashboard_shell_isolated_from_api_and_static_assets() -> None:
    api = client()

    page = api.get("/")
    stylesheet = api.get("/static/dashboard.css")
    script = api.get("/static/dashboard.js")

    assert page.status_code == 200
    assert "Garmin Training Dashboard" in page.text
    assert "/api/dashboard" in page.text
    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert 'id="weekly-plan-content"' in page.text
    assert 'id="sleep-detail"' in page.text
    assert 'id="recovery-detail"' in page.text
    for field in ("health_status", "average_sleep_seconds", "average_sleep_score", "recovery_metrics"):
        assert field in script.text
    assert "proposal.week_start" in script.text
    assert "proposal?.workouts" in script.text
    assert "Weekly plan unavailable" in script.text
    assert "Sleep: unavailable" in script.text
    assert "Recovery: unavailable" in script.text
