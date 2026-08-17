import { describe, expect, it } from "vitest";
import type { HealthSummary, TrendSnapshot } from "../../api/types";
import { buildTrendPoints } from "./trendPoints";

const health = (start: string, sleep: number | null, recovery: number | null): HealthSummary => ({
  start,
  end: start,
  available: sleep !== null || recovery !== null,
  average_sleep_seconds: sleep,
  average_sleep_score: null,
  recovery_metrics: recovery === null ? [] : [["body_battery", recovery, "percent"]],
});

describe("buildTrendPoints", () => {
  it("preserves dated middle and latest gaps for nullable health metrics", () => {
    const snapshot: TrendSnapshot = {
      start: "2026-01-01",
      end: "2026-01-22",
      bucket: "week",
      training: [],
      health: [
        health("2026-01-01", 28_800, 70),
        health("2026-01-08", null, null),
        health("2026-01-15", null, null),
      ],
    };

    expect(buildTrendPoints("sleep", snapshot)).toEqual([
      { date: "2026-01-01", value: 28_800 },
      { date: "2026-01-08", value: null },
      { date: "2026-01-15", value: null },
    ]);
    expect(buildTrendPoints("recovery", snapshot, "body_battery")).toEqual([
      { date: "2026-01-01", value: 70 },
      { date: "2026-01-08", value: null },
      { date: "2026-01-15", value: null },
    ]);
  });
});
