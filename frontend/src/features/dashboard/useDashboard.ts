import { useCallback, useEffect, useState } from "react";
import { ApiError, getDashboard } from "../../api/client";
import type { RequestState } from "../../api/requestState";
import type { DashboardView } from "../../api/types";

export function useDashboard(): RequestState<DashboardView> & { retry: () => void } {
  const [state, setState] = useState<RequestState<DashboardView>>({ status: "loading" });
  const [requestId, setRequestId] = useState(0);
  const retry = useCallback(() => setRequestId((current) => current + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });

    getDashboard().then(
      (data) => { if (!controller.signal.aborted) setState({ status: "success", data }); },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ status: "error", error: error instanceof ApiError ? error : new ApiError(0, "Dashboard request failed") });
        }
      },
    );

    return () => controller.abort();
  }, [requestId]);

  return { ...state, retry };
}
