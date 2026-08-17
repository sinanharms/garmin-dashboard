import type { TrendSnapshot } from "../../api/types";
import type { TrendPoint } from "../../components/TrendChart/TrendChart";

export type MetricId = "training-load" | "activity-volume" | "elevation" | "sleep" | "recovery";

export function buildTrendPoints(
  metricId: MetricId,
  snapshot: TrendSnapshot,
  recoveryMetricName?: string,
): readonly TrendPoint[] {
  if (metricId === "training-load") {
    return snapshot.training.map((item) => ({ date: item.start, value: item.training_load }));
  }
  if (metricId === "activity-volume") {
    return snapshot.training.map((item) => ({ date: item.start, value: item.duration_seconds }));
  }
  if (metricId === "elevation") {
    return snapshot.training.map((item) => ({ date: item.start, value: item.elevation_meters }));
  }
  if (metricId === "sleep") {
    return snapshot.health.map((item) => ({ date: item.start, value: item.average_sleep_seconds }));
  }
  return snapshot.health.map((item) => {
    const metric = item.recovery_metrics.find(
      (candidate) => candidate[0] === recoveryMetricName && typeof candidate[1] === "number",
    );
    return { date: item.start, value: typeof metric?.[1] === "number" ? metric[1] : null };
  });
}
