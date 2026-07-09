"""Tests for fetch_stargazers() with subprocess.run mocked."""
from unittest.mock import patch

import pytest

from mystarhistory import fetch_stargazers


class _FakeCompleted:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_parses_sorted_timestamps(monkeypatch):
    fake_stdout = "2024-02-01T00:00:00Z\n2024-01-15T00:00:00Z\n2024-03-01T00:00:00Z\n"
    fake = _FakeCompleted(stdout=fake_stdout)
    monkeypatch.setattr("mystarhistory.subprocess.run", lambda *a, **kw: fake)

    result = fetch_stargazers("test/repo")
    assert result == [
        "2024-01-15T00:00:00Z",
        "2024-02-01T00:00:00Z",
        "2024-03-01T00:00:00Z",
    ]


def test_strips_empty_lines(monkeypatch):
    fake_stdout = "\n2024-01-15T00:00:00Z\n\n\n2024-01-16T00:00:00Z\n"
    fake = _FakeCompleted(stdout=fake_stdout)
    monkeypatch.setattr("mystarhistory.subprocess.run", lambda *a, **kw: fake)

    result = fetch_stargazers("test/repo")
    assert result == ["2024-01-15T00:00:00Z", "2024-01-16T00:00:00Z"]


def test_empty_output_returns_empty_list(monkeypatch):
    fake = _FakeCompleted(stdout="")
    monkeypatch.setattr("mystarhistory.subprocess.run", lambda *a, **kw: fake)
    assert fetch_stargazers("test/repo") == []


def test_failed_gh_command_exits(monkeypatch, capsys):
    fake = _FakeCompleted(stderr="HTTP 401: bad credentials", returncode=1)
    monkeypatch.setattr("mystarhistory.subprocess.run", lambda *a, **kw: fake)

    with pytest.raises(SystemExit) as excinfo:
        fetch_stargazers("test/repo")
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "gh command failed" in err
    assert "HTTP 401" in err


def test_uses_correct_api_endpoint(monkeypatch):
    """Verify the gh CLI is invoked with the stargazers endpoint and the
    star+json Accept header that returns starred_at timestamps."""
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeCompleted(stdout="2024-01-15T00:00:00Z\n")

    monkeypatch.setattr("mystarhistory.subprocess.run", fake_run)
    fetch_stargazers("owner/name")

    assert captured["args"][0] == "gh"
    assert captured["args"][1] == "api"
    assert "/repos/owner/name/stargazers" in captured["args"]
    assert "--paginate" in captured["args"]
    assert "Accept: application/vnd.github.v3.star+json" in captured["args"]
