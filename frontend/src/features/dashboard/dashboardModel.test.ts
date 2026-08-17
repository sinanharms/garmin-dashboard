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
    expect(summaries.find((item) => item.id === "activity-volume")).toMatchObject({
      supporting: "1 activity · 10.0 km · running: 1",
    });
    expect(summaries.find((item) => item.id === "elevation")?.unit).toBe("m");
    expect(summaries.find((item) => item.id === "sleep")?.supporting).toBe("Sleep score 82");
    expect(summaries.find((item) => item.id === "recovery")?.unit).toBe("percent");
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

  it("marks sleep missing when aggregate health is available but sleep is incomplete", () => {
    const summaries = buildMetricSummaries({
      ...viewWithHealth,
      health: { ...viewWithHealth.health, average_sleep_seconds: null },
    });

    const sleep = summaries.find((item) => item.id === "sleep");
    expect(sleep).toMatchObject({ value: "Unavailable", status: "missing" });
  });

  it("marks recovery missing when aggregate health is available but recovery is empty", () => {
    const summaries = buildMetricSummaries({
      ...viewWithHealth,
      health: { ...viewWithHealth.health, recovery_metrics: [] },
    });

    const recovery = summaries.find((item) => item.id === "recovery");
    expect(recovery).toMatchObject({ value: "Unavailable", status: "missing" });
  });
});
