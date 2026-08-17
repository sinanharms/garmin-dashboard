# React Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the provisional static dashboard with a React + TypeScript + Vite dashboard that shows current Garmin values in cards and reveals historical detail through inline expansion.

**Architecture:** Keep FastAPI, application services, and Pydantic responses as the data boundary. Build a separate `frontend/` Vite app, compile it into the application image, and serve its static output from FastAPI. Use focused React components, a typed API client, explicit async request states, and SVG chart primitives.

**Tech Stack:** React 19, TypeScript, Vite, npm, Vitest, Testing Library, FastAPI `StaticFiles`, Docker multi-stage build, inline SVG, existing `/api/dashboard` and `/api/dashboard/trends` endpoints.

## Global Constraints

- Keep runtime configuration in `strava_dashboard.config.Settings` and preserve explicit environment aliases.
- Keep Python and TypeScript source files below 300 lines.
- Use Docker Compose as the primary project workflow; do not install host system packages.
- Do not expose Garmin credentials, tokens, raw MCP payloads, or internal exception details.
- Do not invent unsupported Garmin metrics or convert missing values to zero.
- Keep same-origin browser requests under `/api/*`; do not add a public frontend service.
- Preserve unrelated dirty worktree changes.
- Use TDD for behavior: failing test, focused implementation, passing test, then commit.
- Run `docker compose config`, focused checks, and the full relevant test suite before completion.

---

## File map

Create the frontend build and source tree:

```text
frontend/
  index.html
  package.json
  package-lock.json
  tsconfig.json
  tsconfig.app.json
  tsconfig.node.json
  vite.config.ts
  vitest.config.ts
  src/
    main.tsx
    vite-env.d.ts
    app/App.tsx
    api/client.ts
    api/requestState.ts
    api/types.ts
    components/MetricCard/MetricCard.tsx
    components/MetricCard/MetricCard.module.css
    components/StatusBadge/StatusBadge.tsx
    components/StatusBadge/StatusBadge.module.css
    components/TrendChart/TrendChart.tsx
    components/TrendChart/TrendChart.module.css
    components/Gauge/Gauge.tsx
    components/Gauge/Gauge.module.css
    features/dashboard/DashboardPage.tsx
    features/dashboard/DashboardPage.module.css
    features/dashboard/dashboardModel.ts
    features/dashboard/dashboardModel.test.ts
    features/dashboard/useDashboard.ts
    features/dashboard/useDashboard.test.tsx
    features/dashboard/useTrendDetails.ts
    features/dashboard/useTrendDetails.test.tsx
    features/dashboard/GoalCard.tsx
    features/dashboard/PlanCard.tsx
    features/dashboard/RecentActivities.tsx
    styles/tokens.css
    styles/globals.css
    test/setup.ts
```

Modify production delivery files:

```text
Dockerfile
.dockerignore
README.md
src/strava_dashboard/api/app.py
src/strava_dashboard/api/static/app/.gitkeep
tests/test_api.py
```

Delete only after React delivery verification:

```text
src/strava_dashboard/api/templates/index.html
src/strava_dashboard/api/static/dashboard.js
src/strava_dashboard/api/static/dashboard.css
```

Do not modify existing backend application, domain, adapter, or worker files for this frontend slice.

---

### Task 1: Scaffold the Vite frontend and test harness

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/package-lock.json` via npm
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/globals.css`
- Modify: `Dockerfile` to add a reusable `frontend` build target
- Modify: `.dockerignore`

**Interfaces:**
- Produces `npm run dev`, `npm run build`, `npm run typecheck`, and `npm run test` commands.
- Produces a Vite build rooted at `/static/app/` so FastAPI can serve assets from its existing static mount.
- Produces a React `App` shell that later dashboard tasks can replace without changing `main.tsx`.

- [ ] **Step 1: Write the failing frontend smoke test.**

Create `frontend/src/app/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("renders the dashboard application shell", () => {
    render(<App />);
    expect(screen.getByRole("main")).toHaveTextContent("Garmin Training Dashboard");
  });
});
```

- [ ] **Step 2: Run the test to verify the scaffold is absent.**

Run:

```bash
docker build --target frontend -t garmin-dashboard-frontend .
```

Expected: FAIL because `frontend/package.json` and the Vite target do not exist.

