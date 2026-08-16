from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time, tzinfo
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict

from strava_dashboard.domain.models import Activity, RecoverySignal, SleepSession

GARMIN_MCP_SCHEMA_COMMIT = "3610be6feed93088d85b0f35aba9d7d07c2505a7"
PAGE_SIZE = 200
HRV_METRICS = (
    "last_night_avg_hrv_ms",
    "last_night_5min_high_hrv_ms",
    "weekly_avg_hrv_ms",
    "baseline_balanced_low_ms",
    "baseline_balanced_upper_ms",
    "baseline_low_upper_ms",
)


class ToolArgument(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    json_type: Literal["string", "integer", "boolean"]
    required: bool
    default: str | int | bool | None = None


class ToolContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    arguments: tuple[ToolArgument, ...]


ACTIVITIES_CONTRACT = ToolContract(
    name="get_activities_by_date",
    arguments=(
        ToolArgument(name="start_date", json_type="string", required=True),
        ToolArgument(name="end_date", json_type="string", required=True),
        ToolArgument(name="activity_type", json_type="string", required=False, default=""),
        ToolArgument(name="page", json_type="integer", required=False, default=0),
        ToolArgument(name="page_size", json_type="integer", required=False, default=100),
    ),
)
SLEEP_CONTRACT = ToolContract(
    name="get_sleep_summary",
    arguments=(ToolArgument(name="date", json_type="string", required=True),),
)
HRV_CONTRACT = ToolContract(
    name="get_hrv_data",
    arguments=(
        ToolArgument(name="date", json_type="string", required=True),
        ToolArgument(name="return_timeseries", json_type="boolean", required=False, default=False),
    ),
)

ACTIVITIES_TOOL = ACTIVITIES_CONTRACT.name
SLEEP_TOOL = SLEEP_CONTRACT.name
HRV_TOOL = HRV_CONTRACT.name


class GarminDataError(RuntimeError):
    """Raised when Garmin MCP data cannot become a domain model."""


def date_argument(value: date) -> str:
    return value.isoformat()


def activity_arguments(start_date: date, end_date: date, page: int) -> dict[str, object]:
    return {
        "start_date": date_argument(start_date),
        "end_date": date_argument(end_date),
        "page": page,
        "page_size": PAGE_SIZE,
    }


def sleep_arguments(day: date) -> dict[str, object]:
    return {"date": date_argument(day)}


def recovery_arguments(day: date) -> dict[str, object]:
    return {"date": date_argument(day), "return_timeseries": False}


def next_activity_page(payload: Mapping[str, object], current_page: int) -> int | None:
    has_more = payload.get("has_more")
    if not isinstance(has_more, bool):
        raise GarminDataError("missing or malformed field: has_more")
    if not has_more:
        return None
    next_page = _required_int(payload, "next_page")
    if next_page <= current_page:
        raise GarminDataError("missing or malformed field: next_page")
    return next_page


def map_activities(payload: Mapping[str, object], local_timezone: tzinfo) -> tuple[Activity, ...]:
    rows = _required_sequence(payload, "activities")
    return tuple(_map_activity(row, local_timezone) for row in rows)


def map_sleep(payload: Mapping[str, object], requested_local_date: date, local_timezone: tzinfo) -> tuple[SleepSession, ...]:
    started_at = _timestamp_millis(payload, "sleep_start")
    ended_at = _timestamp_millis(payload, "sleep_end")
    if datetime.combine(requested_local_date, time.min, tzinfo=local_timezone).utcoffset() is None:
        raise GarminDataError("missing or malformed local timezone")
    return (
        SleepSession(
            external_id=f"sleep:{requested_local_date.isoformat()}",
            started_at=started_at,
            ended_at=ended_at,
            local_date=requested_local_date,
            duration_seconds=_required_int(payload, "sleep_seconds"),
            score=_optional_float(payload, "sleep_score"),
        ),
    )


def map_recovery(payload: Mapping[str, object], local_timezone: tzinfo) -> tuple[RecoverySignal, ...]:
    local_date = _required_date(payload, "date")
    measured_at = _naive_timestamp(payload, "sleep_end", local_timezone)
    return tuple(
        RecoverySignal(
            external_id=f"hrv:{local_date.isoformat()}:{metric_name}",
            local_date=local_date,
            measured_at=measured_at,
            metric_name=metric_name,
            value=_required_float(payload, metric_name),
            unit="ms",
        )
        for metric_name in HRV_METRICS
    )


def _map_activity(row: Mapping[str, object], local_timezone: tzinfo) -> Activity:
    started_at = _naive_timestamp(row, "start_time", local_timezone)
    return Activity(
        external_id=_required_text(row, "id"),
        activity_type=_required_text(row, "type"),
        started_at=started_at,
        local_date=started_at.date(),
        duration_seconds=_required_int(row, "duration_seconds"),
        distance_meters=_optional_float(row, "distance_meters"),
        elevation_meters=_optional_float(row, "elevation_gain_meters"),
        average_heart_rate=_optional_float(row, "avg_hr_bpm"),
        max_heart_rate=_optional_float(row, "max_hr_bpm"),
        calories=_optional_float(row, "calories"),
    )


def _required_sequence(payload: Mapping[str, object], key: str) -> Sequence[Mapping[str, object]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise GarminDataError(f"missing or malformed field: {key}")
    return cast(Sequence[Mapping[str, object]], value)


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, (str, int)) and str(value).strip():
        return str(value)
    raise GarminDataError(f"missing or malformed field: {key}")


def _required_int(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value or value < 0:
        raise GarminDataError(f"missing or malformed field: {key}")
    return int(value)


def _required_float(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GarminDataError(f"missing or malformed field: {key}")
    return float(value)


def _optional_float(payload: Mapping[str, object], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    return _required_float(payload, key)


def _required_date(payload: Mapping[str, object], key: str, default: date | None = None) -> date:
    value = payload.get(key)
    if value is None and default is not None:
        return default
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise GarminDataError(f"missing or malformed field: {key}")


def _timestamp_millis(payload: Mapping[str, object], key: str) -> datetime:
    value = payload.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value / 1000, UTC)
    raise GarminDataError(f"missing or malformed field: {key}")


def _naive_timestamp(payload: Mapping[str, object], key: str, local_timezone: tzinfo) -> datetime:
    value = payload.get(key)
    if not isinstance(value, str):
        raise GarminDataError(f"missing or malformed field: {key}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError as error:
            raise GarminDataError(f"missing or malformed field: {key}") from error
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=local_timezone)
    return parsed
