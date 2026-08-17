import type {
  Activity,
  DashboardView,
  Goal,
  HealthSummary,
  TrendBucket,
  TrendSnapshot,
  TrainingSummary,
  ValidatedPlan,
  Workout,
} from "./types";

type RecordValue = Record<string, unknown>;

function isRecord(value: unknown): value is RecordValue {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string { return typeof value === "string"; }
function isNumber(value: unknown): value is number { return typeof value === "number" && Number.isFinite(value); }
function isNullableNumber(value: unknown): value is number | null { return value === null || isNumber(value); }

function isMetricCollection(value: unknown): value is readonly (readonly (string | number)[])[] {
  return Array.isArray(value) && value.every((item) => (
    Array.isArray(item)
    && isString(item[0])
    && isNumber(item[1])
    && (item[2] === undefined || isString(item[2]) || isNumber(item[2]))
  ));
}

function isTrainingSummary(value: unknown): value is TrainingSummary {
  return isRecord(value)
    && isString(value.start)
    && isString(value.end)
    && isNumber(value.activity_count)
    && isNumber(value.duration_seconds)
    && isNumber(value.distance_meters)
    && isNumber(value.elevation_meters)
    && isMetricCollection(value.sport_counts)
    && isNullableNumber(value.training_load);
}

function isHealthSummary(value: unknown): value is HealthSummary {
  return isRecord(value)
    && isString(value.start)
    && isString(value.end)
    && typeof value.available === "boolean"
    && isNullableNumber(value.average_sleep_seconds)
    && isNullableNumber(value.average_sleep_score)
    && isMetricCollection(value.recovery_metrics);
}

function isActivity(value: unknown): value is Activity {
  return isRecord(value)
    && isString(value.external_id)
    && isString(value.activity_type)
    && isString(value.started_at)
    && isString(value.local_date)
    && isNumber(value.duration_seconds)
    && isNullableNumber(value.distance_meters)
    && isNullableNumber(value.elevation_meters)
    && isNullableNumber(value.average_heart_rate)
    && isNullableNumber(value.max_heart_rate)
    && isNullableNumber(value.calories);
}

function isGoal(value: unknown): value is Goal {
  return isRecord(value)
    && isString(value.goal_id)
    && isString(value.description)
    && isString(value.target_date);
}

function isWorkout(value: unknown): value is Workout {
  return isRecord(value)
    && isString(value.workout_id)
    && isString(value.scheduled_date)
    && isString(value.activity_type)
    && isNumber(value.duration_seconds)
    && isString(value.intensity)
    && isString(value.purpose)
    && isString(value.explanation);
}

function isValidatedPlan(value: unknown): value is ValidatedPlan {
  if (!isRecord(value) || !isString(value.validated_at) || !isRecord(value.proposal)) return false;
  const proposal = value.proposal;
  return isString(proposal.proposal_id)
    && isString(proposal.goal_id)
    && isString(proposal.week_start)
    && Array.isArray(proposal.workouts)
    && proposal.workouts.every(isWorkout)
    && isString(proposal.explanation)
    && isString(proposal.created_at);
}

export function isDashboardView(value: unknown): value is DashboardView {
  return isRecord(value)
    && isString(value.generated_at)
    && isTrainingSummary(value.training)
    && isHealthSummary(value.health)
    && (value.health_status === "available" || value.health_status === "missing")
    && (value.goal === null || isGoal(value.goal))
    && (value.plan === null || isValidatedPlan(value.plan))
    && Array.isArray(value.recent_activities)
    && value.recent_activities.every(isActivity);
}

function isTrendBucket(value: unknown): value is TrendBucket {
  return value === "week" || value === "month" || value === "year";
}

export function isTrendSnapshot(value: unknown): value is TrendSnapshot {
  return isRecord(value)
    && isString(value.start)
    && isString(value.end)
    && isTrendBucket(value.bucket)
    && Array.isArray(value.training)
    && value.training.every(isTrainingSummary)
    && Array.isArray(value.health)
    && value.health.every(isHealthSummary);
}
