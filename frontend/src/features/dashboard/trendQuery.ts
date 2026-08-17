import type { TrendBucket, TrendQuery } from "../../api/types";
import { offsetIsoDate } from "../../components/formatters";

const historyDays: Record<TrendBucket, number> = {
  week: 12 * 7,
  month: 12 * 30,
  year: 5 * 365,
};

export function buildTrendQuery(exclusiveEnd: string, bucket: TrendBucket): TrendQuery {
  return {
    start: offsetIsoDate(exclusiveEnd, -historyDays[bucket]),
    end: exclusiveEnd,
    bucket,
  };
}
