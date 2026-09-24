#!/usr/bin/env python3
"""Auction limited focus time between tasks that loudly want it."""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass


VERSION = "1.1.0"


@dataclass
class Task:
    name: str
    urgency: int
    dread: int
    minutes: int

    @property
    def bid(self) -> int:
        """A theatrical bid: urgency plus dread, capped for readable output."""
        return min(100, self.urgency * 7 + self.dread * 5)


def parse_task(spec: str) -> Task:
    """Parse ``name,urgency,dread,minutes`` with friendly validation."""
    parts = [part.strip() for part in spec.split(",")]
    if len(parts) != 4 or not parts[0]:
        raise ValueError("tasks must look like 'name,urgency,dread,minutes'")
    try:
        urgency, dread, minutes = (int(value) for value in parts[1:])
    except ValueError as exc:
        raise ValueError("urgency, dread, and minutes must be integers") from exc
    if not 1 <= urgency <= 10 or not 1 <= dread <= 10 or minutes < 1:
        raise ValueError("urgency and dread must be 1-10; minutes must be positive")
    return Task(parts[0], urgency, dread, minutes)


def auction(
    tasks: list[Task],
    focus_minutes: int,
    rng: random.Random,
    round_minutes: int = 5,
) -> dict:
    """Allocate focus in rounds, with a small chaos bonus for the underdog.

    ``tasks`` are copied before bidding, so callers can safely reuse their
    original task definitions for another auction.
    """
    if focus_minutes < 1:
        raise ValueError("focus minutes must be positive")
    if not 1 <= round_minutes <= 60:
        raise ValueError("round minutes must be between 1 and 60")
    names = [task.name for task in tasks]
    if len(names) != len(set(names)):
        raise ValueError("task names must be unique")
    remaining = focus_minutes
    original_minutes = {task.name: task.minutes for task in tasks}
    working = [Task(task.name, task.urgency, task.dread, task.minutes) for task in tasks]
    rounds = []
    ranked = sorted(working, key=lambda task: (task.bid, task.urgency), reverse=True)
    while remaining and ranked:
        active: list[Task] = [task for task in ranked if task.minutes]
        if not active:
            break
        scores = {task.name: task.bid + rng.randint(0, 12) for task in active}
        winner = max(active, key=lambda task: (scores[task.name], task.urgency))
        awarded = min(round_minutes, winner.minutes, remaining)
        winner.minutes -= awarded
        remaining -= awarded
        rounds.append({"winner": winner.name, "minutes": awarded, "score": scores[winner.name]})
        ranked = sorted(active, key=lambda task: (task.bid, task.urgency), reverse=True)
    allocation_map = {
        task.name: original_minutes[task.name] - task.minutes for task in working
    }
    return {"allocations": allocation_map, "unused_minutes": remaining, "rounds": rounds}


def format_report(tasks: list[Task], result: dict) -> str:
    lines = ["PROCRASTINATION AUCTION", "=" * 24, "The tasks have made their case.", ""]
    for task in tasks:
        awarded = result["allocations"][task.name]
        bar = "█" * awarded + "·" * max(0, task.minutes - awarded)
        lines.append(f"{task.name:<24} bid {task.bid:>3}  {bar} {awarded} min")
    lines += ["", f"Unused focus: {result['unused_minutes']} min"]
    if result["rounds"]:
        lines.append(f"Final ruling: {result['rounds'][-1]['winner']} got the last word.")
    return "\n".join(lines)


def default_tasks() -> list[Task]:
    return [
        Task("answer the email", 8, 4, 15),
        Task("organize the cables", 2, 7, 10),
        Task("learn one magic trick", 4, 2, 10),
        Task("wash the suspicious mug", 6, 9, 5),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Auction your focus minutes to competing tasks.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--task", action="append", metavar="NAME,URGENCY,DREAD,MINUTES",
                        help="task specification; repeat for multiple tasks")
    parser.add_argument("--minutes", type=int, default=20, help="focus minutes available (default: 20)")
    parser.add_argument("--round-minutes", type=int, default=5,
                        help="maximum minutes awarded per round (default: 5)")
    parser.add_argument("--seed", type=int, help="seed chaos for repeatable results")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args()
    try:
        tasks = [parse_task(spec) for spec in args.task] if args.task else default_tasks()
        if not tasks:
            raise ValueError("provide at least one task")
        result = auction(tasks, args.minutes, random.Random(args.seed), args.round_minutes)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps({"tasks": [asdict(task) for task in tasks], "result": result}, indent=2))
    else:
        print(format_report(tasks, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
