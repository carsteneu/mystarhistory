"""Tests for smooth_path()."""
from mystarhistory import smooth_path


def test_empty_returns_empty_string():
    assert smooth_path([]) == ""


def test_single_point_returns_bare_moveto():
    """A single data point (all stars on one day) must still yield a valid
    path: bare M command, no dangling L that would malform the area path."""
    assert smooth_path([(10, 20)]) == "M 10.0,20.0"


def test_two_points_starts_with_move_to():
    path = smooth_path([(0, 0), (100, 100)])
    assert path.startswith("M 0.0,0.0")


def test_two_points_is_linear():
    """Sparse data (≤3 points) uses straight lines, not synthesized curves."""
    path = smooth_path([(0, 0), (100, 100)])
    assert path.count("C ") == 0
    assert path.count("L ") == 1


def test_three_points_is_linear():
    path = smooth_path([(0, 0), (50, 25), (100, 0)])
    assert path.count("C ") == 0
    assert path.count("L ") == 2


def test_output_format_is_consistent():
    """Path uses 1-decimal precision. Each cubic segment has 3 coord pairs:
    "cp1x,cp1y cp2x,cp2y endx,endy". Uses 4 points so smoothing kicks in."""
    path = smooth_path([(10, 20), (30, 40), (50, 60), (70, 80)])
    assert "M 10.0,20.0" in path
    for segment in path.split(" C ")[1:]:
        pairs = segment.split(" ")
        assert len(pairs) == 3
        for pair in pairs:
            assert "," in pair
            x_str, y_str = pair.split(",")
            float(x_str)
            float(y_str)
