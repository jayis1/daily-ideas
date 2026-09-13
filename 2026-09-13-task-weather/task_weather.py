#!/usr/bin/env python3
"""Turn a Markdown task list into a tiny, deterministic workload forecast."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional

TASK_RE = re.compile(r"^\s*[-*+]\s+\[(?P<done>[ xX])\]\s+(?P<title>.+?)\s*$")
DATE_RE = re.compile(r"\b(?:due[: ]*)?(\d{4}-\d{2}-\d{2})\b", re.I)

@dataclass
class Task:
    title: str
    done: bool
    priority: int
    due: Optional[str]
    tags: List[str]

    @property
    def pressure(self) -> int:
        value = self.priority * 2 + (0 if self.done else 2)
        if self.due:
            try:
                days = (date.fromisoformat(self.due) - date.today()).days
                value += 5 if days < 0 else 3 if days <= 1 else 1 if days <= 3 else 0
            except ValueError:
                pass
        return value


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
        tags = re.findall(r"(?<!\w)#([\w-]+)", title)
        clean = re.sub(r"\s+", " ", title).strip()
        tasks.append(Task(clean, done, priority, due, tags))
    return tasks


def forecast(tasks: Iterable[Task]) -> dict:
    items = list(tasks)
    open_tasks = [task for task in items if not task.done]
    pressure = sum(task.pressure for task in open_tasks)
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
            "total": len(items), "open": len(open_tasks), "done": len(items) - len(open_tasks)}


def render(tasks: List[Task], report: dict, width: int = 58) -> str:
    width = max(36, width)
    lines = ["┌" + "─" * (width - 2) + "┐", "│" + " TASK WEATHER".ljust(width - 1) + "│",
             "│" + f"  {report['icon']}  {report['condition'].upper()}".ljust(width - 1) + "│",
             "│" + f"  pressure {report['pressure']:>2}  •  {report['open']} open / {report['total']} total".ljust(width - 1) + "│",
             "├" + "─" * (width - 2) + "┤"]
    if not tasks:
        lines.append("│" + "  No Markdown tasks found.".ljust(width - 1) + "│")
    else:
        for task in sorted(tasks, key=lambda item: (item.done, -item.pressure, item.title.lower())):
            marker = "✓" if task.done else "•"
            due = f"  due {task.due}" if task.due else ""
            label = f"  {marker} {task.title}{due}"
            lines.append("│" + label[: width - 3].ljust(width - 1) + "│")
            if not task.done:
                bar = "  " + "█" * min(12, task.pressure) + "░" * max(0, 12 - min(12, task.pressure))
                lines.append("│" + (bar + f"  pressure {task.pressure}")[: width - 3].ljust(width - 1) + "│")
    lines.append("└" + "─" * (width - 2) + "┘")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="Markdown file (default: stdin)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable forecast")
    parser.add_argument("--width", type=int, default=58, help="box width (default: 58)")
    args = parser.parse_args(argv)
    try:
        text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    except OSError as exc:
        parser.error(str(exc))
    tasks = parse_tasks(text)
    report = forecast(tasks)
    if args.json:
        print(json.dumps({"forecast": report, "tasks": [asdict(task) | {"pressure": task.pressure} for task in tasks]}, indent=2))
    else:
        print(render(tasks, report, args.width))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
