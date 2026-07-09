"""GitHub Action orchestrator for mystarhistory.

Renders star-history SVGs for one or more repos, writes them with
cache-busting timestamp filenames, replaces the block between marker
comments in the README, removes superseded timestamped files, and
commits the result.

Inputs (read from environment, per GitHub Actions convention):

    INPUT_REPOS            Comma-separated owner/repo list.
    INPUT_THEMES           Comma list, subset of {light,dark}. Default: light,dark
    INPUT_OUTPUT_DIR       Where SVGs are written. Default: assets/my-star-history
    INPUT_README           README path. Default: README.md
    INPUT_UPDATE_README    'true' to rewrite between markers. Default: true
    INPUT_COMMIT           'true' to git-commit. Default: true
    INPUT_COMMIT_MESSAGE   Default: 'chore: update star history [skip ci]'
    INPUT_COLOR            Chart line color. Default: #dd4528
    INPUT_TITLE            Chart title. Default: 'Star History'

Outputs (written to GITHUB_OUTPUT):

    changed    'true' if any SVG was (re)generated
    files      newline-separated paths of the new SVGs
    light      path of the newest light SVG (or empty)
    dark       path of the newest dark SVG (or empty)

Marker convention in the README:

    <!-- my-star-history:start -->
    ... (action fills this in) ...
    <!-- my-star-history:end -->
"""
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from glob import glob
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mystarhistory import fetch_stargazers, generate_svg

MARKER = "my-star-history"


def parse_bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def parse_inputs(env):
    """Read action inputs from env vars, with defaults."""
    return {
        "repos": [r.strip() for r in env.get("INPUT_REPOS", "").split(",") if r.strip()],
        "themes": [t.strip() for t in env.get("INPUT_THEMES", "light,dark").split(",") if t.strip()],
        "output_dir": env.get("INPUT_OUTPUT_DIR", f"assets/{MARKER}"),
        "readme": env.get("INPUT_README", "README.md"),
        "update_readme": parse_bool(env.get("INPUT_UPDATE_README"), True),
        "commit": parse_bool(env.get("INPUT_COMMIT"), True),
        "commit_message": env.get("INPUT_COMMIT_MESSAGE", "chore: update star history [skip ci]"),
        "color": env.get("INPUT_COLOR", "#dd4528"),
        "title": env.get("INPUT_TITLE", "Star History"),
    }


def timestamp_filename(theme, ts):
    """Build a cache-busting filename: star-history-{theme}-{YYYYmmddHHMMSS}.svg."""
    return f"star-history-{theme}-{ts}.svg"


def clean_old_files(out_dir, themes, keep_filename=None):
    """Delete timestamped SVGs in out_dir per theme, keeping only the newest.

    If keep_filename is given, ensure that specific file is preserved even if
    its sort position would otherwise drop it (e.g. same-second rerun)."""
    removed = []
    for theme in themes:
        pattern = str(Path(out_dir) / f"star-history-{theme}-*.svg")
        files = sorted(glob(pattern))
        if len(files) <= 1:
            continue
        # Keep the last (newest by timestamp sort)
        newest = files[-1]
        if keep_filename:
            candidate = str(Path(out_dir) / keep_filename)
            if candidate in files:
                newest = candidate
        for old in files:
            if old != newest:
                Path(old).unlink()
                removed.append(Path(old).name)
    return removed


def build_picture_block(output_dir, light_file, dark_file):
    """Render the HTML block to embed between the README markers.

    Uses <picture> when both themes are present, otherwise a plain <img>.
    A small attribution line is appended below the chart.
    """
    rel = output_dir
    attribution = (
        f'<sub><a href="https://github.com/carsteneu/mystarhistory">made with mystarhistory</a></sub>'
    )
    if light_file and dark_file:
        return (
            "<picture>\n"
            f'  <source media="(prefers-color-scheme: dark)" srcset="{rel}/{dark_file}">\n'
            f'  <img alt="Star history" src="{rel}/{light_file}">\n'
            f"</picture>\n"
            f"{attribution}"
        )
    single = light_file or dark_file
    if not single:
        return ""
    return f'<img alt="Star history" src="{rel}/{single}">\n{attribution}'


