# React Dashboard Redesign

## Status

Approved design. Implementation is intentionally not included in this document.

## Goal

Replace the provisional static dashboard with a long-term React + TypeScript + Vite frontend inspired by the supplied dark health-dashboard reference.

The first frontend slice must show useful current Garmin values immediately, then reveal historical context and deeper explanation when a user expands a card. Existing FastAPI dashboard and trend APIs remain the source of truth.

## Non-goals

- No public hosting, accounts, social features, or remote access.
- No SSR framework or separate frontend deployment service.
- No invented Garmin metrics such as strain, recovery percentage, or stress score when the backend does not expose equivalent data.
- No direct browser access to Garmin, MCP, SQLite, credentials, or token state.
- No unrelated backend refactor.

## Approved technical direction

Create a separate `frontend/` React + TypeScript + Vite application. FastAPI remains the production host and serves the built frontend assets. The browser communicates with same-origin `/api/*` routes.

Development flow:

```text
Vite dev server → proxy /api/* → FastAPI
Vite production build → frontend/dist → FastAPI static serving
```

The frontend owns presentation, interaction, formatting, and request state. FastAPI, application services, and Pydantic models remain responsible for data access, business rules, and response contracts.

Suggested source boundaries:

```text
frontend/
  src/
    app/
      App.tsx
      routes.tsx
    api/
      client.ts
      types.ts
    components/
      Card/
      Gauge/
      TrendChart/
      StatusBadge/
    features/
      dashboard/
      trends/
      planning/
      activities/
      system-health/
    styles/
      tokens.css
      globals.css
```

Keep code files below 300 lines. Components should have one clear responsibility and receive data through typed props.

## Information architecture

Initial routes:

1. Dashboard overview.
2. Trends explorer.
3. Training plan.
4. Activity details.
5. System health.

The first implementation may render only the dashboard route, but its shell and feature boundaries must not prevent the later routes.

Dashboard composition:

```text
DashboardPage
├── Header and date-range controls
├── Current metric card grid
├── Training and health trend cards
├── Goal and weekly-plan cards
└── Recent activity list
```

Initial cards use fields already supported by `DashboardView` and `TrendSnapshot`:

- Training load.
- Activity count, duration, distance, and elevation.
- Sport mix.
- Average sleep duration and sleep score.
- Recovery signals.
- Goal and target date.
- Weekly workouts and explanations.
- Recent activities.

## Card interaction model

All metric cards use a shared `MetricCard` contract:

- Summary: current value, unit, label, status, and optional comparison.
- Detail: historical chart, date range, breakdown, and explanation.
- Source state: loading, available, missing, stale, or error.
- Expand control: keyboard-accessible button with `aria-expanded`.

Collapsed cards prioritize the current value. Cards with a compact visual preview may show a small sparkline or gauge, but the value remains readable without relying on color or graphics.

Clicking or activating a card expands it inline within the CSS grid. The expanded card grows to a wider/full-row layout on larger screens and full width on mobile. It shows historical data and more detailed context without changing route or losing dashboard context.

Card expansion lazily requests `/api/dashboard/trends`. Trend responses are cached by date range and bucket so cards reuse the same response. Already-loaded summary values remain visible while detail data loads or fails.

The default interaction allows one expanded card at a time on the dashboard to keep grid movement predictable. The component remains reusable if future detail pages need multiple expanded panels.

## Visual system

Use a reference-inspired dark visual language:

- Canvas: near-black `#070a0c`.
- Card surfaces: charcoal `#11171b` and elevated `#182126`.
- Primary text: warm white.
- Secondary text: muted blue-gray.
- Cyan: activity and training.
- Green: recovery and healthy state.
- Purple: sleep and planning.
- Amber: warnings and comparisons.
- Red: errors and unavailable data.

Use a 12-column desktop grid, compact supporting cards, larger hero cards, and responsive one-column mobile layout. Expanded cards span a wider region or full row. Cards use rounded corners, thin borders, restrained shadows, and subtle accent glow. Labels are compact and uppercase; numeric values are visually dominant.

Use CSS design tokens and isolated component styles. Use inline SVG components for gauges and trend charts so the visual system remains controllable without a chart-library lock-in. Every visual must have an accessible text representation.

Do not add external fonts or runtime image dependencies for the first slice.

## Data flow

Initial load:

```text
App shell
  → GET /api/dashboard
  → parse typed response
  → render current cards
```

Expanded detail:

```text
MetricCard
  → GET /api/dashboard/trends?start=...&end=...&bucket=...
  → cache response by query
  → render historical detail
```

`api/client.ts` owns request construction, response parsing, and HTTP error mapping. `api/types.ts` mirrors the FastAPI response shapes. API types must stay aligned with Pydantic models; generated OpenAPI types can replace manual mirrors in a later maintenance step.

Components must not perform business calculations. Date, duration, distance, and unit formatting belongs in shared formatter modules. The frontend may format and compare values already returned by the API; it must not infer medical limits or invent missing metrics.

## Loading, missing, stale, and error states

Use an explicit discriminated request state:

```text
idle | loading | success(data) | error(error)
```

Rules:

- Initial failure renders a clear dashboard error with retry.
- Detail failure affects only the expanded card.
- Summary content remains visible while detail content loads.
- `health_status: "missing"` renders an explicit missing-health state.
- Missing values remain unavailable; they are not converted to zero.
- Freshness is shown from backend-provided timestamps. The frontend must not guess stale status from page load time.
- Retry actions issue a new request and preserve the last successful data.
- No credentials, tokens, raw MCP payloads, or internal stack traces are rendered.

If stale-health metadata becomes necessary, extend the backend response explicitly rather than deriving it in React.

## Accessibility and responsive behavior

- Card expansion is available by mouse, keyboard, and assistive technology.
- Expand controls expose their expanded/collapsed state.
- Focus remains predictable after expansion and retry.
- Color is never the only status indicator.
- Charts include labels, summaries, and readable values.
- Layout works at desktop, tablet, and mobile widths.
- Touch targets remain usable on small screens.
- Reduced-motion preferences disable decorative expansion/glow animation.

## Verification

Frontend verification must include:

- TypeScript type checking.
- Vite production build.
- Component tests for current, expanded, loading, missing, stale, and error states.
- Keyboard/accessibility test for card expansion.
- API contract tests against existing FastAPI responses.
- Browser smoke test for dashboard load and trend expansion.
- Responsive checks at desktop, tablet, and mobile widths.

Existing Docker Compose and Python checks remain required. The frontend build must be reproducible in the application image without exposing credentials or adding a public service.

## Delivery phases

1. Scaffold `frontend/` with React + TypeScript + Vite and establish production asset serving.
2. Build design tokens, shared card primitives, typed API client, and explicit request states.
3. Rebuild the dashboard summary using `/api/dashboard`.
4. Add inline expansion and historical trend loading using `/api/dashboard/trends`.
5. Add responsive/accessibility coverage and Docker build verification.
6. Remove the provisional static dashboard only after the React path passes the full verification set.
7. Add trends, planning, activity, and system-health routes incrementally using the same boundaries.
