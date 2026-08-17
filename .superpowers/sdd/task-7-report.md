# Task 7 implementation report

Implemented editable training-plan validation and the replaceable coach boundary.

## Behaviors covered

- Immutable Pydantic plan constraints reject duplicate weekdays and blank constraint text.
- Provider proposals are revalidated with Pydantic, rejecting unknown workout fields, malformed dates, and negative durations.
- Plan validation rejects non-Monday starts, workouts outside the seven-day proposal window, duplicate scheduled days, unavailable weekdays, activity-preference violations, weekly time-budget violations, and unaddressed explicit requirements.
- `PlanningService` separates proposal/validation from persistence; accept and edit save only validated plans, while skip returns the current stored plan.
- Validation and provider failures leave the current plan untouched; no fallback proposal is generated.
- Health summaries are passed unchanged through `CoachContext`; planning creates no medical-advice field or recommendation.
- `UnavailableCoachProvider` raises an explicit `CoachProviderUnavailable` boundary until a concrete provider is selected.

## TDD and verification

- Red: `uv run pytest tests/test_planning.py -q` failed during collection because `application.planning` did not exist.
- Green: `uv run pytest tests/test_planning.py -q` — 10 passed.
- Full suite: `uv run pytest -q` — 119 passed.
- Ruff check — passed.
- Ruff format check — 43 files already formatted.
- `uv run ty check .` — passed.
- `docker compose config --quiet` — passed.

All runtime source files remain below 300 lines. No provider SDK or fallback plan was added.
