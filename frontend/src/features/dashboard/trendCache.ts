import type { TrendQuery, TrendSnapshot } from "../../api/types";

function trendKey(query: TrendQuery): string {
  return `${query.start}:${query.end}:${query.bucket}`;
}

export class TrendCache {
  private readonly snapshots = new Map<string, TrendSnapshot>();

  get(query: TrendQuery): TrendSnapshot | undefined {
    return this.snapshots.get(trendKey(query));
  }

  set(query: TrendQuery, value: TrendSnapshot): void {
    this.snapshots.set(trendKey(query), value);
  }
}
