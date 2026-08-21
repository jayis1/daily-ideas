#!/usr/bin/env python3
"""Validate the committed catalog against the source tree."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from daily_ideas.catalog import load_apps, validate_apps  # noqa: E402


def main() -> int:
    apps = load_apps(ROOT / "src/daily_ideas/apps.json")
    errors = validate_apps(apps, ROOT)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"catalog valid: {len(apps)} apps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
