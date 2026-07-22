"""Tests for main() CLI wiring."""
import sys
from unittest.mock import patch

import pytest

import mystarhistory


def test_main_requires_repo_arg(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mystarhistory.py"])
    with pytest.raises(SystemExit) as excinfo:
        mystarhistory.main()
    # argparse exits with code 2 on usage error
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--repo" in err or "required" in err


def test_main_rejects_repo_without_slash(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mystarhistory.py", "--repo", "invalid"])
    with pytest.raises(SystemExit) as excinfo:
        mystarhistory.main()
    assert excinfo.value.code == 2
    assert "owner/name" in capsys.readouterr().err


def test_main_prepends_hash_to_color(monkeypatch, tmp_path):
    """Colors without leading # get it added automatically."""
    captured = {}

    def fake_generate(repo, dates, output, color, title, width, height, dark=False):
        captured["color"] = color

    monkeypatch.setattr(sys, "argv", [
        "mystarhistory.py",
        "--repo", "owner/name",
        "--color", "0066cc",
        "--output", str(tmp_path / "x.svg"),
    ])
    monkeypatch.setattr(mystarhistory, "fetch_stargazers", lambda r, **kw: ["2024-01-15T00:00:00Z"])
    monkeypatch.setattr(mystarhistory, "generate_svg", fake_generate)

    mystarhistory.main()
    assert captured["color"] == "#0066cc"


def test_main_passes_dark_flag(monkeypatch, tmp_path):
    captured = {}

    def fake_generate(repo, dates, output, color, title, width, height, dark=False):
        captured["dark"] = dark

    monkeypatch.setattr(sys, "argv", [
        "mystarhistory.py",
        "--repo", "owner/name",
        "--dark",
        "--output", str(tmp_path / "x.svg"),
    ])
    monkeypatch.setattr(mystarhistory, "fetch_stargazers", lambda r, **kw: ["2024-01-15T00:00:00Z"])
    monkeypatch.setattr(mystarhistory, "generate_svg", fake_generate)

    mystarhistory.main()
    assert captured["dark"] is True


def test_main_exits_on_empty_stargazers(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "mystarhistory.py",
        "--repo", "owner/name",
        "--output", "/tmp/whatever.svg",
    ])
    monkeypatch.setattr(mystarhistory, "fetch_stargazers", lambda r, **kw: [])

    with pytest.raises(SystemExit) as excinfo:
        mystarhistory.main()
    assert excinfo.value.code == 1
    assert "no stargazers" in capsys.readouterr().err
