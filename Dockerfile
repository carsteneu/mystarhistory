FROM python:3.12-slim

# gh CLI (script calls `gh api` to fetch stargazers) and git (for commits).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl ca-certificates git gnupg \
 && install -m 0755 -d /usr/share/keyrings \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends gh \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /action
COPY mystarhistory.py handlee-subset.woff2 action.py entrypoint.sh /action/
RUN chmod +x /action/entrypoint.sh

ENTRYPOINT ["/action/entrypoint.sh"]
