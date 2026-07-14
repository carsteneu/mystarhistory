#!/usr/bin/env bash
set -euo pipefail

# Since Jul 14 2026, the default GITHUB_TOKEN (github-actions[bot]) no longer
# has access to the stargazers endpoint. A fine-grained PAT with Stargazers:
# Read-only must be passed via the 'token' input (mapped to INPUT_TOKEN).
if [ -z "${INPUT_TOKEN:-}" ]; then
  echo "ERROR: 'token' input is required." >&2
  echo "Since Jul 14 2026, the default GITHUB_TOKEN can no longer read stargazers." >&2
  echo "Create a fine-grained PAT with 'Metadata: Read-only' on the target repo," >&2
  echo "store it as a repo secret (e.g. STAR_HISTORY_TOKEN), and set 'token:' in your workflow." >&2
  exit 1
fi

export GH_TOKEN="$INPUT_TOKEN"

cd "$GITHUB_WORKSPACE"
exec python3 /action/action.py
