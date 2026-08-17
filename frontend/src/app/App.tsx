import type { RequestState } from "../api/requestState";
import type { DashboardView } from "../api/types";

type AppProps = {
  dashboardState?: RequestState<DashboardView>;
};

export function App({ dashboardState = { status: "idle" } }: AppProps) {
  return (
    <main data-dashboard-status={dashboardState.status}>
      <h1>Garmin Training Dashboard</h1>
    </main>
  );
}
