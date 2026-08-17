import { useState } from "react";
import { MetricCard } from "../../components/MetricCard/MetricCard";
import { GoalCard } from "./GoalCard";
import { PlanCard } from "./PlanCard";
import { RecentActivities } from "./RecentActivities";
import { buildMetricSummaries } from "./dashboardModel";
import { useDashboard } from "./useDashboard";
import styles from "./DashboardPage.module.css";

export function DashboardPage() {
  const dashboard = useDashboard();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (dashboard.status === "loading" || dashboard.status === "idle") return <main className={styles.page}><p>Loading dashboard…</p></main>;
  if (dashboard.status === "error") return <main className={styles.page}><section className={styles.error}><h1>Dashboard unavailable</h1><p>Current dashboard values could not load.</p><button type="button" onClick={dashboard.retry}>Retry</button></section></main>;

  const view = dashboard.data;
  return <main className={styles.page}>
    <header className={styles.header}><p className={styles.eyebrow}>Current dashboard</p><h1>Garmin Training Dashboard</h1><p>{view.training.start} – {view.training.end} · Generated {new Date(view.generated_at).toLocaleString()}</p></header>
    {view.health_status === "missing" && <p className={styles.notice}>Health data unavailable</p>}
    <section aria-label="Current metrics" className={styles.metrics}>{buildMetricSummaries(view).map((metric) => <MetricCard key={metric.id} title={metric.title} value={metric.value} detail={metric.unit} status={metric.status} expanded={expandedId === metric.id} onToggle={() => setExpandedId((current) => current === metric.id ? null : metric.id)} />)}</section>
    <section className={styles.details}><GoalCard goal={view.goal} /><PlanCard plan={view.plan} /><RecentActivities activities={view.recent_activities} /></section>
  </main>;
}
