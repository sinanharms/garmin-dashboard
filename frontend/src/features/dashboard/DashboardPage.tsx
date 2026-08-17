import { useState } from "react";
import { MetricCard } from "../../components/MetricCard/MetricCard";
import { TrendChart } from "../../components/TrendChart/TrendChart";
import type { TrendBucket, TrendSnapshot } from "../../api/types";
import { GoalCard } from "./GoalCard";
import { PlanCard } from "./PlanCard";
import { RecentActivities } from "./RecentActivities";
import { buildMetricSummaries } from "./dashboardModel";
import { useDashboard } from "./useDashboard";
import { useTrendDetails } from "./useTrendDetails";
import styles from "./DashboardPage.module.css";

type MetricId = "training-load" | "activity-volume" | "elevation" | "sleep" | "recovery";

const bucketLabels: Record<TrendBucket, string> = { week: "Weekly", month: "Monthly", year: "Yearly" };

function trendPoints(metricId: MetricId, snapshot: TrendSnapshot, recoveryMetricName?: string): readonly number[] {
  if (metricId === "training-load") return snapshot.training.flatMap((item) => item.training_load === null ? [] : [item.training_load]);
  if (metricId === "activity-volume") return snapshot.training.map((item) => item.duration_seconds);
  if (metricId === "elevation") return snapshot.training.map((item) => item.elevation_meters);
  if (metricId === "sleep") return snapshot.health.flatMap((item) => item.average_sleep_seconds === null ? [] : [item.average_sleep_seconds]);
  return snapshot.health.flatMap((item) => item.recovery_metrics.flatMap((metric) => metric[0] === recoveryMetricName && typeof metric[1] === "number" ? [metric[1]] : []));
}

function matchesQuery(snapshot: TrendSnapshot, query: { start: string; end: string; bucket: TrendBucket } | null): boolean {
  return query !== null && snapshot.start === query.start && snapshot.end === query.end && snapshot.bucket === query.bucket;
}

export function DashboardPage() {
  const dashboard = useDashboard();
  const [expandedId, setExpandedId] = useState<MetricId | null>(null);
  const [bucket, setBucket] = useState<TrendBucket>("week");
  const query = dashboard.status === "success" && expandedId !== null
    ? { start: dashboard.data.training.start, end: dashboard.data.training.end, bucket }
    : null;
  const trend = useTrendDetails(query);

  if (dashboard.status === "loading" || dashboard.status === "idle") return <main className={styles.page}><p>Loading dashboard…</p></main>;
  if (dashboard.status === "error") return <main className={styles.page}><section className={styles.error}><h1>Dashboard unavailable</h1><p>Current dashboard values could not load.</p><button type="button" onClick={dashboard.retry}>Retry</button></section></main>;

  const view = dashboard.data;
  const metrics = buildMetricSummaries(view);
  const expandedMetric = expandedId === null ? undefined : metrics.find((metric) => metric.id === expandedId);
  const trendDetail = expandedId === null ? null : (
    <div className={styles.trendDetail}>
      <label className={styles.periodControl}>Trend period
        <select value={bucket} onChange={(event) => setBucket(event.target.value as TrendBucket)}>
          {Object.entries(bucketLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <p className={styles.periodLabel}>{view.training.start} – {view.training.end} · {bucketLabels[bucket]}</p>
      {trend.status === "loading" && <p aria-live="polite">Loading trend history…</p>}
      {trend.status === "error" && <p role="alert">Trend history unavailable. Collapse and expand to retry.</p>}
      {trend.status === "success" && matchesQuery(trend.data, query) && <TrendChart points={trendPoints(expandedId, trend.data, expandedMetric?.trendMetricName)} valueLabel={expandedMetric?.title ?? "Metric"} emptyLabel="No trend history for this period." />}
    </div>
  );
  return <main className={styles.page}>
    <header className={styles.header}><p className={styles.eyebrow}>Current dashboard</p><h1>Garmin Training Dashboard</h1><p>{view.training.start} – {view.training.end} · Generated {new Date(view.generated_at).toLocaleString()}</p></header>
    {view.health_status === "missing" && <p className={styles.notice}>Health data unavailable</p>}
    <section aria-label="Current metrics" className={styles.metrics}>{metrics.map((metric) => <MetricCard key={metric.id} title={metric.title} value={metric.value} detail={expandedId === metric.id ? trendDetail : metric.unit} status={metric.status} expanded={expandedId === metric.id} onToggle={() => setExpandedId((current) => current === metric.id ? null : metric.id)} />)}</section>
    <section className={styles.details}><GoalCard goal={view.goal} /><PlanCard plan={view.plan} /><RecentActivities activities={view.recent_activities} /></section>
  </main>;
}
