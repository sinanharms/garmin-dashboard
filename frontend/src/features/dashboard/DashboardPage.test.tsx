import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { DashboardView } from "../../api/types";
import { DashboardPage } from "./DashboardPage";

const useDashboard = vi.fn();
vi.mock("./useDashboard", () => ({ useDashboard: () => useDashboard() }));

const view: DashboardView = {
  generated_at: "2026-08-17T08:00:00Z",
  training: { start: "2026-08-10", end: "2026-08-17", activity_count: 1, duration_seconds: 3600, distance_meters: 10_000, elevation_meters: 100, sport_counts: [], training_load: 60 },
  health: { start: "2026-08-10", end: "2026-08-17", available: false, average_sleep_seconds: null, average_sleep_score: null, recovery_metrics: [] },
  health_status: "missing",
  goal: { goal_id: "goal-1", description: "Run 10 km", target_date: "2026-10-01" },
  plan: null,
  recent_activities: [{ external_id: "activity-1", activity_type: "running", started_at: "2026-08-17T08:00:00Z", local_date: "2026-08-17", duration_seconds: 3600, distance_meters: 10_000, elevation_meters: 100, average_heart_rate: null, max_heart_rate: null, calories: null }],
};

describe("DashboardPage", () => {
  it("renders available dashboard values and explicit missing health", () => {
    useDashboard.mockReturnValue({ status: "success", data: view, retry: vi.fn() });
    render(<DashboardPage />);

    expect(screen.getByRole("heading", { name: "Garmin Training Dashboard" })).toBeVisible();
    expect(screen.getByText("60")).toBeVisible();
    expect(screen.getByText("Health data unavailable")).toBeVisible();
    expect(screen.getByText("Run 10 km")).toBeVisible();
    expect(screen.getByText("Weekly plan unavailable")).toBeVisible();
    expect(screen.getByText(/running/i)).toBeVisible();
  });

  it("shows a retryable safe error", () => {
    const retry = vi.fn();
    useDashboard.mockReturnValue({ status: "error", error: new Error("private response body"), retry });
    render(<DashboardPage />);

    expect(screen.getByText("Dashboard unavailable")).toBeVisible();
    expect(screen.queryByText("private response body")).not.toBeInTheDocument();
  });
});
