"""Regenerate golden SVG files for snapshot tests.

Run this when generate_svg() output changes intentionally:

    .venv/bin/python tests/regenerate_golden.py

After regeneration, inspect `git diff tests/golden/` to confirm the visual
change is what you wanted, then commit.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mystarhistory import generate_svg

OUT_DIR = Path(__file__).parent / "golden"
OUT_DIR.mkdir(exist_ok=True)


def fixture_dates():
    base = datetime(2024, 1, 15, 12, 0, 0)
    offsets = [0, 0, 1, 5, 12, 13, 13, 28, 45, 46, 60, 75, 90, 91, 92,
               105, 120, 134, 135, 150]
    return sorted(
        (base + timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for d in offsets
    )


def main():
    dates = fixture_dates()
    repo = "test/example-repo"

    light = OUT_DIR / "star-history-light.svg"
    dark = OUT_DIR / "star-history-dark.svg"

    generate_svg(repo, dates, str(light), "#dd4528", "Star History", dark=False)
    generate_svg(repo, dates, str(dark), "#dd4528", "Star History", dark=True)

    print(f"Wrote {light} ({light.stat().st_size} bytes)")
    print(f"Wrote {dark} ({dark.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