- [ ] **Step 3: Add the minimum Vite React TypeScript scaffold and frontend Docker target.**

Use these package scripts and dependency roles in `frontend/package.json`:

```json
{
  "name": "garmin-dashboard-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc -b --pretty false",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "latest",
    "react-dom": "latest"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "latest",
    "@testing-library/react": "latest",
    "@testing-library/user-event": "latest",
    "@types/react": "latest",
    "@types/react-dom": "latest",
    "@vitejs/plugin-react-swc": "latest",
    "jsdom": "latest",
    "typescript": "latest",
    "vite": "latest",
    "vitest": "latest"
  }
}
```

Resolve and record exact versions in `package-lock.json` with `npm install` inside a Node container. Configure `frontend/vite.config.ts` with React support, `/static/app/` base, `dist` output, and a development proxy:

```ts
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/static/app/",
  plugins: [react()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
```

Configure Vitest with `jsdom`, `src/test/setup.ts`, and global assertions. `main.tsx` must import `tokens.css`, `globals.css`, and render `<App />` into `#root`.

Add this first stage to `Dockerfile` before the existing Python stage so frontend checks remain container-first:

```dockerfile
FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build
```

Generate the lockfile before the first `npm ci` build:

```bash
docker run --rm --mount type=bind,src="$PWD/frontend",dst=/frontend --workdir /frontend node:22-bookworm-slim npm install
```

- [ ] **Step 4: Run the focused frontend checks.**

Run inside the frontend build target:

```bash
docker build --target frontend -t garmin-dashboard-frontend .
docker run --rm garmin-dashboard-frontend npm run typecheck
docker run --rm garmin-dashboard-frontend npm test -- --run
docker run --rm garmin-dashboard-frontend npm run build
```

Expected: the shell test, type check, and Vite build pass; build output contains `dist/index.html` and asset files under `dist/assets/`.

- [ ] **Step 5: Commit the scaffold.**

```bash
git add frontend .dockerignore
git commit -m "feat: scaffold React dashboard frontend"
```

### Task 2: Add typed API contracts and request-state helpers

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/requestState.ts`
- Create: `frontend/src/api/client.test.ts`
- Modify: `frontend/src/app/App.tsx`

**Interfaces:**
- `getDashboard(today?: string): Promise<DashboardView>`
- `getTrends(query: TrendQuery): Promise<TrendSnapshot>`
- `RequestState<T> = { status: "idle" } | { status: "loading" } | { status: "success"; data: T } | { status: "error"; error: ApiError }`
- `TrendQuery = { start: string; end: string; bucket: TrendBucket }`

- [ ] **Step 1: Write API client tests against mocked `fetch`.**

Create tests covering a successful dashboard response, a successful trend response, and redacted HTTP failure:

```tsx
it("requests the dashboard endpoint and returns typed JSON", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ health_status: "missing" }), { status: 200 })));
  await expect(getDashboard("2026-08-17")).resolves.toMatchObject({ health_status: "missing" });
  expect(fetch).toHaveBeenCalledWith("/api/dashboard?today=2026-08-17", expect.any(Object));
});

