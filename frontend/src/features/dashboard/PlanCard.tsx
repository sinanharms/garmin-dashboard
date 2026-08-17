import type { ValidatedPlan } from "../../api/types";
import { formatDuration } from "../../components/formatters";
import styles from "./PlanCard.module.css";

type PlanCardProps = { plan: ValidatedPlan | null };

export function PlanCard({ plan }: PlanCardProps) {
  if (plan === null) return <section className={styles.card}><h2>Weekly plan</h2><p>Weekly plan unavailable</p></section>;
  return <section className={styles.card}>
    <h2>Weekly plan</h2>
    <p className={styles.week}>Week of {plan.proposal.week_start}</p>
    {plan.proposal.explanation && <p>{plan.proposal.explanation}</p>}
    <ul>{plan.proposal.workouts.map((workout) => <li key={workout.workout_id}>
      <span>{workout.scheduled_date} · {workout.activity_type} · {formatDuration(workout.duration_seconds)} · {workout.intensity} · {workout.purpose}</span>
      {workout.explanation && <span className={styles.explanation}>{workout.explanation}</span>}
    </li>)}</ul>
  </section>;
}
