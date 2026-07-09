#!/usr/bin/env bash
set -euo pipefail

# GitHub Actions: `with:` inputs arrive as INPUT_* env vars.
# The checkout step persists GITHUB_TOKEN as git credentials, so plain
# `git push` works inside the workspace without extra auth.
export GH_TOKEN="${INPUT_TOKEN:-${GITHUB_TOKEN:-${GH_TOKEN:-}}}"

if [ -z "$GH_TOKEN" ]; then
  echo "ERROR: no token. Set 'token:' input or ensure GITHUB_TOKEN is available." >&2
  exit 1
fi

cd "$GITHUB_WORKSPACE"

# GitHub Actions checks out the workspace as the runner user; the Docker
# container runs as root, so git refuses to operate without this exception.
git config --global --add safe.directory "$GITHUB_WORKSPACE"

# Container has no git identity by default. Use the conventional
# github-actions[bot] identity so commits have a valid author.
git config --global user.email "github-actions[bot]@users.noreply.github.com"
git config --global user.name "github-actions[bot]"

exec python3 /action/action.py
