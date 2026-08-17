import type { ValidatedPlan } from "../../api/types";
import { formatDuration } from "../../components/formatters";

type PlanCardProps = { plan: ValidatedPlan | null };

export function PlanCard({ plan }: PlanCardProps) {
  if (plan === null) return <section><h2>Weekly plan</h2><p>Weekly plan unavailable</p></section>;
  return <section><h2>Weekly plan</h2><ul>{plan.proposal.workouts.map((workout) => <li key={workout.workout_id}>{workout.scheduled_date} · {workout.activity_type} · {formatDuration(workout.duration_seconds)} · {workout.intensity} · {workout.purpose}</li>)}</ul></section>;
}
