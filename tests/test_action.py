"""Tests for the GitHub Action orchestrator (action.py).

These cover the testable pure helpers: input parsing, timestamp filename
construction, README marker replacement, old-file cleanup, and picture-block
rendering. The end-to-end main() (which shells out to `gh` and `git`) is
not unit-tested here; it is exercised via the Docker build + a manual
workflow run in a test repo.
"""
import os
from pathlib import Path

import pytest

import action


# --- parse_inputs -----------------------------------------------------------

def test_parse_inputs_defaults():
    cfg = action.parse_inputs({})
    assert cfg["repos"] == []
    assert cfg["themes"] == ["light", "dark"]
    assert cfg["output_dir"] == "assets/my-star-history"
    assert cfg["readme"] == "README.md"
    assert cfg["update_readme"] is True
    assert cfg["commit"] is True
    assert cfg["commit_message"] == "chore: update star history [skip ci]"
    assert cfg["color"] == "#dd4528"
    assert cfg["title"] == "Star History"


def test_parse_inputs_repos_split():
    cfg = action.parse_inputs({"INPUT_REPOS": "a/b, c/d ,e/f"})
    assert cfg["repos"] == ["a/b", "c/d", "e/f"]


def test_parse_inputs_themes_subset():
    cfg = action.parse_inputs({"INPUT_THEMES": "dark"})
    assert cfg["themes"] == ["dark"]


def test_parse_inputs_bool_variants():
    for true_val in ("true", "True", "1", "yes", "on"):
        assert action.parse_inputs({"INPUT_UPDATE_README": true_val})["update_readme"] is True
    for false_val in ("false", "0", "no", ""):
        assert action.parse_inputs({"INPUT_UPDATE_README": false_val})["update_readme"] is False


# --- timestamp_filename -----------------------------------------------------

def test_timestamp_filename_format():
    name = action.timestamp_filename("light", "20260709143000")
    assert name == "star-history-light-20260709143000.svg"


def test_timestamp_filename_dark():
    name = action.timestamp_filename("dark", "20260709143000")
    assert name == "star-history-dark-20260709143000.svg"


# --- build_picture_block ----------------------------------------------------

def test_picture_block_both_themes():
    block = action.build_picture_block("assets/x", "a.svg", "b.svg")
    assert "<picture>" in block
    assert "</picture>" in block
    assert 'src="assets/x/a.svg"' in block
    assert 'srcset="assets/x/b.svg"' in block
    assert "prefers-color-scheme: dark" in block


def test_picture_block_light_only():
    block = action.build_picture_block("assets/x", "a.svg", None)
    assert "<picture>" not in block
    assert '<img alt="Star history" src="assets/x/a.svg">' in block


def test_picture_block_dark_only():
    block = action.build_picture_block("assets/x", None, "b.svg")
    assert "<picture>" not in block
    assert 'src="assets/x/b.svg"' in block


def test_picture_block_neither_returns_empty():
    assert action.build_picture_block("assets/x", None, None) == ""


# --- update_readme ----------------------------------------------------------

README_TEMPLATE = (
    "# Project\n\n"
    "Some intro.\n\n"
    "<!-- my-star-history:start -->\n"
    "old content\n"
    "<!-- my-star-history:end -->\n\n"
    "Trailing.\n"
)


def test_update_readme_replaces_block(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README_TEMPLATE)
    block = "<img alt=\"Star history\" src=\"assets/x/a.svg\">"

    result = action.update_readme(readme, block)

    assert result is True
    content = readme.read_text()
    assert "<!-- my-star-history:start -->" in content
    assert "<!-- my-star-history:end -->" in content
    assert "old content" not in content
    assert block in content
    # Markers preserved, content between them replaced
    assert "<!-- my-star-history:start -->\n" + block + "\n<!-- my-star-history:end -->" in content


