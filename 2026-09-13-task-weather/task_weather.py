#!/usr/bin/env python3
"""Turn a Markdown task list into a tiny workload forecast."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional

VERSION = "1.1.0"

TASK_RE = re.compile(r"^\s*[-*+]\s+\[(?P<done>[ xX])\]\s+(?P<title>.+?)\s*$")
DATE_RE = re.compile(r"\b(?:due[: ]*)?(\d{4}-\d{2}-\d{2})\b", re.I)

@dataclass
class Task:
    title: str
    done: bool
    priority: int
    due: Optional[str]
    tags: List[str]

    def score(self, as_of: Optional[date] = None) -> int:
        """Return urgency points, optionally evaluated on a supplied date.

        ``as_of`` makes reports reproducible in tests and scheduled jobs.  The
        property below remains convenient for callers that want today's score.
        """
        as_of = as_of or date.today()
        value = self.priority * 2 + (0 if self.done else 2)
        if self.due:
            try:
                days = (date.fromisoformat(self.due) - as_of).days
                value += 5 if days < 0 else 3 if days <= 1 else 1 if days <= 3 else 0
            except ValueError:
                pass
        return value

    @property
    def pressure(self) -> int:
        """Today's score (kept as a convenient public attribute)."""
        return self.score()


def parse_tasks(text: str) -> List[Task]:
    tasks = []
    for line in text.splitlines():
        match = TASK_RE.match(line)
        if not match:
            continue
        title = match.group("title")
        done = match.group("done").lower() == "x"
        priority = min(3, max(0, title.count("!")))
        found = DATE_RE.search(title)
        due = found.group(1) if found else None
        # DATE_RE is intentionally permissive around text, but only expose
        # calendar-valid dates in machine-readable output.
        if due:
            try:
                date.fromisoformat(due)
            except ValueError:
                due = None
        tags = list(dict.fromkeys(re.findall(r"(?<!\w)#([\w-]+)", title)))
        clean = re.sub(r"\s+", " ", title).strip()
        tasks.append(Task(clean, done, priority, due, tags))
    return tasks


def forecast(tasks: Iterable[Task], as_of: Optional[date] = None) -> dict:
    items = list(tasks)
    open_tasks = [task for task in items if not task.done]
    pressure = sum(task.score(as_of) for task in open_tasks)
    if not open_tasks:
        condition, icon = "clear skies", "☀"
    elif pressure >= 18:
        condition, icon = "thunderstorm", "⛈"
    elif pressure >= 10:
        condition, icon = "heavy rain", "🌧"
    elif pressure >= 5:
        condition, icon = "scattered clouds", "⛅"
    else:
        condition, icon = "mostly clear", "🌤"
    return {"condition": condition, "icon": icon, "pressure": pressure,
            "total": len(items), "open": len(open_tasks), "done": len(items) - len(open_tasks),
            "tags": {tag: sum(tag in task.tags for task in open_tasks)
                     for tag in sorted({tag for task in open_tasks for tag in task.tags})}}


def render(tasks: List[Task], report: dict, width: int = 58,
           as_of: Optional[date] = None) -> str:
    width = max(36, width)
    lines = ["┌" + "─" * (width - 2) + "┐", "│" + " TASK WEATHER".ljust(width - 1) + "│",
             "│" + f"  {report['icon']}  {report['condition'].upper()}".ljust(width - 1) + "│",
             "│" + f"  pressure {report['pressure']:>2}  •  {report['open']} open / {report['total']} total".ljust(width - 1) + "│",
             "├" + "─" * (width - 2) + "┤"]
    if not tasks:
        lines.append("│" + "  No Markdown tasks found.".ljust(width - 1) + "│")
    else:
        for task in sorted(tasks, key=lambda item: (item.done, -item.score(as_of), item.title.lower())):
            marker = "✓" if task.done else "•"
            due = f"  due {task.due}" if task.due else ""
            label = f"  {marker} {task.title}{due}"
            lines.append("│" + label[: width - 3].ljust(width - 1) + "│")
            if not task.done:
                score = task.score(as_of)
                bar = "  " + "█" * min(12, score) + "░" * max(0, 12 - min(12, score))
                lines.append("│" + (bar + f"  pressure {score}")[: width - 3].ljust(width - 1) + "│")
    lines.append("└" + "─" * (width - 2) + "┘")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("file", nargs="?", help="Markdown file (default: stdin)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable forecast")
    parser.add_argument("--open-only", action="store_true", help="hide completed tasks in the report")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="evaluate due dates on this date")
    parser.add_argument("--width", type=int, default=58, help="box width (default: 58)")
    args = parser.parse_args(argv)
    try:
        text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    except OSError as exc:
        parser.error(str(exc))
    as_of = None
    if args.as_of:
        try:
            as_of = date.fromisoformat(args.as_of)
        except ValueError:
            parser.error("--as-of must be a valid date in YYYY-MM-DD format")
    tasks = parse_tasks(text)
    report = forecast(tasks, as_of)
    display_tasks = [task for task in tasks if not task.done] if args.open_only else tasks
    if args.json:
        print(json.dumps({"forecast": report, "tasks": [asdict(task) | {"pressure": task.score(as_of)} for task in display_tasks]}, indent=2))
    else:
        print(render(display_tasks, report, args.width, as_of))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
