# Story: React dashboard redesign

## Summary

As the dashboard operator, I want a responsive React dashboard that shows current Garmin values first and reveals historical context through accessible inline card expansion.

## Status

Implemented. FastAPI serves the production Vite build, and the React dashboard progressively loads current summaries and historical detail from same-origin APIs.

## Context

- [Architecture overview](../architecture/overview.md)
- [Dashboard and trends story](dashboard-and-trends.md)
- [Application API](../api/application.md)
- [Security convention](../conventions/security-and-secrets.md)
- [Archived approved design](../archive/specs/2026-08-17-react-dashboard-redesign-design.md)
- [Open questions](../decisions/open-questions.md)

## Acceptance Criteria

1. A separate React + TypeScript + Vite frontend uses same-origin `/api/*` requests.
2. FastAPI remains production host and source of truth for data access, business rules, and response contracts.
3. Dashboard cards show supported training, sleep, recovery, goal, plan, and activity values without inventing metrics.
4. Cards expose keyboard-accessible expansion with `aria-expanded`; one dashboard card is expanded at a time.
5. Expanded cards lazily request and cache `/api/dashboard/trends` details while preserving summary values.
6. Loading, missing, stale, and error states remain explicit; missing values are not converted to zero.
7. Color is not the only status signal, visuals have text alternatives, and reduced-motion preferences are respected.
8. Frontend tests, type checks, production build, API contract checks, and responsive/accessibility browser smoke pass for the shipped React UI.

## Testing Notes

Component/API tests cover summary, expansion, retry, nullable trends, and request behavior. The production Playwright smoke loads the built JS through FastAPI and checks expansion at desktop, tablet, and mobile widths. Type checking, Vite build verification, Compose validation, and Python checks remain required.
