"""GitHub Action orchestrator for mystarhistory.

Renders star-history SVGs for one or more repos and pushes them to a
dedicated orphan branch (default: star-history). This avoids polluting
the main branch with chart updates and works with branch protection.

Inputs (read from environment, per GitHub Actions convention):

    INPUT_REPOS            Comma-separated owner/repo list.
    INPUT_THEMES           Comma list, subset of {light,dark}. Default: light,dark
    INPUT_OUTPUT_DIR       Where SVGs are written. Default: assets/my-star-history
    INPUT_BRANCH           Branch to push to. Default: star-history
    INPUT_COMMIT_MESSAGE   Default: 'chore: update star history [skip ci]'
    INPUT_COLOR            Chart line color. Default: #dd4528
    INPUT_TITLE            Chart title. Default: 'Star History'

Outputs (written to GITHUB_OUTPUT):

    changed    'true' if any SVG was (re)generated
    files      newline-separated paths of the new SVGs
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mystarhistory import fetch_stargazers, generate_svg


def parse_inputs(env):
    return {
        "repos": [r.strip() for r in env.get("INPUT_REPOS", "").split(",") if r.strip()],
        "themes": [t.strip() for t in env.get("INPUT_THEMES", "light,dark").split(",") if t.strip()],
        "output_dir": env.get("INPUT_OUTPUT_DIR", "assets/my-star-history"),
        "branch": env.get("INPUT_BRANCH", "star-history"),
        "commit_message": env.get("INPUT_COMMIT_MESSAGE", "chore: update star history [skip ci]"),
        "color": env.get("INPUT_COLOR", "#dd4528"),
        "title": env.get("INPUT_TITLE", "Star History"),
    }


def prepare_orphan_branch(workspace, branch, github_token):
    """Create or switch to an orphan branch containing only chart files.

    Works in a temporary directory to avoid any risk to the main workspace.
    The SVGs are written there, committed, and pushed. The main checkout
    is never modified."""
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="star-history-"))
    subprocess.run(["git", "init", "-b", branch, str(tmp)], check=True)

    if not github_token:
        raise RuntimeError("No token available for git push")

    repo_url = os.environ.get("GITHUB_REPOSITORY", "")
    if repo_url:
        authed_url = f"https://x-access-token:{github_token}@github.com/{repo_url}"
    else:
        remote_url = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, cwd=workspace,
        ).stdout.strip()
        authed_url = remote_url.replace(
            "https://github.com/",
            f"https://x-access-token:{github_token}@github.com/",
        )

    subprocess.run(["git", "remote", "add", "origin", authed_url],
                   check=True, cwd=tmp)

    # Check if branch exists remotely by trying to fetch it.
    # ls-remote can return non-empty output even when the ref is not
    # fetchable (e.g. stale caches, tag/branch name collisions), so
    # we use fetch itself as the source of truth.
    fetch = subprocess.run(
        ["git", "fetch", "origin", branch],
        capture_output=True, text=True, cwd=tmp,
    )
    if fetch.returncode == 0:
        subprocess.run(["git", "checkout", branch], check=True, cwd=tmp)

    subprocess.run(["git", "config", "user.email",
                    "github-actions[bot]@users.noreply.github.com"], cwd=tmp)
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=tmp)

    return tmp


def write_outputs(changed, files):
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a") as f:
        f.write(f"changed={'true' if changed else 'false'}\n")
        if files:
            delimiter = "__MyStarHistoryFiles__"
            f.write(f"files<<{delimiter}\n")
            for fp in files:
                f.write(f"{fp}\n")
            f.write(f"{delimiter}\n")


def main():
    cfg = parse_inputs(os.environ)
    if not cfg["repos"]:
        print("No repos specified (INPUT_REPOS is empty)", file=sys.stderr)
        return 1

    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))
    github_token = os.environ.get("INPUT_TOKEN", "")

    git_config = [
        ["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"],
        ["git", "config", "--global", "user.name", "github-actions[bot]"],
    ]
    for cmd in git_config:
        subprocess.run(cmd, check=True)

    branch_dir = prepare_orphan_branch(workspace, cfg["branch"], github_token)

    out_dir = branch_dir / cfg["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    generated = []

    for repo in cfg["repos"]:
        dates = fetch_stargazers(repo)
        if not dates:
            print(f"No stargazers for {repo}, skipping", file=sys.stderr)
            continue
        for theme in cfg["themes"]:
            dark = theme == "dark"
            fname = f"star-history-{theme}.svg"
            generate_svg(repo, dates, str(out_dir / fname), cfg["color"], cfg["title"], dark=dark)
            generated.append(f"{cfg['output_dir']}/{fname}")
            print(f"Generated {cfg['output_dir']}/{fname}")

    if not generated:
        print("Nothing generated for any repo", file=sys.stderr)
        write_outputs(False, [])
        return 1

    write_outputs(True, generated)

    subprocess.run(["git", "add", "-A"], check=True, cwd=branch_dir)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=branch_dir)
    if diff.returncode != 0:
        subprocess.run(["git", "commit", "-m", cfg["commit_message"]],
                       check=True, cwd=branch_dir)
        subprocess.run(["git", "push", "-u", "origin", cfg["branch"]],
                       check=True, cwd=branch_dir)
        print(f"Pushed to {cfg['branch']}")
    else:
        print("No changes to commit")

    return 0


if __name__ == "__main__":
    sys.exit(main())