it("maps an HTTP failure without exposing response internals", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("secret token", { status: 503 })));
  await expect(getDashboard()).rejects.toMatchObject({ status: 503, message: "Dashboard request failed" });
  await expect(getDashboard()).rejects.not.toHaveProperty("body");
});
```

- [ ] **Step 2: Run the API tests to verify missing client code fails.**

```bash
docker run --rm garmin-dashboard-frontend npm test -- --run src/api/client.test.ts
```

Expected: FAIL because the typed models and client functions do not exist.

- [ ] **Step 3: Implement the API types and client.**

Mirror these existing response fields in `types.ts`: `Activity`, `TrainingSummary`, `HealthSummary`, `Goal`, `Workout`, `PlanProposal`, `ValidatedPlan`, `DashboardView`, `TrendBucket`, `TrendQuery`, and `TrendSnapshot`. Use `readonly` arrays for tuple collections and string union types for `health_status` and trend buckets.

Implement `ApiError` with only `status` and a safe user-facing `message`. The request helper must set `Accept: application/json`, reject non-2xx responses with `ApiError`, parse JSON, and never include response bodies in the error object. Build trend query parameters with `URLSearchParams` and preserve the server’s date and bucket values.

Implement `RequestState<T>` as a discriminated union. Do not add a fallback data object.

- [ ] **Step 4: Run API tests and type check.**

```bash
docker run --rm garmin-dashboard-frontend npm test -- --run src/api/client.test.ts
docker run --rm garmin-dashboard-frontend npm run typecheck
```

Expected: all API tests pass and TypeScript reports no errors.

- [ ] **Step 5: Commit the typed boundary.**

```bash
git add frontend/src/api frontend/src/app/App.tsx
git commit -m "feat: add typed dashboard API client"
```

### Task 3: Build reusable visual primitives and formatters

**Files:**
- Create: `frontend/src/components/MetricCard/MetricCard.tsx`
- Create: `frontend/src/components/MetricCard/MetricCard.module.css`
- Create: `frontend/src/components/StatusBadge/StatusBadge.tsx`
- Create: `frontend/src/components/StatusBadge/StatusBadge.module.css`
- Create: `frontend/src/components/TrendChart/TrendChart.tsx`
- Create: `frontend/src/components/TrendChart/TrendChart.module.css`
- Create: `frontend/src/components/Gauge/Gauge.tsx`
- Create: `frontend/src/components/Gauge/Gauge.module.css`
- Create: `frontend/src/components/formatters.ts`
- Create: `frontend/src/components/MetricCard/MetricCard.test.tsx`
- Create: `frontend/src/components/Gauge/Gauge.test.tsx`
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/globals.css`

**Interfaces:**
- `MetricCardProps = { title: string; value: ReactNode; detail?: ReactNode; status?: Status; expanded: boolean; onToggle: () => void }`
- `StatusBadge({ status, label })`
- `TrendChart({ points, valueLabel, emptyLabel })`
- `Gauge({ value, min, max, label, color })`
- `formatDuration(seconds: number | null): string`
- `formatDistance(meters: number | null): string`

- [ ] **Step 1: Write interaction tests for the card primitive.**

```tsx
it("shows summary and expands detail through an accessible control", async () => {
  const user = userEvent.setup();
  render(<MetricCard title="Training load" value="60" expanded={false} onToggle={onToggle} detail={<p>History</p>} />);
  expect(screen.getByText("60")).toBeVisible();
  expect(screen.queryByText("History")).not.toBeVisible();
  await user.click(screen.getByRole("button", { name: /training load/i }));
  expect(onToggle).toHaveBeenCalledOnce();
});
```

Add tests for `aria-expanded`, unavailable status text, gauge text alternatives, and empty chart labels.

- [ ] **Step 2: Run primitive tests to verify missing components fail.**

```bash
docker run --rm garmin-dashboard-frontend npm test -- --run src/components
```

Expected: FAIL because components and formatters do not exist.

- [ ] **Step 3: Implement the primitives.**

`MetricCard` must render a real `<button>` for the header/expand affordance, preserve summary content while detail loads, and render detail only when `expanded` is true. `StatusBadge` must include text, not color alone. `Gauge` must render the numeric value and label as text alongside its SVG arc. `TrendChart` must render an accessible summary and an SVG polyline/area from supplied points; it must render `emptyLabel` when points are empty.

Use CSS tokens for the approved palette and responsive card geometry. Add `@media (prefers-reduced-motion: reduce)` to disable decorative transitions. Keep SVG geometry in the chart/gauge components, not in page components.

- [ ] **Step 4: Run primitive tests and type check.**

```bash
docker run --rm garmin-dashboard-frontend npm test -- --run src/components
docker run --rm garmin-dashboard-frontend npm run typecheck
```

Expected: all primitive tests pass and type checking is clean.

- [ ] **Step 5: Commit the visual primitives.**

```bash
git add frontend/src/components frontend/src/styles
git commit -m "feat: add dashboard card and chart primitives"
```

### Task 4: Render current dashboard values

**Files:**
- Create: `frontend/src/features/dashboard/dashboardModel.ts`
- Create: `frontend/src/features/dashboard/dashboardModel.test.ts`
- Create: `frontend/src/features/dashboard/useDashboard.ts`
- Create: `frontend/src/features/dashboard/useDashboard.test.tsx`
- Create: `frontend/src/features/dashboard/DashboardPage.tsx`
- Create: `frontend/src/features/dashboard/DashboardPage.module.css`
- Create: `frontend/src/features/dashboard/GoalCard.tsx`
- Create: `frontend/src/features/dashboard/PlanCard.tsx`
- Create: `frontend/src/features/dashboard/RecentActivities.tsx`
- Modify: `frontend/src/app/App.tsx`

