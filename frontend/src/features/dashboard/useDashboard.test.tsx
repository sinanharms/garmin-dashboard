import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getDashboard } from "../../api/client";
import type { DashboardView } from "../../api/types";
import { useDashboard } from "./useDashboard";

vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
  getDashboard: vi.fn(),
}));

const view = { generated_at: "2026-08-17T08:00:00Z" } as DashboardView;
const mockedGetDashboard = vi.mocked(getDashboard);

afterEach(() => { vi.resetAllMocks(); });

describe("useDashboard", () => {
  it("loads dashboard data and retries a failed request", async () => {
    mockedGetDashboard.mockRejectedValueOnce(new Error("request failed")).mockResolvedValueOnce(view);
    const { result } = renderHook(() => useDashboard());

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current).not.toHaveProperty("data");

    act(() => result.current.retry());
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current).toMatchObject({ status: "success", data: view }));
    expect(mockedGetDashboard).toHaveBeenCalledTimes(2);
  });
});
