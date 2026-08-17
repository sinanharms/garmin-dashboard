# Task 1 Report: Scaffold the Vite Frontend and Test Harness

## Result

Implemented the Task 1 frontend scaffold on branch `feat/react-dashboard-redesign-v2`.

The frontend now provides:

- Vite React TypeScript development and production configuration.
- `/static/app/` as the Vite base path.
- Development proxying for `/api` to `http://127.0.0.1:8000`.
- Vitest with jsdom, Testing Library setup, and a dashboard shell smoke test.
- `npm run dev`, `npm run build`, `npm run typecheck`, and `npm run test` scripts.
- A reusable `frontend` Docker build target using Node 22.
- Ignore rules for generated frontend dependencies and build output.

## TDD evidence

1. Added `frontend/src/app/App.test.tsx` before the implementation.
2. Ran `docker build --target frontend -t garmin-dashboard-frontend .` and confirmed RED: the `frontend` target did not exist.
3. Added the minimal scaffold and `App` implementation.
4. Ran the focused frontend checks and confirmed GREEN.

## Verification

All checks were run container-first:

- `docker build --target frontend -t garmin-dashboard-frontend .` — passed.
- `docker run --rm garmin-dashboard-frontend npm run typecheck` — passed.
- `docker run --rm garmin-dashboard-frontend npm test -- --run` — 1 test passed.
- `docker run --rm garmin-dashboard-frontend npm run build` — passed.
- Built image contains `dist/index.html` and hashed CSS/JS files under `dist/assets/`.
- `docker build -t garmin-dashboard-app .` — passed.
- Mounted backend suite: `147 passed in 2.49s`.
- `git diff --check` — passed before commit.

## Self-review

- All files required by the task brief are present.
- `main.tsx` owns rendering and imports both stylesheet files, leaving the `App` shell replaceable.
- No backend source files were changed.
- No credentials or environment values were printed.
- The generated host-side `frontend/node_modules` directory was removed after the first staging attempt; it is ignored and not committed.

## Concerns

The default application image build emits the existing Docker warning about `ENV GARMIN_TOKEN_DIR` being treated as sensitive. This is pre-existing backend configuration and was not changed for Task 1.

## Commits

- `160bd97 feat: scaffold React dashboard frontend`
