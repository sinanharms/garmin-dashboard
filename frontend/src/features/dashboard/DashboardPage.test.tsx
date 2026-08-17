import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getTrends } from "../../api/client";
import type { DashboardView } from "../../api/types";
import { DashboardPage } from "./DashboardPage";

const useDashboard = vi.fn();
vi.mock("./useDashboard", () => ({ useDashboard: () => useDashboard() }));
vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
  getTrends: vi.fn(),
}));

const mockedGetTrends = vi.mocked(getTrends);

afterEach(() => { vi.resetAllMocks(); });

const view: DashboardView = {
  generated_at: "2026-08-17T08:00:00Z",
  training: { start: "2026-08-10", end: "2026-08-18", activity_count: 1, duration_seconds: 3600, distance_meters: 10_000, elevation_meters: 100, sport_counts: [["running", 1]], training_load: 60 },
  health: { start: "2026-08-10", end: "2026-08-18", available: false, average_sleep_seconds: null, average_sleep_score: null, recovery_metrics: [] },
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
    expect(screen.getByText("2026-08-10 – 2026-08-17", { exact: false })).toBeVisible();
    expect(screen.getByText(/1 activity · 10\.0 km · running: 1/i)).toBeVisible();
    expect(screen.getByText("Weekly plan unavailable")).toBeVisible();
    expect(screen.getAllByText(/running/i)).toHaveLength(2);
  });

  it("shows a retryable safe error", () => {
    const retry = vi.fn();
    useDashboard.mockReturnValue({ status: "error", error: new Error("private response body"), retry });
    render(<DashboardPage />);

    expect(screen.getByText("Dashboard unavailable")).toBeVisible();
    expect(screen.queryByText("private response body")).not.toBeInTheDocument();
  });

  it("loads weekly history inline for one expanded metric", async () => {
    const user = userEvent.setup();
    let resolveTrend: (value: Parameters<typeof mockedGetTrends.mockResolvedValue>[0]) => void;
    useDashboard.mockReturnValue({ status: "success", data: view, retry: vi.fn() });
    mockedGetTrends.mockImplementationOnce(() => new Promise((resolve) => { resolveTrend = resolve; }));
    render(<DashboardPage />);

    await user.click(screen.getByRole("button", { name: /training load/i }));

    expect(mockedGetTrends.mock.calls[0]?.[0]).toEqual({ start: "2026-05-26", end: "2026-08-18", bucket: "week" });
    expect(screen.getByText("Loading trend history…")).toBeVisible();
    resolveTrend!({ start: "2026-05-26", end: view.training.end, bucket: "week", training: [{ ...view.training, start: "2026-05-26", training_load: 50 }, view.training], health: [] });
    await waitFor(() => expect(screen.getByRole("img", { name: "Training load trend" })).toBeVisible());
    expect(screen.getByText("60")).toBeVisible();
  });

  it("retries a detail failure with a focused keyboard-accessible action", async () => {
    const user = userEvent.setup();
    const retryView = { ...view, training: { ...view.training, end: "2026-08-20" } };
    useDashboard.mockReturnValue({ status: "success", data: retryView, retry: vi.fn() });
    mockedGetTrends
      .mockRejectedValueOnce(new Error("request failed"))
      .mockResolvedValueOnce({ start: "2026-05-28", end: retryView.training.end, bucket: "week", training: [retryView.training], health: [] });
    render(<DashboardPage />);

    await user.click(screen.getByRole("button", { name: /training load/i }));
    const retry = await screen.findByRole("button", { name: "Retry trend history" });
    retry.focus();
    expect(retry).toHaveFocus();
    await user.keyboard("{Enter}");

    await waitFor(() => expect(mockedGetTrends).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByRole("img", { name: "Training load trend" })).toBeVisible());
    expect(screen.getByText("60")).toBeVisible();
  });

  it("does not render a previous period while a new period loads", async () => {
    const user = userEvent.setup();
    const periodView = { ...view, training: { ...view.training, end: "2026-08-19" } };
    useDashboard.mockReturnValue({ status: "success", data: periodView, retry: vi.fn() });
    mockedGetTrends
      .mockResolvedValueOnce({ start: "2026-05-27", end: periodView.training.end, bucket: "week", training: [periodView.training], health: [] })
      .mockImplementationOnce(() => new Promise(() => undefined));
    render(<DashboardPage />);

    await user.click(screen.getByRole("button", { name: /training load/i }));
    await waitFor(() => expect(screen.getByRole("img", { name: "Training load trend" })).toBeVisible());
    await user.selectOptions(screen.getByLabelText("Trend period"), "month");

    expect(screen.queryByRole("img", { name: "Training load trend" })).not.toBeInTheDocument();
    expect(screen.getByText("Loading trend history…")).toBeVisible();
  });

  it("plots only the selected recovery metric history", async () => {
    const user = userEvent.setup();
    const recoveryView: DashboardView = {
      ...view,
      training: { ...view.training, start: "2026-07-10", end: "2026-07-18" },
      health: { ...view.health, start: "2026-07-10", end: "2026-07-18", available: true, recovery_metrics: [["body_battery", 70, "percent"]] },
      health_status: "available",
    };
    useDashboard.mockReturnValue({ status: "success", data: recoveryView, retry: vi.fn() });
    mockedGetTrends.mockResolvedValue({
      start: "2026-04-25",
      end: recoveryView.training.end,
      bucket: "week",
      training: [],
      health: [
        { ...recoveryView.health, recovery_metrics: [["hrv", 80, "percent"], ["body_battery", 60, "percent"]] },
        { ...recoveryView.health, recovery_metrics: [["hrv", 81, "percent"], ["body_battery", 70, "percent"]] },
      ],
    });
    render(<DashboardPage />);

    await user.click(screen.getByRole("button", { name: /recovery/i }));

    await waitFor(() => expect(screen.getByText("Recovery: latest value 70 percent · 0 missing periods")).toBeVisible());
  });

  it("renders supported plan and workout explanations", () => {
    useDashboard.mockReturnValue({
      status: "success",
      retry: vi.fn(),
      data: {
        ...view,
        plan: {
          validated_at: "2026-08-17T08:00:00Z",
          proposal: {
            proposal_id: "proposal-1",
            goal_id: "goal-1",
            week_start: "2026-08-17",
            explanation: "Build aerobic consistency.",
            created_at: "2026-08-16T08:00:00Z",
            workouts: [{
              workout_id: "workout-1",
              scheduled_date: "2026-08-18",
              activity_type: "running",
              duration_seconds: 2700,
              intensity: "easy",
              purpose: "Base endurance",
              explanation: "Keep effort conversational.",
            }],
          },
        },
      },
    });

    render(<DashboardPage />);

    expect(screen.getByText("Week of 2026-08-17")).toBeVisible();
    expect(screen.getByText("Build aerobic consistency.")).toBeVisible();
    expect(screen.getByText("Keep effort conversational.")).toBeVisible();
  });
});
