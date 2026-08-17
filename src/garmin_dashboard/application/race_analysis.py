from collections.abc import Sequence
from datetime import timedelta

from garmin_dashboard.application.metrics import summarize_training
from garmin_dashboard.domain.models import Activity, TrainingBlock


def select_preceding_block(activities: Sequence[Activity], outcome: Activity, weeks: int) -> TrainingBlock:
    if weeks <= 0:
        raise ValueError("weeks must be positive")
    end = outcome.local_date
    start = end - timedelta(weeks=weeks)
    selected = tuple(
        sorted(
            (item for item in activities if start <= item.local_date < end),
            key=lambda item: (item.started_at, item.external_id),
        )
    )
    return TrainingBlock(
        start=start,
        end=end,
        outcome=outcome,
        activities=selected,
        summary=summarize_training(selected, start, end),
    )
