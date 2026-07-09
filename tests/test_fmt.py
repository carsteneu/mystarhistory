"""Tests for fmt() number formatting."""
import pytest

from mystarhistory import fmt


@pytest.mark.parametrize("n,expected", [
    (0, "0"),
    (1, "1"),
    (25, "25"),
    (999, "999"),
    (1000, "1K"),
    (1001, "1.001K"),   # :g preserves up to 4 sig digits
    (1500, "1.5K"),
    (2500, "2.5K"),
    (10000, "10K"),
    (12500, "12.5K"),
    (100000, "100K"),
])
def test_fmt(n, expected):
    assert fmt(n) == expected


def test_fmt_returns_string():
    assert isinstance(fmt(42), str)
    assert isinstance(fmt(42000), str)


def test_fmt_negative_thousands_not_in_spec():
    """fmt() isn't documented for negative inputs (stars can't be negative).
    Documenting current behavior so it's visible if someone changes it."""
    # Currently: n < 1000 hits the str() branch, so -500 -> "-500"
    assert fmt(-500) == "-500"
