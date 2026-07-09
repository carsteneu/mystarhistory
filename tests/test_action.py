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
    '<img alt="Star history" src="old.svg">\n'
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
    assert "old.svg" not in content
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
    assert "old.svg" in readme.read_text()


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


def test_update_readme_skips_marker_pairs_with_documentation_content(tmp_path):
    """Regression: markers shown in documentation (code samples, prose) must
    NOT be replaced by the action. The regex should only match marker pairs
    whose content is either empty/whitespace or a previously-written action
    block (<picture> or <img alt="Star history">).

    Documentation that quotes the markers must put some non-empty,
    non-action-block content between them so the regex skips the pair.
    Previously the lazy '.*?' matched the first start..end pair anywhere in
    the file, clobbering documentation that quoted the markers as examples.
    """
    content = (
        "# Project\n\n"
        "## Setup\n\n"
        "Add these markers:\n\n"
        "```html\n"
        "<!-- my-star-history:start -->\n"
        "<!-- your chart will appear here -->\n"
        "<!-- my-star-history:end -->\n"
        "```\n\n"
        "## Star History\n\n"
        "<!-- my-star-history:start -->\n"
        "<!-- my-star-history:end -->\n"
    )
    readme = tmp_path / "README.md"
    readme.write_text(content)
    block = "<picture>\n  <img alt=\"Star history\" src=\"a.svg\">\n</picture>"

    result = action.update_readme(readme, block)

    assert result is True
    new = readme.read_text()
    # The documentation comment inside the doc markers must survive
    assert "<!-- your chart will appear here -->" in new
    # The real block must be replaced
    assert "<picture>" in new
    assert 'src="a.svg"' in new


def test_update_readme_skips_doc_marker_pair_with_descriptive_text(tmp_path):
    """Same regression, different shape: markers quoted inline in prose.

    'The block between <!-- my-star-history:start --> and <!-- my-star-history:end -->'
    must not be replaced even though start and end markers appear in sequence.
    """
    content = (
        "# Project\n\n"
        "The block between <!-- my-star-history:start --> these words "
        "<!-- my-star-history:end --> is rewritten.\n\n"
        "## Star History\n\n"
        "<!-- my-star-history:start -->\n"
        "<!-- my-star-history:end -->\n"
    )
    readme = tmp_path / "README.md"
    readme.write_text(content)
    block = "<picture>\n  <img alt=\"Star history\" src=\"a.svg\">\n</picture>"

    result = action.update_readme(readme, block)
    assert result is True
    new = readme.read_text()
    # Prose between doc markers preserved
    assert "these words" in new
    # Real block replaced
    assert "<picture>" in new


def test_update_readme_replaces_existing_picture_block(tmp_path):
    """Idempotent re-run: an existing <picture> block between markers must
    be replaceable so the action can refresh the chart."""
    content = (
        "# Project\n\n"
        "<!-- my-star-history:start -->\n"
        "<picture>\n"
        "  <img alt=\"Star history\" src=\"old.svg\">\n"
        "</picture>\n"
        "<!-- my-star-history:end -->\n"
    )
    readme = tmp_path / "README.md"
    readme.write_text(content)
    block = "<picture>\n  <img alt=\"Star history\" src=\"new.svg\">\n</picture>"

    result = action.update_readme(readme, block)
    assert result is True
    new = readme.read_text()
    assert "new.svg" in new
    assert "old.svg" not in new


def test_update_readme_replaces_existing_img_block(tmp_path):
    """Same idempotency for plain <img alt="Star history"> blocks."""
    content = (
        "# Project\n\n"
        "<!-- my-star-history:start -->\n"
        '<img alt="Star history" src="old.svg">\n'
        "<!-- my-star-history:end -->\n"
    )
    readme = tmp_path / "README.md"
    readme.write_text(content)
    block = '<img alt="Star history" src="new.svg">'

    result = action.update_readme(readme, block)
    assert result is True
    new = readme.read_text()
    assert "new.svg" in new
    assert "old.svg" not in new


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


# --- write_outputs ----------------------------------------------------------

def test_write_outputs_single_line_values(tmp_path, monkeypatch):
    out = tmp_path / "outputs.txt"
    monkeypatch.setattr(os, "environ", {**os.environ, "GITHUB_OUTPUT": str(out)})

    action.write_outputs(changed=True, files=[], light=None, dark=None)

    content = out.read_text()
    assert "changed=true\n" in content


def test_write_outputs_multiline_files_use_heredoc(tmp_path, monkeypatch):
    """Regression test: $GITHUB_OUTPUT multiline values must use heredoc
    syntax. Plain 'files=foo\\nbar' fails because the second line is parsed
    as a new key=value pair and rejected."""
    out = tmp_path / "outputs.txt"
    monkeypatch.setattr(os, "environ", {**os.environ, "GITHUB_OUTPUT": str(out)})

    action.write_outputs(
        changed=True,
        files=["a/x.svg", "a/y.svg"],
        light="a/x.svg",
        dark="a/y.svg",
    )

    content = out.read_text()
    # Heredoc syntax for multiline value
    assert "files<<__" in content
    # Closing delimiter present
    assert "__MyStarHistoryFiles__\n" in content
    # Both file paths live inside the heredoc block
    assert "a/x.svg\n" in content
    assert "a/y.svg\n" in content
    # Single-line values stay plain
    assert "changed=true\n" in content
    assert "light=a/x.svg\n" in content
    assert "dark=a/y.svg\n" in content


def test_write_outputs_no_files_skips_entry(tmp_path, monkeypatch):
    out = tmp_path / "outputs.txt"
    monkeypatch.setattr(os, "environ", {**os.environ, "GITHUB_OUTPUT": str(out)})

    action.write_outputs(changed=False, files=[], light=None, dark=None)

    content = out.read_text()
    assert "changed=false\n" in content
    assert "files" not in content
    assert "light" not in content
    assert "dark" not in content


def test_write_outputs_no_env_no_crash(tmp_path, monkeypatch):
    """If GITHUB_OUTPUT is unset (local invocation), write_outputs is a no-op."""
    monkeypatch.setattr(os, "environ", {k: v for k, v in os.environ.items() if k != "GITHUB_OUTPUT"})
    action.write_outputs(True, ["x"], "x", None)  # must not raise

