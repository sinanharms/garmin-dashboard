import type { ReactNode } from "react";
import { StatusBadge, type Status } from "../StatusBadge/StatusBadge";
import styles from "./MetricCard.module.css";

export type MetricCardProps = {
  title: string;
  value: ReactNode;
  detail?: ReactNode;
  status?: Status;
  expanded: boolean;
  onToggle: () => void;
};

const statusLabels: Record<Status, string> = {
  available: "Available",
  missing: "Unavailable",
  stale: "Stale",
  error: "Error",
  loading: "Loading",
};

export function MetricCard({ title, value, detail, status, expanded, onToggle }: MetricCardProps) {
  const detailId = `${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-detail`;

  return (
    <article className={`${styles.card} ${expanded ? styles.expanded : ""}`}>
      <button
        className={styles.header}
        type="button"
        aria-expanded={expanded}
        aria-controls={detail ? detailId : undefined}
        onClick={onToggle}
      >
        <span className={styles.title}>{title}</span>
        <span className={styles.chevron} aria-hidden="true">{expanded ? "−" : "+"}</span>
      </button>
      <div className={styles.summary}>
        <span className={styles.value}>{value}</span>
        {status && <StatusBadge status={status} label={statusLabels[status]} />}
      </div>
      {expanded && detail && <div className={styles.detail} id={detailId}>{detail}</div>}
    </article>
  );
}
