"""Snapshot (golden-file) tests for generate_svg().

If these tests fail, the SVG output has changed. Re-generate the golden
files deliberately and commit them:

    .venv/bin/python tests/regenerate_golden.py
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mystarhistory import generate_svg

GOLDEN_DIR = Path(__file__).parent / "golden"


def _golden_path(name):
    return GOLDEN_DIR / name


def _render(tmp_path, fixture_dates, fixture_repo, **overrides):
    out = tmp_path / "out.svg"
    kwargs = {
        "repo": fixture_repo,
        "dates": fixture_dates,
        "output": str(out),
        "color": "#dd4528",
        "title": "Star History",
    }
    kwargs.update(overrides)
    generate_svg(**kwargs)
    return out.read_text()


def _assert_xml_valid(svg_text):
    ET.fromstring(svg_text)


def test_light_matches_golden(tmp_path, fixture_dates, fixture_repo):
    svg = _render(tmp_path, fixture_dates, fixture_repo)
    _assert_xml_valid(svg)
    golden = _golden_path("star-history-light.svg").read_text()
    assert svg == golden, (
        "Generated SVG differs from golden. If this is intentional, "
        "regenerate via: python tests/regenerate_golden.py"
    )


def test_dark_matches_golden(tmp_path, fixture_dates, fixture_repo):
    svg = _render(tmp_path, fixture_dates, fixture_repo, dark=True)
    _assert_xml_valid(svg)
    golden = _golden_path("star-history-dark.svg").read_text()
    assert svg == golden, (
        "Generated dark SVG differs from golden. If this is intentional, "
        "regenerate via: python tests/regenerate_golden.py"
    )


def test_dark_uses_dark_palette(tmp_path, fixture_dates, fixture_repo):
    svg = _render(tmp_path, fixture_dates, fixture_repo, dark=True)
    assert "#0d1117" in svg          # background
    assert "#e6edf3" in svg          # foreground text
    assert "#30363d" in svg          # axis


def test_light_uses_light_palette(tmp_path, fixture_dates, fixture_repo):
    svg = _render(tmp_path, fixture_dates, fixture_repo, dark=False)
    assert 'fill="#fff"' in svg
    assert "#0d1117" not in svg


def test_custom_color_appears_in_output(tmp_path, fixture_dates, fixture_repo):
    svg = _render(tmp_path, fixture_dates, fixture_repo, color="#abcdef")
    assert "#abcdef" in svg


def test_custom_dimensions_appear_in_viewbox(tmp_path, fixture_dates, fixture_repo):
    svg = _render(tmp_path, fixture_dates, fixture_repo, width=1200, height=700)
    assert 'viewBox="0 0 1200 700"' in svg


def test_custom_title_appears(tmp_path, fixture_dates, fixture_repo):
    svg = _render(tmp_path, fixture_dates, fixture_repo, title="My Project")
    assert ">My Project</text>" in svg


def test_empty_dates_exits(tmp_path, capsys):
    with pytest.raises(SystemExit) as excinfo:
        generate_svg(
            repo="test/repo",
            dates=[],
            output=str(tmp_path / "x.svg"),
            color="#dd4528",
            title="x",
        )
    assert excinfo.value.code == 1
    assert "no stars found" in capsys.readouterr().err


def test_renders_repo_name_in_legend(tmp_path, fixture_dates, fixture_repo):
    svg = _render(tmp_path, fixture_dates, fixture_repo)
    assert f">{fixture_repo}</text>" in svg


def test_github_stars_label_is_not_clipped_on_left(tmp_path, fixture_dates, fixture_repo):
    """Regression test for the Y-axis label clipping bug.

    The rotated 'GitHub Stars' label must have its rotation center far enough
    from the left viewBox edge that the font ascender/descender doesn't go
    below x=0. Empirically: rotation center at x=43 with font-size 17 keeps
    the whole glyph within viewBox."""
    svg = _render(tmp_path, fixture_dates, fixture_repo)
    # Rotation center for the label must be >= 30 (empirically safe)
    assert 'rotate(-90, 3' in svg or 'rotate(-90, 4' in svg or 'rotate(-90, 5' in svg
    # Specifically, the current safe value is x=43
    assert 'rotate(-90, 43,' in svg


def test_output_file_is_written(tmp_path, fixture_dates, fixture_repo):
    out = tmp_path / "out.svg"
    generate_svg(
        repo=fixture_repo,
        dates=fixture_dates,
        output=str(out),
        color="#dd4528",
        title="x",
    )
    assert out.exists()
    assert out.stat().st_size > 1000  # font base64 alone is several KB


def test_generated_svg_has_embedded_font(tmp_path, fixture_dates, fixture_repo):
    svg = _render(tmp_path, fixture_dates, fixture_repo)
    assert "@font-face" in svg
    assert "data:font/woff2;charset=utf-8;base64," in svg
    assert "Handlee" in svg
