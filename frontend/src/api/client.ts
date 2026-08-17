import type { DashboardView, TrendQuery, TrendSnapshot } from "./types";
import { isDashboardView, isTrendSnapshot } from "./guards";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function requestJson<T>(
  url: string,
  failureMessage: string,
  invalidResponseMessage: string,
  validator: (value: unknown) => value is T,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new ApiError(response.status, failureMessage);
  }

  const value: unknown = await response.json();
  if (!validator(value)) throw new ApiError(0, invalidResponseMessage);
  return value;
}

export function getDashboard(today?: string, signal?: AbortSignal): Promise<DashboardView> {
  const query = today === undefined ? "" : `?today=${encodeURIComponent(today)}`;
  return requestJson<DashboardView>(
    `/api/dashboard${query}`,
    "Dashboard request failed",
    "Dashboard response invalid",
    isDashboardView,
    signal,
  );
}

export function getTrends(query: TrendQuery, signal?: AbortSignal): Promise<TrendSnapshot> {
  const params = new URLSearchParams({
    start: query.start,
    end: query.end,
    bucket: query.bucket,
  });
  return requestJson<TrendSnapshot>(
    `/api/dashboard/trends?${params.toString()}`,
    "Trends request failed",
    "Trends response invalid",
    isTrendSnapshot,
    signal,
  );
}
