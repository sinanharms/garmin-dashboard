import type { Goal } from "../../api/types";

type GoalCardProps = { goal: Goal | null };

export function GoalCard({ goal }: GoalCardProps) {
  return <section><h2>Goal</h2>{goal ? <><p>{goal.description}</p><p>Target date: {goal.target_date}</p></> : <p>No goal available</p>}</section>;
}
