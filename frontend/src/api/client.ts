import type { DashboardView, TrendQuery, TrendSnapshot } from "./types";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function requestJson<T>(url: string, failureMessage: string): Promise<T> {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new ApiError(response.status, failureMessage);
  }

  return (await response.json()) as T;
}

export function getDashboard(today?: string): Promise<DashboardView> {
  const query = today === undefined ? "" : `?today=${encodeURIComponent(today)}`;
  return requestJson<DashboardView>(`/api/dashboard${query}`, "Dashboard request failed");
}

export function getTrends(query: TrendQuery): Promise<TrendSnapshot> {
  const params = new URLSearchParams({
    start: query.start,
    end: query.end,
    bucket: query.bucket,
  });
  return requestJson<TrendSnapshot>(
    `/api/dashboard/trends?${params.toString()}`,
    "Trends request failed",
  );
}
