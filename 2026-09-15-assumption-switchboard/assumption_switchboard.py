#!/usr/bin/env python3
"""Explain how weighted decisions change when assumptions are nudged."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_decision(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("options"), list):
        raise ValueError("input must be an object with an 'options' list")
    criteria = data.get("criteria")
    if not isinstance(criteria, dict) or not criteria:
        raise ValueError("'criteria' must be a non-empty object of weights")
    weights = {}
    for name, weight in criteria.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("criterion names must be non-empty strings")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight < 0:
            raise ValueError(f"weight for {name!r} must be a non-negative number")
        weights[name] = float(weight)
    if sum(weights.values()) <= 0:
        raise ValueError("at least one criterion weight must be positive")
    options = []
    for option in data["options"]:
        if not isinstance(option, dict) or not isinstance(option.get("name"), str):
            raise ValueError("each option needs a string 'name'")
        scores = option.get("scores")
        if not isinstance(scores, dict) or set(scores) != set(weights):
            raise ValueError(f"{option.get('name', 'option')!r} must score every criterion exactly once")
        if any(not isinstance(scores[c], (int, float)) or isinstance(scores[c], bool) for c in scores):
            raise ValueError(f"scores for {option['name']!r} must be numbers")
        options.append({"name": option["name"], "scores": {c: float(scores[c]) for c in weights}})
    if not options:
        raise ValueError("at least one option is required")
    return {"criteria": weights, "options": options}


def ranking(data: dict, weights: dict[str, float]) -> list[tuple[str, float]]:
    total = sum(weights.values())
    results = []
    for option in data["options"]:
        score = sum(option["scores"][c] * weights[c] for c in weights) / total
        results.append((option["name"], score))
    return sorted(results, key=lambda item: (-item[1], item[0].casefold()))


def analyze(data: dict, steps: tuple[float, ...] = (0.25, 0.5, 2.0, 4.0)) -> dict:
    base = data["criteria"]
    baseline = ranking(data, base)
    winner = baseline[0][0]
    changes = []
    for criterion, original in base.items():
        for multiplier in steps:
            altered = dict(base)
            altered[criterion] = original * multiplier
            altered_rank = ranking(data, altered)
            if altered_rank[0][0] != winner:
                changes.append({"criterion": criterion, "multiplier": multiplier, "winner": altered_rank[0][0]})
    return {"baseline": baseline, "winner": winner, "changes": changes, "tested": len(base) * len(steps)}


def render(report: dict) -> str:
    lines = [f"Baseline winner: {report['winner']}", "", "Ranking:"]
    for index, (name, score) in enumerate(report["baseline"], 1):
        lines.append(f"  {index}. {name:<18} {score:6.2f}")
    lines.append("")
    if report["changes"]:
        lines.append("Winner changes when one weight is adjusted:")
        for change in report["changes"]:
            lines.append(f"  {change['criterion']}: x{change['multiplier']:g} -> {change['winner']}")
    else:
        lines.append("No winner changes in the tested adjustments.")
    lines.append(f"Tested {report['tested']} one-criterion adjustments; this is not a guarantee outside them.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reveal whether a weighted decision is sensitive to its assumptions.")
    parser.add_argument("input", type=Path, help="JSON decision file")
    args = parser.parse_args(argv)
    try:
        print(render(analyze(load_decision(args.input))))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
