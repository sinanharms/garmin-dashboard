from datetime import UTC, datetime

import pytest


@pytest.fixture
def utc_now() -> datetime:
    return datetime(2026, 8, 16, 6, 30, tzinfo=UTC)
