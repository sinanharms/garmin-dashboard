import { describe, expect, it } from "vitest";
import type { DashboardView } from "../../api/types";
import { buildMetricSummaries } from "./dashboardModel";

const viewWithHealth: DashboardView = {
  generated_at: "2026-08-17T08:00:00Z",
  training: {
    start: "2026-08-10",
    end: "2026-08-17",
    activity_count: 1,
    duration_seconds: 3600,
    distance_meters: 10_000,
    elevation_meters: 100,
    sport_counts: [["running", 1]],
    training_load: 60,
  },
  health: {
    start: "2026-08-10",
    end: "2026-08-17",
    available: true,
    average_sleep_seconds: 28_800,
    average_sleep_score: 82,
    recovery_metrics: [["body_battery", 75, "percent"]],
  },
  health_status: "available",
  goal: null,
  plan: null,
  recent_activities: [],
};

describe("buildMetricSummaries", () => {
  it("maps current dashboard values without unsupported metrics", () => {
    const summaries = buildMetricSummaries(viewWithHealth);

    expect(summaries.map((item) => item.id)).toEqual([
      "training-load",
      "activity-volume",
      "elevation",
      "sleep",
      "recovery",
    ]);
    expect(summaries.find((item) => item.id === "training-load")?.value).toBe("60");
    expect(summaries.find((item) => item.id === "recovery")?.status).toBe("available");
  });

  it("keeps missing health values explicit", () => {
    const summaries = buildMetricSummaries({
      ...viewWithHealth,
      health: {
        ...viewWithHealth.health,
        available: false,
        average_sleep_seconds: null,
        average_sleep_score: null,
        recovery_metrics: [],
      },
      health_status: "missing",
    });

    const sleep = summaries.find((item) => item.id === "sleep");
    expect(sleep?.value).toBe("Unavailable");
    expect(sleep?.status).toBe("missing");
  });
});
