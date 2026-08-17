import { formatDistance, formatDuration } from "../../components/formatters";
import type { DashboardView } from "../../api/types";

export type MetricStatus = "available" | "missing";

export type MetricSummary = {
  id: "training-load" | "activity-volume" | "elevation" | "sleep" | "recovery";
  title: string;
  value: string;
  unit: string;
  status: MetricStatus;
};

function numberValue(value: number | null): string {
  return value === null ? "Unavailable" : String(value);
}

function healthStatus(view: DashboardView): MetricStatus {
  return view.health_status === "available" ? "available" : "missing";
}

export function buildMetricSummaries(view: DashboardView): readonly MetricSummary[] {
  const status = healthStatus(view);
  const recovery = view.health.recovery_metrics[0];

  return [
    { id: "training-load", title: "Training load", value: numberValue(view.training.training_load), unit: "", status: view.training.training_load === null ? "missing" : "available" },
    { id: "activity-volume", title: "Activity volume", value: formatDuration(view.training.duration_seconds), unit: `${view.training.activity_count} activities · ${formatDistance(view.training.distance_meters)}`, status: "available" },
    { id: "elevation", title: "Elevation", value: numberValue(view.training.elevation_meters), unit: "m", status: "available" },
    { id: "sleep", title: "Sleep", value: formatDuration(view.health.average_sleep_seconds), unit: view.health.average_sleep_score === null ? "" : `score ${view.health.average_sleep_score}`, status },
    { id: "recovery", title: "Recovery", value: recovery === undefined ? "Unavailable" : String(recovery[1]), unit: recovery === undefined ? "" : String(recovery[2] ?? ""), status },
  ];
}
