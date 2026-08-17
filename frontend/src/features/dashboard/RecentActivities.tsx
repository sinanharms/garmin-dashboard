import type { Activity } from "../../api/types";
import { formatDistance, formatDuration } from "../../components/formatters";

type RecentActivitiesProps = { activities: readonly Activity[] };

export function RecentActivities({ activities }: RecentActivitiesProps) {
  return <section><h2>Recent activities</h2>{activities.length === 0 ? <p>No recent activities</p> : <ul>{activities.map((activity) => <li key={activity.external_id}>{activity.activity_type} · {activity.local_date} · {formatDuration(activity.duration_seconds)} · {formatDistance(activity.distance_meters)}{activity.elevation_meters === null ? "" : ` · ${activity.elevation_meters} m elevation`}</li>)}</ul>}</section>;
}
