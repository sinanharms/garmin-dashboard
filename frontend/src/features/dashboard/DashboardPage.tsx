import { useState } from "react";
import { MetricCard } from "../../components/MetricCard/MetricCard";
import { TrendChart } from "../../components/TrendChart/TrendChart";
import type { TrendBucket, TrendSnapshot } from "../../api/types";
import { formatDuration, formatInclusivePeriod } from "../../components/formatters";
import { GoalCard } from "./GoalCard";
import { PlanCard } from "./PlanCard";
import { RecentActivities } from "./RecentActivities";
import { buildMetricSummaries } from "./dashboardModel";
import { buildTrendPoints, type MetricId } from "./trendPoints";
import { buildTrendQuery } from "./trendQuery";
import { useDashboard } from "./useDashboard";
import { useTrendDetails } from "./useTrendDetails";
import styles from "./DashboardPage.module.css";

const bucketLabels: Record<TrendBucket, string> = { week: "Weekly", month: "Monthly", year: "Yearly" };

function matchesQuery(snapshot: TrendSnapshot, query: { start: string; end: string; bucket: TrendBucket } | null): boolean {
  return query !== null && snapshot.start === query.start && snapshot.end === query.end && snapshot.bucket === query.bucket;
}

function formatTrendValue(metricId: MetricId, value: number, unit: string): string {
  if (metricId === "activity-volume" || metricId === "sleep") return formatDuration(value);
  return unit === "" ? String(value) : `${value} ${unit}`;
}

export function DashboardPage() {
  const dashboard = useDashboard();
  const [expandedId, setExpandedId] = useState<MetricId | null>(null);
  const [bucket, setBucket] = useState<TrendBucket>("week");
  const query = dashboard.status === "success" && expandedId !== null
    ? buildTrendQuery(dashboard.data.training.end, bucket)
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
      <p className={styles.periodLabel}>{query && formatInclusivePeriod(query.start, query.end)} · {bucketLabels[bucket]}</p>
      {trend.status === "loading" && <p aria-live="polite">Loading trend history…</p>}
      {trend.status === "error" && <div className={styles.detailError}><p role="alert">Trend history unavailable.</p><button type="button" onClick={trend.retry}>Retry trend history</button></div>}
      {trend.status === "success" && matchesQuery(trend.data, query) && <TrendChart points={buildTrendPoints(expandedId, trend.data, expandedMetric?.trendMetricName)} valueLabel={expandedMetric?.title ?? "Metric"} valueFormatter={(value) => formatTrendValue(expandedId, value, expandedMetric?.unit ?? "")} emptyLabel="No trend history for this period." />}
    </div>
  );
  return <main className={styles.page}>
    <header className={styles.header}><p className={styles.eyebrow}>Current dashboard</p><h1>Garmin Training Dashboard</h1><p>{formatInclusivePeriod(view.training.start, view.training.end)} · Generated {new Date(view.generated_at).toLocaleString()}</p></header>
    {view.health_status === "missing" && <p className={styles.notice}>Health data unavailable</p>}
    <section aria-label="Current metrics" className={styles.metrics}>{metrics.map((metric) => <MetricCard key={metric.id} title={metric.title} value={metric.value} unit={metric.unit} supporting={metric.supporting} detail={expandedId === metric.id ? trendDetail : undefined} status={metric.status} layout={metric.layout} tone={metric.tone} expanded={expandedId === metric.id} onToggle={() => setExpandedId((current) => current === metric.id ? null : metric.id)} />)}</section>
    <section className={styles.details}><GoalCard goal={view.goal} /><PlanCard plan={view.plan} /><RecentActivities activities={view.recent_activities} /></section>
  </main>;
}
