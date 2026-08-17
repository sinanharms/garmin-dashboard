import styles from "./Gauge.module.css";

type GaugeProps = {
  value: number;
  min: number;
  max: number;
  label: string;
  color: string;
};

const radius = 42;
const circumference = 2 * Math.PI * radius;

export function Gauge({ value, min, max, label, color }: GaugeProps) {
  const range = max - min;
  const progress = range === 0 ? 0 : Math.min(1, Math.max(0, (value - min) / range));
  const dashOffset = circumference * (1 - progress);

  return (
    <div className={styles.gauge}>
      <svg
        className={styles.visual}
        viewBox="0 0 100 100"
        role="img"
        aria-label={`${label}: ${value}`}
      >
        <circle className={styles.track} cx="50" cy="50" r={radius} />
        <circle
          className={styles.arc}
          cx="50"
          cy="50"
          r={radius}
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
        />
      </svg>
      <div className={styles.text}>
        <strong>{value}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}
