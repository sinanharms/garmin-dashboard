async function loadDashboard() {
  const response = await fetch("/api/dashboard");
  if (!response.ok) throw new Error("dashboard unavailable");
  const data = await response.json();
  document.querySelector("#health-status").textContent = `Health data: ${data.health_status}`;
  document.querySelector("#dashboard").textContent =
    `Fitness load: ${data.training.training_load ?? "unavailable"}; ` +
    `Goal: ${data.goal?.description ?? "none"}; ` +
    `Recent activities: ${data.recent_activities.length}`;
}

loadDashboard().catch(() => {
  document.querySelector("#health-status").textContent = "Dashboard unavailable";
});
