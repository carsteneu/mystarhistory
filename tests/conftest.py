"""Shared pytest fixtures for mystarhistory tests."""
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def fixture_dates():
    """Deterministic set of star timestamps for snapshot tests.

    Spans ~5 months with multiple stars on some days so cumulative
    building and date-axis rendering have something meaningful to do.
    """
    base = datetime(2024, 1, 15, 12, 0, 0)
    offsets = [
        0, 0, 1, 5, 12, 13, 13, 28, 45, 46, 60, 75, 90, 91, 92,
        105, 120, 134, 135, 150,
    ]
    return sorted(
        (base + timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for d in offsets
    )


@pytest.fixture
def fixture_repo():
    """Repo slug used in snapshot tests."""
    return "test/example-repo"
