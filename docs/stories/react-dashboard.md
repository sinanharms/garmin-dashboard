# Story: React dashboard redesign

## Summary

As the dashboard operator, I want a responsive React dashboard that shows current Garmin values first and reveals historical context through accessible inline card expansion.

## Status

Approved future design. No `frontend/` application is currently present, and the current static dashboard remains the shipped browser UI.

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
8. Frontend tests, type checks, production build, API contract checks, and responsive/accessibility checks pass before removing the provisional static UI.

## Testing Notes

The approved design requires frontend component/API tests, type checking, Vite build verification, browser smoke coverage, responsive checks, and existing Compose/Python checks. This story is not an implementation plan; use the archived plan only as historical task context.
