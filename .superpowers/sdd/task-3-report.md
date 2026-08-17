# Task 3 Report: Reusable visual primitives and formatters

## Outcome

Implemented the approved reusable frontend visual primitives for the React/Vite dashboard. The change is limited to `frontend/src/components` and the two requested global style files; backend files and unrelated frontend files were not modified.

## Implemented

- `MetricCard`: accessible button header with `aria-expanded`, preserved summary value, optional status badge, and conditional expanded detail.
- `StatusBadge`: textual status label with visual status treatment for available, missing, stale, error, and loading states.
- `Gauge`: inline SVG circular gauge with numeric value and label rendered as text and an accessible SVG name.
- `TrendChart`: inline SVG polyline/area chart with accessible latest-value summary and explicit empty state.
- `formatDuration`: formats seconds as minutes or hours/minutes and preserves `null` as `Unavailable`.
- `formatDistance`: formats meters as kilometers and preserves `null` as `Unavailable`.
- Dark design tokens, responsive card geometry, focus-visible styling, and reduced-motion rules for decorative transitions.

## TDD evidence

Added focused tests before implementation. The initial clean-container run failed because the requested component imports did not exist. After implementation, the focused suite passed with 5 tests across 2 files.

Coverage includes card interaction and `aria-expanded`, summary preservation during expansion, textual unavailable status, empty chart messaging, and gauge text alternatives.

## Verification

- `npm run typecheck` — passed.
- `npm test` — passed: 4 files, 9 tests.
- `npm run build` — passed.
- `git diff --check` — passed.
- Source files remain below the 300-line limit.
- Generated `frontend/node_modules` was removed before commit and no dependency artifacts are included.

## Concerns / follow-ups

- `TrendChart` currently accepts numeric points; date labels and domain-specific series mapping belong to the later dashboard/detail tasks.
- Formatter output uses metric kilometers and compact `h`/`m` units; locale-specific formatting can be introduced if the approved UI requirements later call for it.
