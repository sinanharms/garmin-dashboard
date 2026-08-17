import styles from "./TrendChart.module.css";

export type TrendPoint = number;

type TrendChartProps = {
  points: readonly TrendPoint[];
  valueLabel: string;
  emptyLabel: string;
};

const width = 320;
const height = 120;
const padding = 12;

function getCoordinates(points: readonly number[]): string {
  const minimum = Math.min(...points);
  const maximum = Math.max(...points);
  const range = maximum - minimum || 1;
  const step = points.length === 1 ? 0 : (width - padding * 2) / (points.length - 1);

  return points
    .map((point, index) => {
      const x = padding + index * step;
      const y = height - padding - ((point - minimum) / range) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(" ");
}

export function TrendChart({ points, valueLabel, emptyLabel }: TrendChartProps) {
  if (points.length === 0) {
    return <p className={styles.empty}>{emptyLabel}</p>;
  }

  const coordinates = getCoordinates(points);
  const latest = points[points.length - 1];

  return (
    <div className={styles.chart}>
      <p className={styles.summary}>{valueLabel}: latest value {latest}</p>
      <svg className={styles.visual} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${valueLabel} trend`}>
        <polyline className={styles.area} points={`${padding},${height - padding} ${coordinates} ${width - padding},${height - padding}`} />
        <polyline className={styles.line} points={coordinates} />
      </svg>
    </div>
  );
}
