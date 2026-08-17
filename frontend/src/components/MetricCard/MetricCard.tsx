import { useId, type ReactNode } from "react";
import { StatusBadge, type Status } from "../StatusBadge/StatusBadge";
import styles from "./MetricCard.module.css";

export type MetricCardProps = {
  title: string;
  value: ReactNode;
  unit?: ReactNode;
  supporting?: ReactNode;
  detail?: ReactNode;
  status?: Status;
  layout?: "hero" | "supporting";
  tone?: "cyan" | "green" | "purple";
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

export function MetricCard({
  title,
  value,
  unit,
  supporting,
  detail,
  status,
  layout = "supporting",
  tone = "cyan",
  expanded,
  onToggle,
}: MetricCardProps) {
  const detailId = `${useId()}-detail`;

  return (
    <article className={`${styles.card} ${styles[layout]} ${styles[tone]} ${expanded ? styles.expanded : ""}`}>
      <button
        className={styles.header}
        type="button"
        aria-expanded={expanded}
        aria-controls={expanded && detail ? detailId : undefined}
        onClick={onToggle}
      >
        <span className={styles.title}>{title}</span>
        <span className={styles.chevron} aria-hidden="true">{expanded ? "−" : "+"}</span>
      </button>
      <div className={styles.summary}>
        <span className={styles.measure}><span className={styles.value}>{value}</span>{unit && <span className={styles.unit}>{unit}</span>}</span>
        {status && <StatusBadge status={status} label={statusLabels[status]} />}
      </div>
      {supporting && <p className={styles.supportText}>{supporting}</p>}
      {expanded && detail && <div className={styles.detail} id={detailId}>{detail}</div>}
    </article>
  );
}
