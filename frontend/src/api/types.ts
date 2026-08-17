export type Activity = {
  readonly external_id: string;
  readonly activity_type: string;
  readonly started_at: string;
  readonly local_date: string;
  readonly duration_seconds: number;
  readonly distance_meters: number | null;
  readonly elevation_meters: number | null;
  readonly average_heart_rate: number | null;
  readonly max_heart_rate: number | null;
  readonly calories: number | null;
};

export type TrainingSummary = {
  readonly start: string;
  readonly end: string;
  readonly activity_count: number;
  readonly duration_seconds: number;
  readonly distance_meters: number;
  readonly elevation_meters: number;
  readonly sport_counts: readonly (readonly (string | number)[])[];
  readonly training_load: number | null;
};

export type HealthSummary = {
  readonly start: string;
  readonly end: string;
  readonly available: boolean;
  readonly average_sleep_seconds: number | null;
  readonly average_sleep_score: number | null;
  readonly recovery_metrics: readonly (readonly (string | number)[])[];
};

export type Goal = {
  readonly goal_id: string;
  readonly description: string;
  readonly target_date: string;
};

export type Workout = {
  readonly workout_id: string;
  readonly scheduled_date: string;
  readonly activity_type: string;
  readonly duration_seconds: number;
  readonly intensity: string;
  readonly purpose: string;
  readonly explanation: string;
};

export type PlanProposal = {
  readonly proposal_id: string;
  readonly goal_id: string;
  readonly week_start: string;
  readonly workouts: readonly Workout[];
  readonly explanation: string;
  readonly created_at: string;
};

export type ValidatedPlan = {
  readonly proposal: PlanProposal;
  readonly validated_at: string;
};

export type DashboardView = {
  readonly generated_at: string;
  readonly training: TrainingSummary;
  readonly health: HealthSummary;
  readonly health_status: "available" | "missing";
  readonly goal: Goal | null;
  readonly plan: ValidatedPlan | null;
  readonly recent_activities: readonly Activity[];
};

export type TrendBucket = "week" | "month" | "year";

export type TrendQuery = {
  readonly start: string;
  readonly end: string;
  readonly bucket: TrendBucket;
};

export type TrendSnapshot = {
  readonly start: string;
  readonly end: string;
  readonly bucket: TrendBucket;
  readonly training: readonly TrainingSummary[];
  readonly health: readonly HealthSummary[];
};