def update_readme(readme_path, block, marker=MARKER):
    """Replace content between marker comments. Returns True if updated.

    Only matches marker pairs whose current content is either empty
    (whitespace only) or an existing action-written block (<picture> or
    <img alt="Star history">). This prevents the action from clobbering
    documentation that quotes the markers as examples — doc authors must
    put some other content between the markers so the regex skips them.
    """
    if not block:
        return False
    if not readme_path.exists():
        return False
    content = readme_path.read_text()
    start = f"<!-- {marker}:start -->"
    end = f"<!-- {marker}:end -->"
    # Inner content must be either whitespace-only OR an existing action block
    # (<picture>...</picture> or <img alt="Star history">). The alternation is
    # wrapped in its own non-capturing group so the | does not split the whole
    # pattern into "start\s*" vs "<picture>...end" — that would let the second
    # branch match a <picture> far away from the markers with DOTALL `.*?`
    # spanning arbitrary text between them.
    inner = r"(?:\s*|\s*(?:<picture>.*?</picture>|<img[^>]*alt=\"Star history\"[^>]*>)\s*)"
    pattern = re.compile(re.escape(start) + inner + re.escape(end), re.DOTALL)
    if not pattern.search(content):
        return False
    new_content = pattern.sub(f"{start}\n{block}\n{end}", content)
    readme_path.write_text(new_content)
    return True


def git_commit(workspace, message):
    """Stage all, commit if there are staged changes, push.

    Returns True if a commit was made, False if nothing changed."""
    subprocess.run(["git", "add", "-A"], check=True, cwd=workspace)
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=workspace
    )
    if diff.returncode == 0:
        return False
    subprocess.run(["git", "commit", "-m", message], check=True, cwd=workspace)
    subprocess.run(["git", "push"], check=True, cwd=workspace)
    return True


def write_outputs(changed, files, light, dark):
    """Append $GITHUB_OUTPUT lines.

    Uses heredoc syntax for the multi-file list because GitHub's file-command
    parser rejects values containing newlines in plain 'key=value' form.
    """
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
        if light:
            f.write(f"light={light}\n")
        if dark:
            f.write(f"dark={dark}\n")


def main():
    cfg = parse_inputs(os.environ)
    if not cfg["repos"]:
        print("No repos specified (INPUT_REPOS is empty)", file=sys.stderr)
        return 1

    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))
    out_dir = workspace / cfg["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    generated = []  # list of (repo, theme, filename)
    light_file = None
    dark_file = None

    for repo in cfg["repos"]:
        dates = fetch_stargazers(repo)
        if not dates:
            print(f"No stargazers for {repo}, skipping", file=sys.stderr)
            continue
        for theme in cfg["themes"]:
            dark = theme == "dark"
            fname = timestamp_filename(theme, ts)
            generate_svg(repo, dates, str(out_dir / fname), cfg["color"], cfg["title"], dark=dark)
            generated.append((repo, theme, fname))
            print(f"Generated {cfg['output_dir']}/{fname}")
            if dark:
                dark_file = fname
            else:
                light_file = fname

    if not generated:
        print("Nothing generated for any repo", file=sys.stderr)
        write_outputs(False, [], None, None)
        return 1

    for fname_to_keep in ([light_file, dark_file] if (light_file or dark_file) else []):
        if fname_to_keep:
            clean_old_files(out_dir, cfg["themes"], keep_filename=fname_to_keep)
            break
    else:
        clean_old_files(out_dir, cfg["themes"])

    if cfg["update_readme"]:
        block = build_picture_block(cfg["output_dir"], light_file, dark_file)
        updated = update_readme(workspace / cfg["readme"], block)
        if updated:
            print(f"Updated {cfg['readme']}")
        else:
            print(f"README markers not found or file missing, skipped README update", file=sys.stderr)

    files_rel = [f"{cfg['output_dir']}/{f}" for _, _, f in generated]
    write_outputs(True, files_rel, light_file, dark_file)

    if cfg["commit"]:
        committed = git_commit(workspace, cfg["commit_message"])
        print("Committed and pushed" if committed else "No changes to commit")

    return 0


if __name__ == "__main__":
    sys.exit(main())
