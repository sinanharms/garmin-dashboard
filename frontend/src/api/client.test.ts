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
        new Response(JSON.stringify({ health_status: "missing" }), { status: 200 }),
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
        new Response(JSON.stringify({ bucket: "month" }), { status: 200 }),
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
});
