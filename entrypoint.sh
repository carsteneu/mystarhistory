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
exec python3 /action/action.py
