function renderPlan(plan) {
  const target = document.querySelector("#weekly-plan-content");
  const proposal = plan?.proposal;
  const workouts = proposal?.workouts ?? [];
  if (!proposal || workouts.length === 0) {
    target.textContent = "Weekly plan unavailable";
    return;
  }
  const workoutText = workouts.map((workout) =>
    `${workout.scheduled_date}: ${workout.activity_type}, ` +
    `${workout.duration_seconds}s, ${workout.intensity} — ${workout.purpose}`
  ).join("; ");
  target.textContent = `Week of ${proposal.week_start}: ${workoutText}`;
}

function renderHealth(data) {
  const health = data.health;
  const status = data.health_status === "available" && health.available ? "available" : "missing";
  document.querySelector("#health-status").textContent = `Health data: ${status}`;
  document.querySelector("#sleep-detail").textContent = health.average_sleep_seconds == null
    ? "Sleep: unavailable"
    : `Sleep: ${Math.round(health.average_sleep_seconds / 60)} minutes; ` +
      `score: ${health.average_sleep_score ?? "unavailable"}`;
  document.querySelector("#recovery-detail").textContent = health.recovery_metrics.length === 0
    ? "Recovery: unavailable"
    : `Recovery: ${health.recovery_metrics.map(([name, value, unit]) => `${name}: ${value} ${unit}`).join(", ")}`;
}

async function loadDashboard() {
  const response = await fetch("/api/dashboard");
  if (!response.ok) throw new Error("dashboard unavailable");
  const data = await response.json();
  renderHealth(data);
  document.querySelector("#fitness-summary").textContent =
    `Fitness load: ${data.training.training_load ?? "unavailable"}; ` +
    `Activity count: ${data.training.activity_count}`;
  document.querySelector("#goal-summary").textContent = `Goal: ${data.goal?.description ?? "none"}`;
  renderPlan(data.plan);
  document.querySelector("#recent-activities").textContent =
    `Recent activities: ${data.recent_activities.length}`;
}

loadDashboard().catch(() => {
  document.querySelector("#health-status").textContent = "Dashboard unavailable";
});
