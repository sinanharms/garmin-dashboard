import { formatDistance, formatDuration } from "../../components/formatters";
import type { DashboardView } from "../../api/types";

export type MetricStatus = "available" | "missing";

export type MetricSummary = {
  id: "training-load" | "activity-volume" | "elevation" | "sleep" | "recovery";
  title: string;
  value: string;
  unit: string;
  supporting?: string;
  status: MetricStatus;
  layout: "hero" | "supporting";
  tone: "cyan" | "green" | "purple";
  readonly trendMetricName?: string;
};

function numberValue(value: number | null): string {
  return value === null ? "Unavailable" : String(value);
}

function activitySupporting(view: DashboardView): string {
  const count = `${view.training.activity_count} ${view.training.activity_count === 1 ? "activity" : "activities"}`;
  const sports = view.training.sport_counts.flatMap((item) => (
    typeof item[0] === "string" && typeof item[1] === "number" ? [`${item[0]}: ${item[1]}`] : []
  ));
  return [count, formatDistance(view.training.distance_meters), ...sports].join(" · ");
}

export function buildMetricSummaries(view: DashboardView): readonly MetricSummary[] {
  const recovery = view.health.recovery_metrics[0];
  const recoveryMetricName = typeof recovery?.[0] === "string" ? recovery[0] : undefined;
  const sleepStatus: MetricStatus = view.health.average_sleep_seconds === null || view.health.average_sleep_score === null ? "missing" : "available";
  const recoveryStatus: MetricStatus = recovery === undefined ? "missing" : "available";

  return [
    { id: "training-load", title: "Training load", value: numberValue(view.training.training_load), unit: "", status: view.training.training_load === null ? "missing" : "available", layout: "hero", tone: "cyan" },
    { id: "activity-volume", title: "Activity volume", value: formatDuration(view.training.duration_seconds), unit: "", supporting: activitySupporting(view), status: "available", layout: "hero", tone: "cyan" },
    { id: "elevation", title: "Elevation", value: numberValue(view.training.elevation_meters), unit: "m", status: "available", layout: "supporting", tone: "cyan" },
    { id: "sleep", title: "Sleep", value: formatDuration(view.health.average_sleep_seconds), unit: "", supporting: view.health.average_sleep_score === null ? undefined : `Sleep score ${view.health.average_sleep_score}`, status: sleepStatus, layout: "supporting", tone: "purple" },
    { id: "recovery", title: "Recovery", value: recovery === undefined ? "Unavailable" : String(recovery[1]), unit: recovery === undefined ? "" : String(recovery[2] ?? ""), status: recoveryStatus, layout: "supporting", tone: "green", trendMetricName: recoveryMetricName },
  ];
}
