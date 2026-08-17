import styles from "./TrendChart.module.css";

export type TrendPoint = { readonly date: string; readonly value: number | null };

type TrendChartProps = {
  points: readonly TrendPoint[];
  valueLabel: string;
  emptyLabel: string;
  valueFormatter?: (value: number) => string;
};

const width = 320;
const height = 120;
const padding = 12;

type Coordinate = { readonly index: number; readonly value: string };

function getSegments(points: readonly TrendPoint[]): readonly Coordinate[][] {
  const values = points.flatMap((point) => point.value === null ? [] : [point.value]);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum || 1;
  const step = points.length === 1 ? 0 : (width - padding * 2) / (points.length - 1);
  const segments: Coordinate[][] = [];
  let segment: Coordinate[] = [];

  points.forEach((point, index) => {
    if (point.value === null) {
      if (segment.length > 0) segments.push(segment);
      segment = [];
      return;
    }
    const x = padding + index * step;
    const y = height - padding - ((point.value - minimum) / range) * (height - padding * 2);
    segment.push({ index, value: `${x},${y}` });
  });
  if (segment.length > 0) segments.push(segment);
  return segments;
}

export function TrendChart({ points, valueLabel, emptyLabel, valueFormatter = String }: TrendChartProps) {
  const available = points.filter((point) => point.value !== null);
  if (available.length === 0) {
    return <p className={styles.empty}>{emptyLabel}</p>;
  }

  const segments = getSegments(points);
  const latest = points[points.length - 1]?.value;
  const missing = points.length - available.length;
  const missingLabel = `${missing} missing ${missing === 1 ? "period" : "periods"}`;
  const formatValue = (value: number | null) => value === null ? "unavailable" : valueFormatter(value);
  const summary = `${valueLabel}: latest value ${formatValue(latest)} · ${missingLabel}`;

  return (
    <div className={styles.chart}>
      <p className={styles.summary}>{summary}</p>
      <svg className={styles.visual} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${valueLabel} trend`}>
        <desc>{points.map((point) => `${point.date}: ${formatValue(point.value)}`).join("; ")}</desc>
        {segments.filter((segment) => segment.length > 1).map((segment) => (
          <polyline key={segment[0].index} className={styles.line} data-testid="trend-segment" points={segment.map((point) => point.value).join(" ")} />
        ))}
        {segments.flat().map((point) => {
          const [cx, cy] = point.value.split(",");
          return <circle key={point.index} className={styles.point} cx={cx} cy={cy} r="3" />;
        })}
      </svg>
    </div>
  );
}