**Interfaces:**
- `buildMetricSummaries(view: DashboardView): readonly MetricSummary[]`
- `useDashboard(): RequestState<DashboardView> & { retry: () => void }`
- `DashboardPage()` renders current cards from `DashboardView`.

- [ ] **Step 1: Write pure dashboard-model tests.**

Use the existing API fixture shape from `tests/test_api.py` and assert that `buildMetricSummaries` creates current cards for training load, activity volume, elevation, sleep, and recovery without creating unsupported metrics:

```tsx
const summaries = buildMetricSummaries(viewWithHealth);
expect(summaries.map((item) => item.id)).toEqual([
  "training-load",
  "activity-volume",
  "elevation",
  "sleep",
  "recovery",
]);
expect(summaries.find((item) => item.id === "training-load")?.value).toBe("60");
expect(summaries.find((item) => item.id === "recovery")?.status).toBe("available");
```

Add a missing-health case that preserves `null` sleep values and returns a visible `missing` status.

- [ ] **Step 2: Run dashboard-model tests to verify missing implementation fails.**

```bash
docker run --rm garmin-dashboard-frontend npm test -- --run src/features/dashboard/dashboardModel.test.ts
```

Expected: FAIL because the model and formatter functions do not exist.

- [ ] **Step 3: Implement the model and dashboard hook.**

Define the model types before the mapper:

```ts
export type MetricStatus = "available" | "missing";

export type MetricSummary = {
  id: "training-load" | "activity-volume" | "elevation" | "sleep" | "recovery";
  title: string;
  value: string;
  unit: string;
  status: MetricStatus;
};
```

`buildMetricSummaries` may format values but must not calculate a new business metric. Map `training.training_load`, `training.activity_count`, `training.duration_seconds`, `training.distance_meters`, `training.elevation_meters`, `health.average_sleep_seconds`, `health.average_sleep_score`, and `health.recovery_metrics` only.

`useDashboard` must start in `loading`, call `getDashboard`, transition to `success` or safe `error`, and expose `retry` that starts a fresh request. Use an `AbortController` cleanup so unmounted pages do not update state.

- [ ] **Step 4: Implement the dashboard page.**

Render:

- Header with generated timestamp and compact period label.
- Current metric card grid.
- Goal card with description and target date.
- Weekly plan card with each workout’s date, type, duration, intensity, and purpose; show `Weekly plan unavailable` when no plan exists.
- Recent activities list with type, local date, duration, distance, and elevation where available.
- Health missing state when `health_status` is `missing`.

Wire `App.tsx` to render `DashboardPage`. Summary failure must render a retryable error panel and must not expose the `ApiError` response body.

- [ ] **Step 5: Run dashboard tests and build.**

```bash
docker run --rm garmin-dashboard-frontend npm test -- --run src/features/dashboard
docker run --rm garmin-dashboard-frontend npm run typecheck
docker run --rm garmin-dashboard-frontend npm run build
```

Expected: model, hook, and page tests pass; type check and build pass.

- [ ] **Step 6: Commit the current-value dashboard.**

```bash
git add frontend/src/app frontend/src/features/dashboard
git commit -m "feat: render React dashboard summaries"
```

### Task 5: Add inline trend expansion and cached detail loading

**Files:**
- Create: `frontend/src/features/dashboard/useTrendDetails.ts`
- Create: `frontend/src/features/dashboard/useTrendDetails.test.tsx`
- Create: `frontend/src/features/dashboard/trendCache.ts`
- Create: `frontend/src/features/dashboard/trendCache.test.ts`
- Modify: `frontend/src/components/MetricCard/MetricCard.tsx`
- Modify: `frontend/src/features/dashboard/DashboardPage.tsx`
- Modify: `frontend/src/features/dashboard/DashboardPage.module.css`

**Interfaces:**
- `TrendCache.get(query: TrendQuery): TrendSnapshot | undefined`
- `TrendCache.set(query: TrendQuery, value: TrendSnapshot): void`
- `useTrendDetails(query: TrendQuery | null): RequestState<TrendSnapshot>`
- `MetricCard` receives `expanded`, `detail`, and `onToggle` props.

