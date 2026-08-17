# Story: Planning and coaching

## Summary

As the athlete, I need a goal and explicit constraints applied to any proposed weekly plan so that a plan can be reviewed, edited, accepted, skipped, or rejected without silently changing existing training intent.

## Status

Domain models, plan validation, SQLite plan storage, and an unavailable coach-provider boundary exist. A production AI coach and public planning API/UI are not currently wired.

## Context

- [Architecture overview](../architecture/overview.md)
- [Data model](../architecture/data-model.md)
- [Glossary](../domain/glossary.md)
- [Data-integrity convention](../conventions/data-integrity-and-failure.md)
- [Open questions](../decisions/open-questions.md)

## Acceptance Criteria

1. Goals contain an ID, description, and target date.
2. Constraints contain weekly time budget, available weekdays, activity preferences, and explicit requirements.
3. Proposals contain a goal, Monday week start, workouts, explanation, and creation time.
4. Validation rejects non-Monday week starts, workouts outside the proposal week, duplicate scheduled days, budget overruns, unavailable weekdays, preference violations, and unaddressed requirements.
5. Provider responses are validated into `PlanProposal` before plan validation.
6. Invalid proposals leave the previous plan unchanged and expose a clear validation reason.
7. Accepted or edited validated plans persist through `PlanStore`.
8. The coach provider remains replaceable behind `CoachProvider`; an unavailable provider fails explicitly.
9. No plan is mutated by synchronization without explicit user action.

## Testing Notes

Planning tests cover constraints, validation rules, provider response validation, accept/edit/skip behavior, and plan persistence. Current API tests verify safe plan rendering in the dashboard response but no planning write endpoint exists.
