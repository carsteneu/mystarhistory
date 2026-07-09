"""GitHub Action orchestrator for mystarhistory.

Renders star-history SVGs for one or more repos and commits them to the
repository. Does NOT modify the README — the user sets up the embed once
and the action just refreshes the image files.

Inputs (read from environment, per GitHub Actions convention):

    INPUT_REPOS            Comma-separated owner/repo list.
    INPUT_THEMES           Comma list, subset of {light,dark}. Default: light,dark
    INPUT_OUTPUT_DIR       Where SVGs are written. Default: assets/my-star-history
    INPUT_COMMIT           'true' to git-commit. Default: true
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


def parse_bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def parse_inputs(env):
    return {
        "repos": [r.strip() for r in env.get("INPUT_REPOS", "").split(",") if r.strip()],
        "themes": [t.strip() for t in env.get("INPUT_THEMES", "light,dark").split(",") if t.strip()],
        "output_dir": env.get("INPUT_OUTPUT_DIR", "assets/my-star-history"),
        "commit": parse_bool(env.get("INPUT_COMMIT"), True),
        "commit_message": env.get("INPUT_COMMIT_MESSAGE", "chore: update star history [skip ci]"),
        "color": env.get("INPUT_COLOR", "#dd4528"),
        "title": env.get("INPUT_TITLE", "Star History"),
    }


def git_commit(workspace, message):
    subprocess.run(["git", "add", "-A"], check=True, cwd=workspace)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=workspace)
    if diff.returncode == 0:
        return False
    subprocess.run(["git", "commit", "-m", message], check=True, cwd=workspace)
    subprocess.run(["git", "push"], check=True, cwd=workspace)
    return True


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
    out_dir = workspace / cfg["output_dir"]
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

    if cfg["commit"]:
        committed = git_commit(workspace, cfg["commit_message"])
        print("Committed and pushed" if committed else "No changes to commit")

    return 0


if __name__ == "__main__":
    sys.exit(main())
