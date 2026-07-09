#!/usr/bin/env bash
set -euo pipefail

export GH_TOKEN="${INPUT_TOKEN:-${GITHUB_TOKEN:-${GH_TOKEN:-}}}"

if [ -z "$GH_TOKEN" ]; then
  echo "ERROR: no token. Set 'token:' input or ensure GITHUB_TOKEN is available." >&2
  exit 1
fi

cd "$GITHUB_WORKSPACE"
exec python3 /action/action.py
