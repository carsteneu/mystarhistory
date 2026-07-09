"""Tests for build_cumulative()."""
from mystarhistory import build_cumulative


def test_empty_input_returns_empty():
    assert build_cumulative([]) == []


def test_single_star():
    dates = ["2024-01-15T12:00:00Z"]
    assert build_cumulative(dates) == [("2024-01-15", 1)]


def test_multiple_stars_same_day_aggregate():
    dates = [
        "2024-01-15T08:00:00Z",
        "2024-01-15T18:00:00Z",
        "2024-01-15T23:59:59Z",
    ]
    assert build_cumulative(dates) == [("2024-01-15", 3)]


def test_cumulative_across_days():
    dates = [
        "2024-01-15T12:00:00Z",
        "2024-01-16T12:00:00Z",
        "2024-01-18T12:00:00Z",
    ]
    assert build_cumulative(dates) == [
        ("2024-01-15", 1),
        ("2024-01-16", 2),
        ("2024-01-18", 3),
    ]


def test_unsorted_input_gets_sorted():
    dates = [
        "2024-01-18T12:00:00Z",
        "2024-01-15T12:00:00Z",
        "2024-01-16T12:00:00Z",
    ]
    assert build_cumulative(dates) == [
        ("2024-01-15", 1),
        ("2024-01-16", 2),
        ("2024-01-18", 3),
    ]


def test_duplicate_timestamps_handled():
    dates = ["2024-01-15T12:00:00Z"] * 5
    assert build_cumulative(dates) == [("2024-01-15", 5)]