def test_update_readme_returns_false_when_markers_missing(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n\nNo markers here.\n")

    result = action.update_readme(readme, "<img src='x'>")

    assert result is False
    # File unchanged
    assert readme.read_text() == "# Project\n\nNo markers here.\n"


def test_update_readme_returns_false_when_file_missing(tmp_path):
    result = action.update_readme(tmp_path / "nope.md", "<img src='x'>")
    assert result is False


def test_update_readme_empty_block_no_op(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README_TEMPLATE)
    result = action.update_readme(readme, "")
    assert result is False
    assert "old content" in readme.read_text()


def test_update_readme_multiline_block(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(README_TEMPLATE)
    block = (
        "<picture>\n"
        "  <source media=\"(prefers-color-scheme: dark)\" srcset=\"a/d.svg\">\n"
        "  <img alt=\"Star history\" src=\"a/l.svg\">\n"
        "</picture>"
    )
    result = action.update_readme(readme, block)
    assert result is True
    content = readme.read_text()
    assert "<picture>" in content
    assert "</picture>" in content


def test_update_readme_handles_empty_marker_block(tmp_path):
    """Initial state: markers present but nothing between them yet."""
    content = "# Project\n\n<!-- my-star-history:start -->\n<!-- my-star-history:end -->\n"
    readme = tmp_path / "README.md"
    readme.write_text(content)
    block = "<img src='a.svg'>"
    result = action.update_readme(readme, block)
    assert result is True
    new = readme.read_text()
    assert block in new


# --- clean_old_files --------------------------------------------------------

def test_clean_old_files_keeps_newest_per_theme(tmp_path):
    (tmp_path / "star-history-light-20260101000000.svg").write_text("old")
    (tmp_path / "star-history-light-20260201000000.svg").write_text("mid")
    newest = tmp_path / "star-history-light-20260301000000.svg"
    newest.write_text("new")

    removed = action.clean_old_files(tmp_path, ["light"])

    assert len(removed) == 2
    assert newest.exists()
    assert not (tmp_path / "star-history-light-20260101000000.svg").exists()
    assert not (tmp_path / "star-history-light-20260201000000.svg").exists()


def test_clean_old_files_both_themes(tmp_path):
    for theme in ("light", "dark"):
        (tmp_path / f"star-history-{theme}-20260101000000.svg").write_text("old")
        (tmp_path / f"star-history-{theme}-20260201000000.svg").write_text("new")

    removed = action.clean_old_files(tmp_path, ["light", "dark"])

    assert len(removed) == 2
    for theme in ("light", "dark"):
        assert (tmp_path / f"star-history-{theme}-20260201000000.svg").exists()
        assert not (tmp_path / f"star-history-{theme}-20260101000000.svg").exists()


def test_clean_old_files_single_file_no_op(tmp_path):
    f = tmp_path / "star-history-light-20260101000000.svg"
    f.write_text("x")
    removed = action.clean_old_files(tmp_path, ["light"])
    assert removed == []
    assert f.exists()


def test_clean_old_files_no_files(tmp_path):
    removed = action.clean_old_files(tmp_path, ["light", "dark"])
    assert removed == []


def test_clean_old_files_keep_filename_overrides_sort(tmp_path):
    """Same-second rerun: explicit keep_filename wins over sort order."""
    (tmp_path / "star-history-light-00000000000001.svg").write_text("older")
    (tmp_path / "star-history-light-00000000000002.svg").write_text("newer")
    keep = "star-history-light-00000000000001.svg"
    removed = action.clean_old_files(tmp_path, ["light"], keep_filename=keep)
    assert (tmp_path / keep).exists()
    assert len(removed) == 1


def test_clean_old_files_only_matches_theme_prefix(tmp_path):
    """Non-timestamped SVGs (e.g. legacy star-history.svg) are left alone."""
    (tmp_path / "star-history.svg").write_text("legacy")
    (tmp_path / "star-history-light-20260101000000.svg").write_text("ts")
    action.clean_old_files(tmp_path, ["light"])
    assert (tmp_path / "star-history.svg").exists()


# --- parse_bool edge cases --------------------------------------------------

def test_parse_bool_none_returns_default():
    assert action.parse_bool(None, default=True) is True
    assert action.parse_bool(None, default=False) is False