- [ ] **Step 1: Write cache and hook tests.**

```tsx
it("reuses a cached trend response for the same query", () => {
  const cache = new TrendCache();
  cache.set(query, snapshot);
  expect(cache.get({ ...query })).toBe(snapshot);
});

it("does not fetch trend details while no card is expanded", () => {
  renderHook(() => useTrendDetails(null));
  expect(getTrends).not.toHaveBeenCalled();
});
```

Add a test that expands one card, requests the weekly trend, shows loading, then renders the chart; add a failure test that leaves summary visible and shows retryable detail error.

- [ ] **Step 2: Run trend tests to verify missing implementation fails.**

```bash
docker run --rm garmin-dashboard-frontend npm test -- --run src/features/dashboard/trendCache.test.ts src/features/dashboard/useTrendDetails.test.tsx
```

Expected: FAIL because the cache and hook do not exist.

- [ ] **Step 3: Implement query-keyed trend caching.**

Use a stable key:

```ts
function trendKey(query: TrendQuery): string {
  return `${query.start}:${query.end}:${query.bucket}`;
}
```

`useTrendDetails` must return `idle` when query is `null`, read the cache before fetching, set `loading` during a new request, and return `success` or `error` without fallback data. Abort in-flight requests during cleanup.

- [ ] **Step 4: Connect expansion to dashboard cards.**

Allow one expanded card at a time. Derive a query from the dashboard period and selected `TrendBucket`. Map each expanded metric to its relevant `TrendSnapshot.training` or `TrendSnapshot.health` series. Render `TrendChart` with an accessible summary and period labels. Keep summary values visible throughout.

Expansion must be inline: desktop cards widen or span a row; mobile cards occupy full width. The toggle must work with keyboard activation and expose `aria-expanded`.

- [ ] **Step 5: Run trend tests and production build.**

```bash
docker run --rm garmin-dashboard-frontend npm test -- --run src/features/dashboard src/components/MetricCard
docker run --rm garmin-dashboard-frontend npm run typecheck
docker run --rm garmin-dashboard-frontend npm run build
```

Expected: trend cache, hook, interaction, accessibility, typecheck, and build checks pass.

- [ ] **Step 6: Commit inline historical detail.**

```bash
git add frontend/src/components/MetricCard frontend/src/features/dashboard
git commit -m "feat: expand dashboard cards with trend history"
```

### Task 6: Serve the React build from FastAPI and Docker

**Files:**
- Create: `src/strava_dashboard/api/static/app/.gitkeep`
- Modify: `src/strava_dashboard/api/app.py`
- Modify: `Dockerfile`
- Modify: `.dockerignore`
- Modify: `tests/test_api.py`
- Modify: `README.md`

**Interfaces:**
- FastAPI serves React `index.html` at `/`.
- FastAPI serves Vite assets under `/static/app/`.
- Docker final image contains the built frontend and existing Python application.

- [ ] **Step 1: Write the serving test.**

Add an API test that verifies the production shell path is configured without changing API routes. The test must use a temporary built shell directory injected through the app factory, so Python tests do not depend on a host Node install:

```python
def test_dashboard_shell_serves_built_react_index(tmp_path: Path) -> None:
    app = create_app(
        FakeDashboardService(),
        FakeInspectionService(),
        FakeOperationsService(),
        frontend_dir=tmp_path,
    )
    (tmp_path / "index.html").write_text('<div id="root">Garmin Training Dashboard</div>', encoding="utf-8")

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.text == '<div id="root">Garmin Training Dashboard</div>'
```

- [ ] **Step 2: Run the serving test to verify the current app fails.**

```bash
docker compose run --rm app uv run pytest tests/test_api.py::test_dashboard_shell_serves_built_react_index -q
```

Expected: FAIL because `create_app` has no `frontend_dir` boundary and `/` still serves the template shell.

- [ ] **Step 3: Add an explicit frontend asset directory to `create_app`.**

Add keyword-only `frontend_dir: Path | None = None`. Resolve `frontend_dir or BASE_DIR / "static" / "app"`, mount it at `/static/app`, and return `FileResponse(frontend_dir / "index.html")` from `/`. Keep the existing `/static` mount only while old assets remain. Ensure the committed `.gitkeep` makes the directory available before a Docker build.

