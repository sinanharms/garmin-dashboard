export function formatDuration(seconds: number | null): string {
  if (seconds === null) return "Unavailable";

  const totalMinutes = Math.floor(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

export function formatDistance(meters: number | null): string {
  if (meters === null) return "Unavailable";
  const kilometers = Math.round((meters / 1000) * 10) / 10;
  return `${kilometers.toFixed(1)} km`;
}
