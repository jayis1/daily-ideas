#!/usr/bin/env python3
"""Regenerate the app table bounded by markers in the root README."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
START = "<!-- APP_INDEX_START -->"
END = "<!-- APP_INDEX_END -->"


def main() -> int:
    apps = json.loads((ROOT / "src/daily_ideas/apps.json").read_text(encoding="utf-8"))["apps"]
    grouped = {}
    for app in apps:
        grouped.setdefault(app["category"], []).append(app)
    lines = [START, f"**{len(apps)} apps** across {len(grouped)} categories. This section is generated.", ""]
    for category in sorted(grouped):
        lines.extend((f"<details><summary>{category.title()} ({len(grouped[category])})</summary>", "", "| App | Interface | Description |", "|---|---|---|"))
        for app in grouped[category]:
            description = app["description"].replace("|", "\\|")
            lines.append(f"| [{app['title']}](./{app['path']}/) | {app['interface']} | {description} |")
        lines.extend(("", "</details>", ""))
    lines.append(END)
    text = README.read_text(encoding="utf-8")
    before, found, remainder = text.partition(START)
    if not found:
        raise SystemExit("README is missing app index markers")
    _, found, after = remainder.partition(END)
    if not found:
        raise SystemExit("README is missing closing app index marker")
    README.write_text(before + "\n".join(lines) + after, encoding="utf-8")
    print(f"updated README index with {len(apps)} apps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