- [ ] **Step 4: Copy the built frontend into the final application image.**

Keep the Node `frontend` stage from Task 1 and existing Python final stage. Copy `/frontend/dist` into `/app/src/strava_dashboard/api/static/app` after copying Python source. Do not add a production frontend Compose service or publish another port.

Add `frontend/node_modules`, `frontend/dist`, and `frontend/.vite` to `.dockerignore`; keep `frontend/package-lock.json` in the build context.

- [ ] **Step 5: Remove provisional delivery assets and update README.**

Only after the React build is copied into the final image, delete `src/strava_dashboard/api/templates/index.html`, `dashboard.js`, and `dashboard.css`. Update README setup with the Docker build path and state that the browser UI is served by FastAPI from the built frontend.

- [ ] **Step 6: Run serving and Compose checks.**

```bash
docker compose config
docker compose build app
docker compose run --rm app uv run pytest tests/test_api.py -q
docker compose run --rm app uv run pytest -q
```

Expected: Compose config is valid, the app image builds the React bundle, API tests pass, and the full relevant Python suite passes.

- [ ] **Step 7: Commit production integration.**

```bash
git add Dockerfile .dockerignore README.md src/strava_dashboard/api/app.py src/strava_dashboard/api/static/app tests/test_api.py
git rm src/strava_dashboard/api/templates/index.html src/strava_dashboard/api/static/dashboard.js src/strava_dashboard/api/static/dashboard.css
git commit -m "feat: serve React dashboard from FastAPI"
```

### Task 7: Run end-to-end verification and document handoff

**Files:**
- Modify: `README.md` only if verification commands or frontend development instructions need correction.
- Test: `frontend/src/**/*.test.ts`, `frontend/src/**/*.test.tsx`, `tests/test_api.py`.

**Interfaces:**
- The final branch provides reproducible frontend and Python checks through containers.
- The final UI keeps API behavior unchanged and supports current-value cards plus inline trend expansion.

- [ ] **Step 1: Run the frontend test suite in its build target.**

```bash
docker build --target frontend -t garmin-dashboard-frontend .
docker run --rm garmin-dashboard-frontend npm run typecheck
docker run --rm garmin-dashboard-frontend npm test -- --run
docker run --rm garmin-dashboard-frontend npm run build
```

Expected: typecheck, all frontend tests, and production build pass.

- [ ] **Step 2: Run Python checks through Compose.**

```bash
docker compose config
docker compose run --rm app uv run pytest tests/test_config.py -q
docker compose run --rm app uv run pytest -q
```

Expected: valid Compose configuration and passing focused/full suites.

- [ ] **Step 3: Verify the built shell and API through the loopback port.**

```bash
docker compose up --build -d app
curl --fail http://127.0.0.1:8000/
curl --fail http://127.0.0.1:8000/api/dashboard
curl --fail 'http://127.0.0.1:8000/api/dashboard/trends?start=2026-08-01&end=2026-08-17&bucket=week'
docker compose stop app
```

Expected: root returns the React shell, dashboard returns JSON, trends returns a typed snapshot, and no response contains credentials or token data.

- [ ] **Step 4: Run final repository checks and inspect scope.**

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intentional frontend/spec/plan changes are present; unrelated pre-existing dirty changes remain untouched.

- [ ] **Step 5: Commit any documentation-only correction.**

```bash
git add README.md
git commit -m "docs: document React dashboard verification"
```

Run this step only when README changed in Step 2 or Step 3. If no correction is needed, leave no empty commit.

---

## Plan self-review

- Spec coverage: architecture, card progressive disclosure, visual system, typed API flow, explicit states, accessibility, responsive behavior, SVG visuals, Docker delivery, and verification each map to one or more tasks.
- Completeness scan: no task depends on unspecified metrics, unchosen chart libraries, host-installed tools, or undefined API routes.
- Type consistency: `DashboardView`, `TrendSnapshot`, `TrendQuery`, `RequestState`, `MetricCardProps`, `TrendCache`, and `useTrendDetails` are introduced before their consumers.
- Scope safety: backend domain and adapter code remain untouched; production changes are limited to static asset serving and Docker build integration.
