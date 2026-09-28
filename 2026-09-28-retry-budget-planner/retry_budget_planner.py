#!/usr/bin/env python3
"""Fit an exponential retry schedule inside a fixed time budget."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Sequence, TypedDict, Union

VERSION = "1.0.0"
Number = Union[int, float]


@dataclass(frozen=True)
class Attempt:
    number: int
    start: float
    end: float
    wait_before: float


class Plan(TypedDict):
    deadline: float
    attempt_timeout: float
    attempt_count: int
    elapsed: float
    unused: float
    attempts: List[Attempt]


def _positive_finite(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("{} must be a positive finite number".format(name))


def plan_retries(
    deadline: float,
    attempt_timeout: float,
    initial_delay: float,
    multiplier: float = 2.0,
    max_delay: Optional[float] = None,
    max_attempts: Optional[int] = None,
) -> Plan:
    """Return every full attempt that fits before the deadline.

    Delays happen only between attempts. An attempt is omitted unless both its
    preceding delay and its complete timeout fit within the budget.
    """
    for name, value in (
        ("deadline", deadline),
        ("attempt timeout", attempt_timeout),
        ("initial delay", initial_delay),
        ("multiplier", multiplier),
    ):
        _positive_finite(name, value)
    if max_delay is not None:
        _positive_finite("maximum delay", max_delay)
    if max_attempts is not None and (isinstance(max_attempts, bool) or max_attempts < 1):
        raise ValueError("maximum attempts must be at least 1")

    attempts: List[Attempt] = []
    start = 0.0
    wait_before = 0.0
    delay = initial_delay
    limit = max_delay if max_delay is not None else math.inf

    while start + attempt_timeout <= deadline + 1e-12:
        number = len(attempts) + 1
        end = start + attempt_timeout
        attempts.append(Attempt(number, start, end, wait_before))
        if max_attempts is not None and number >= max_attempts:
            break
        wait_before = min(delay, limit)
        start = end + wait_before
        delay = min(delay * multiplier, limit)

    elapsed = attempts[-1].end if attempts else 0.0
    return {
        "deadline": deadline,
        "attempt_timeout": attempt_timeout,
        "attempt_count": len(attempts),
        "elapsed": elapsed,
        "unused": deadline - elapsed,
        "attempts": attempts,
    }


def _clean_number(value: float) -> Number:
    return int(value) if value.is_integer() else round(value, 10)


def serializable(plan: Plan) -> Dict[str, object]:
    return {
        "deadline": _clean_number(plan["deadline"]),
        "attempt_timeout": _clean_number(plan["attempt_timeout"]),
        "attempt_count": plan["attempt_count"],
        "elapsed": _clean_number(plan["elapsed"]),
        "unused": _clean_number(plan["unused"]),
        "attempts": [
            {name: _clean_number(number) if isinstance(number, float) else number
             for name, number in asdict(attempt).items()}
            for attempt in plan["attempts"]
        ],
    }


def _format_seconds(value: float) -> str:
    text = "{:.10f}".format(value).rstrip("0").rstrip(".")
    return "{}s".format(text or "0")


def render_text(plan: Plan) -> str:
    attempts = plan["attempts"]
    assert isinstance(attempts, list)
    lines = [
        "Retry budget: {} attempt{} fit in {}".format(
            len(attempts), "" if len(attempts) == 1 else "s", _format_seconds(float(plan["deadline"]))
        )
    ]
    for attempt in attempts:
        if attempt.number == 1:
            prefix = "start immediately"
        else:
            prefix = "wait {}".format(_format_seconds(attempt.wait_before))
        lines.append(
            "- attempt {}: {}; run {}-{}".format(
                attempt.number,
                prefix,
                _format_seconds(attempt.start),
                _format_seconds(attempt.end),
            )
        )
    if not attempts:
        lines.append("- no complete attempt fits")
    lines.append("Unused budget: {}".format(_format_seconds(float(plan["unused"]))))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deadline", type=float, required=True, help="total time budget in seconds")
    parser.add_argument("--attempt-timeout", type=float, required=True, help="time reserved for each attempt")
    parser.add_argument("--initial-delay", type=float, required=True, help="delay after the first failure")
    parser.add_argument("--multiplier", type=float, default=2.0, help="backoff multiplier (default: 2)")
    parser.add_argument("--max-delay", type=float, help="cap each delay in seconds")
    parser.add_argument("--max-attempts", type=int, help="stop after this many attempts")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--version", action="version", version="retry-budget-planner {}".format(VERSION))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        plan = plan_retries(
            args.deadline,
            args.attempt_timeout,
            args.initial_delay,
            args.multiplier,
            args.max_delay,
            args.max_attempts,
        )
    except ValueError as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(serializable(plan), indent=2))
    else:
        print(render_text(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
