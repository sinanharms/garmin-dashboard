import { useCallback, useEffect, useState } from "react";
import { ApiError, getTrends } from "../../api/client";
import type { RequestState } from "../../api/requestState";
import type { TrendQuery, TrendSnapshot } from "../../api/types";
import { TrendCache } from "./trendCache";

const cache = new TrendCache();

function requestError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError(0, "Trends request failed");
}

export function useTrendDetails(query: TrendQuery | null): RequestState<TrendSnapshot> & { retry: () => void } {
  const [state, setState] = useState<RequestState<TrendSnapshot>>({ status: "idle" });
  const [requestId, setRequestId] = useState(0);
  const retry = useCallback(() => setRequestId((current) => current + 1), []);
  const start = query?.start;
  const end = query?.end;
  const bucket = query?.bucket;

  useEffect(() => {
    if (query === null) {
      setState({ status: "idle" });
      return;
    }

    const cached = cache.get(query);
    if (cached !== undefined) {
      setState({ status: "success", data: cached });
      return;
    }

    const controller = new AbortController();
    setState({ status: "loading" });
    getTrends(query, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        cache.set(query, data);
        setState({ status: "success", data });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ status: "error", error: requestError(error) });
      });

    return () => controller.abort();
  }, [start, end, bucket, requestId]);

  return { ...state, retry };
}
