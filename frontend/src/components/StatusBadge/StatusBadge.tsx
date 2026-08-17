import styles from "./StatusBadge.module.css";

export type Status = "available" | "missing" | "stale" | "error" | "loading";

type StatusBadgeProps = {
  status: Status;
  label: string;
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[status]}`}>
      <span className={styles.dot} aria-hidden="true" />
      {label}
    </span>
  );
}
