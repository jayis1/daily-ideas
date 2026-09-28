#!/usr/bin/env python3
"""Find shared free windows in compact, local calendar descriptions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

VERSION = "1.0.0"
CLOCK = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


@dataclass(frozen=True, order=True)
class Window:
    start: int
    end: int

    @property
    def minutes(self) -> int:
        return self.end - self.start

    def label(self) -> str:
        return "{}-{}".format(format_clock(self.start), format_clock(self.end))


def parse_clock(value: str) -> int:
    """Parse a strict 24-hour HH:MM clock value into minutes after midnight."""
    value = value.strip()
    if not CLOCK.fullmatch(value):
        raise ValueError("invalid time {!r}; expected HH:MM".format(value))
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def format_clock(minutes: int) -> str:
    """Format minutes after midnight as HH:MM."""
    if not 0 <= minutes <= 24 * 60:
        raise ValueError("minutes must be between 0 and 1440")
    if minutes == 24 * 60:
        return "24:00"
    return "{:02d}:{:02d}".format(*divmod(minutes, 60))


def parse_window(value: str) -> Window:
    start_text, separator, end_text = value.strip().partition("-")
    if not separator:
        raise ValueError("invalid window {!r}; expected HH:MM-HH:MM".format(value))
    start = parse_clock(start_text)
    end = parse_clock(end_text)
    if end <= start:
        raise ValueError("window must end after it starts: {!r}".format(value))
    return Window(start, end)


def parse_person(value: str) -> Tuple[str, List[Window]]:
    """Parse NAME=HH:MM-HH:MM,...; an empty list means fully available."""
    name, separator, schedule = value.partition("=")
    name = name.strip()
    if not separator or not name:
        raise ValueError("person must use NAME=WINDOWS: {!r}".format(value))
    windows = [] if not schedule.strip() else [parse_window(item) for item in schedule.split(",")]
    return name, windows


def merge_windows(windows: Iterable[Window], start: int, end: int) -> List[Window]:
    """Clip, sort, and merge busy windows within the search bounds."""
    clipped = [Window(max(window.start, start), min(window.end, end))
               for window in windows
               if window.end > start and window.start < end]
    merged: List[Window] = []
    for window in sorted(clipped):
        if merged and window.start <= merged[-1].end:
            merged[-1] = Window(merged[-1].start, max(merged[-1].end, window.end))
        else:
            merged.append(window)
    return merged


def find_gaps(
    schedules: Mapping[str, Sequence[Window]],
    day: Window,
    minimum: int,
) -> List[Window]:
    """Return periods when every named person is free."""
    if not schedules:
        raise ValueError("provide at least one person")
    if minimum <= 0:
        raise ValueError("minimum duration must be positive")
    busy = merge_windows(
        (window for windows in schedules.values() for window in windows),
        day.start,
        day.end,
    )
    gaps: List[Window] = []
    cursor = day.start
    for window in busy:
        if window.start - cursor >= minimum:
            gaps.append(Window(cursor, window.start))
        cursor = max(cursor, window.end)
    if day.end - cursor >= minimum:
        gaps.append(Window(cursor, day.end))
    return gaps


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--person", action="append", required=True, metavar="NAME=WINDOWS",
        help="busy windows, for example 'Ada=09:00-10:00,13:00-14:00' (repeatable)",
    )
    parser.add_argument("--day", default="09:00-17:00", help="search bounds (default: 09:00-17:00)")
    parser.add_argument("--minutes", type=int, default=30, help="minimum free duration (default: 30)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--version", action="version", version="calendar-gap-finder {}".format(VERSION))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        day = parse_window(args.day)
        schedules: Dict[str, List[Window]] = {}
        for value in args.person:
            name, windows = parse_person(value)
            if name in schedules:
                raise ValueError("duplicate person: {!r}".format(name))
            schedules[name] = windows
        gaps = find_gaps(schedules, day, args.minutes)
    except ValueError as error:
        parser.error(str(error))

    if args.json:
        payload = {
            "day": day.label(),
            "minimum_minutes": args.minutes,
            "people": list(schedules),
            "gaps": [
                {"start": format_clock(gap.start), "end": format_clock(gap.end), "minutes": gap.minutes}
                for gap in gaps
            ],
        }
        print(json.dumps(payload, indent=2))
    elif gaps:
        print("Shared free windows ({} people, {}+ minutes):".format(len(schedules), args.minutes))
        for gap in gaps:
            print("- {} ({} minutes)".format(gap.label(), gap.minutes))
    else:
        print("No shared free window of at least {} minutes.".format(args.minutes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
