import sqlite3
from datetime import date, datetime

from garmin_dashboard.domain.plan_models import Goal, PlanProposal, ValidatedPlan, Workout
from garmin_dashboard.ports.storage import StorageError

from ._common import SQLiteStore, date_text, timestamp_text


class SQLiteGoalStore(SQLiteStore):
    def save(self, goal: Goal) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO goals(goal_id, description, target_date) VALUES (?, ?, ?)
                ON CONFLICT(goal_id) DO UPDATE SET
                    description = excluded.description,
                    target_date = excluded.target_date
                """,
                (goal.goal_id, goal.description, date_text(goal.target_date)),
            )

    def current(self) -> Goal | None:
        try:
            with self.connection.locked():
                row = self.connection.execute("SELECT * FROM goals ORDER BY target_date ASC, goal_id ASC LIMIT 1").fetchone()
        except sqlite3.Error as error:
            raise StorageError("SQLite goal read failed") from error
        if row is None:
            return None
        return Goal(goal_id=row["goal_id"], description=row["description"], target_date=date.fromisoformat(row["target_date"]))


class SQLitePlanStore(SQLiteStore):
    def save(self, plan: ValidatedPlan) -> None:
        proposal = plan.proposal
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO plans(proposal_id, goal_id, week_start, explanation, created_at, validated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(proposal_id) DO UPDATE SET
                    goal_id = excluded.goal_id,
                    week_start = excluded.week_start,
                    explanation = excluded.explanation,
                    created_at = excluded.created_at,
                    validated_at = excluded.validated_at
                """,
                (
                    proposal.proposal_id,
                    proposal.goal_id,
                    date_text(proposal.week_start),
                    proposal.explanation,
                    timestamp_text(proposal.created_at),
                    timestamp_text(plan.validated_at),
                ),
            )
            self.connection.execute("DELETE FROM plan_workouts WHERE proposal_id = ?", (proposal.proposal_id,))
            self.connection.executemany(
                """
                INSERT INTO plan_workouts(
                    proposal_id, workout_id, scheduled_date, activity_type, duration_seconds,
                    intensity, purpose, explanation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(self._workout_values(proposal.proposal_id, workout) for workout in proposal.workouts),
            )

    def current(self) -> ValidatedPlan | None:
        try:
            with self.connection.locked():
                row = self.connection.execute(
                    "SELECT * FROM plans ORDER BY validated_at DESC, proposal_id DESC LIMIT 1"
                ).fetchone()
        except sqlite3.Error as error:
            raise StorageError("SQLite plan read failed") from error
        if row is None:
            return None
        try:
            with self.connection.locked():
                workouts = self.connection.execute(
                    "SELECT * FROM plan_workouts WHERE proposal_id = ? ORDER BY scheduled_date ASC, workout_id ASC",
                    (row["proposal_id"],),
                ).fetchall()
        except sqlite3.Error as error:
            raise StorageError("SQLite plan workout read failed") from error
        proposal = PlanProposal(
            proposal_id=row["proposal_id"],
            goal_id=row["goal_id"],
            week_start=date.fromisoformat(row["week_start"]),
            workouts=tuple(
                Workout(
                    workout_id=workout["workout_id"],
                    scheduled_date=date.fromisoformat(workout["scheduled_date"]),
                    activity_type=workout["activity_type"],
                    duration_seconds=workout["duration_seconds"],
                    intensity=workout["intensity"],
                    purpose=workout["purpose"],
                    explanation=workout["explanation"],
                )
                for workout in workouts
            ),
            explanation=row["explanation"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        return ValidatedPlan(proposal=proposal, validated_at=datetime.fromisoformat(row["validated_at"]))

    @staticmethod
    def _workout_values(proposal_id: str, workout: Workout) -> tuple[object, ...]:
        return (
            proposal_id,
            workout.workout_id,
            date_text(workout.scheduled_date),
            workout.activity_type,
            workout.duration_seconds,
            workout.intensity,
            workout.purpose,
            workout.explanation,
        )
