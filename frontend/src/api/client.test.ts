import { afterEach, describe, expect, it, vi } from "vitest";
import { getDashboard, getTrends } from "./client";

describe("dashboard API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requests the dashboard endpoint and returns typed JSON", async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({
          generated_at: "2026-08-17T08:00:00Z",
          training: { start: "2026-08-10", end: "2026-08-18", activity_count: 0, duration_seconds: 0, distance_meters: 0, elevation_meters: 0, sport_counts: [], training_load: null },
          health: { start: "2026-08-10", end: "2026-08-18", available: false, average_sleep_seconds: null, average_sleep_score: null, recovery_metrics: [] },
          health_status: "missing", goal: null, plan: null, recent_activities: [],
        }), { status: 200 }),
      ),
    );

    await expect(getDashboard("2026-08-17", controller.signal)).resolves.toMatchObject({
      health_status: "missing",
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/dashboard?today=2026-08-17",
      expect.objectContaining({ headers: { Accept: "application/json" }, signal: controller.signal }),
    );
  });

  it("requests trends with the provided query values", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ start: "2026-01-01", end: "2026-08-17", bucket: "month", training: [], health: [] }), { status: 200 }),
      ),
    );

    await expect(
      getTrends({ start: "2026-01-01", end: "2026-08-17", bucket: "month" }),
    ).resolves.toMatchObject({ bucket: "month" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/dashboard/trends?start=2026-01-01&end=2026-08-17&bucket=month",
      expect.any(Object),
    );
  });

  it("maps an HTTP failure without exposing response internals", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("secret token", { status: 503 })),
    );

    await expect(getDashboard()).rejects.toMatchObject({
      status: 503,
      message: "Dashboard request failed",
    });
    await expect(getDashboard()).rejects.not.toHaveProperty("body");
  });

  it("rejects a dashboard response that does not match the API contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ health_status: "missing" }), { status: 200 }),
      ),
    );

    await expect(getDashboard()).rejects.toMatchObject({
      status: 0,
      message: "Dashboard response invalid",
    });
  });

  it("rejects a trends response that does not match the API contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ bucket: "month" }), { status: 200 }),
      ),
    );

    await expect(getTrends({ start: "2026-01-01", end: "2026-08-17", bucket: "month" })).rejects.toMatchObject({
      status: 0,
      message: "Trends response invalid",
    });
  });
});
