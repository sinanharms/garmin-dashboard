import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getTrends } from "../../api/client";
import type { TrendQuery, TrendSnapshot } from "../../api/types";
import { useTrendDetails } from "./useTrendDetails";

vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
  getTrends: vi.fn(),
}));

const query: TrendQuery = { start: "2026-08-09", end: "2026-08-16", bucket: "week" };
const snapshot = { ...query, training: [], health: [] } satisfies TrendSnapshot;
const mockedGetTrends = vi.mocked(getTrends);

afterEach(() => { vi.resetAllMocks(); });

describe("useTrendDetails", () => {
  it("does not fetch trend details while no card is expanded", () => {
    const { result } = renderHook(() => useTrendDetails(null));

    expect(result.current).toMatchObject({ status: "idle" });
    expect(mockedGetTrends).not.toHaveBeenCalled();
  });

  it("loads trend details and reuses the response for the same query", async () => {
    mockedGetTrends.mockResolvedValue(snapshot);
    const { result, rerender } = renderHook(({ activeQuery }) => useTrendDetails(activeQuery), {
      initialProps: { activeQuery: query as TrendQuery | null },
    });

    expect(result.current).toMatchObject({ status: "loading" });
    await waitFor(() => expect(result.current).toMatchObject({ status: "success", data: snapshot }));

    rerender({ activeQuery: null });
    rerender({ activeQuery: { ...query } });
    await waitFor(() => expect(result.current).toMatchObject({ status: "success", data: snapshot }));
    expect(mockedGetTrends).toHaveBeenCalledOnce();
  });

  it("retries a failed detail request directly", async () => {
    const retryQuery = { ...query, start: "2026-06-01" };
    const retrySnapshot = { ...snapshot, ...retryQuery };
    mockedGetTrends.mockRejectedValueOnce(new Error("request failed")).mockResolvedValueOnce(retrySnapshot);
    const { result } = renderHook(() => useTrendDetails(retryQuery));

    await waitFor(() => expect(result.current.status).toBe("error"));
    act(() => result.current.retry());

    await waitFor(() => expect(result.current).toMatchObject({ status: "success", data: retrySnapshot }));
    expect(mockedGetTrends).toHaveBeenCalledTimes(2);
  });
});
