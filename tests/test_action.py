"""Tests for the GitHub Action orchestrator (action.py)."""
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
        assert action.parse_inputs({"INPUT_COMMIT": true_val})["commit"] is True
    for false_val in ("false", "0", "no", ""):
        assert action.parse_inputs({"INPUT_COMMIT": false_val})["commit"] is False


# --- write_outputs ----------------------------------------------------------

def test_write_outputs_single_line_values(tmp_path, monkeypatch):
    out = tmp_path / "outputs.txt"
    monkeypatch.setattr(os, "environ", {**os.environ, "GITHUB_OUTPUT": str(out)})
    action.write_outputs(changed=True, files=[])
    content = out.read_text()
    assert "changed=true\n" in content


def test_write_outputs_multiline_files_use_heredoc(tmp_path, monkeypatch):
    out = tmp_path / "outputs.txt"
    monkeypatch.setattr(os, "environ", {**os.environ, "GITHUB_OUTPUT": str(out)})
    action.write_outputs(changed=True, files=["a/x.svg", "a/y.svg"])
    content = out.read_text()
    assert "files<<__" in content
    assert "__MyStarHistoryFiles__\n" in content
    assert "a/x.svg\n" in content
    assert "a/y.svg\n" in content
    assert "changed=true\n" in content


def test_write_outputs_no_files_skips_entry(tmp_path, monkeypatch):
    out = tmp_path / "outputs.txt"
    monkeypatch.setattr(os, "environ", {**os.environ, "GITHUB_OUTPUT": str(out)})
    action.write_outputs(changed=False, files=[])
    content = out.read_text()
    assert "changed=false\n" in content
    assert "files" not in content


def test_write_outputs_no_env_no_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "environ", {k: v for k, v in os.environ.items() if k != "GITHUB_OUTPUT"})
    action.write_outputs(True, ["x"])


# --- parse_bool edge cases --------------------------------------------------

def test_parse_bool_none_returns_default():
    assert action.parse_bool(None, default=True) is True
    assert action.parse_bool(None, default=False) is False
