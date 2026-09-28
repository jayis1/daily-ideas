#!/usr/bin/env python3
"""Find groups of receipt items that exactly match a mystery subtotal."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable, Optional, Sequence

VERSION = "1.0.0"
MONEY = re.compile(r"^\$?(0|[1-9]\d*)(?:\.(\d{1,2}))?$")
MAX_ITEMS = 24


@dataclass(frozen=True)
class Item:
    name: str
    cents: int

    @property
    def price(self) -> str:
        return f"{self.cents // 100}.{self.cents % 100:02d}"


def parse_money(value: str) -> int:
    """Convert a non-negative dollar amount to integer cents without floats."""
    match = MONEY.fullmatch(value.strip())
    if not match:
        raise ValueError(f"invalid money amount: {value!r}")
    dollars, fraction = match.groups()
    return int(dollars) * 100 + int((fraction or "").ljust(2, "0"))


def parse_item(value: str) -> Item:
    """Parse NAME=PRICE into an item."""
    name, separator, amount = value.rpartition("=")
    name = name.strip()
    if not separator or not name:
        raise ValueError(f"item must use NAME=PRICE: {value!r}")
    cents = parse_money(amount)
    if cents == 0:
        raise ValueError(f"item price must be greater than zero: {value!r}")
    return Item(name, cents)


def load_items(path: Path) -> list[Item]:
    """Load one NAME=PRICE item per line, ignoring blanks and comments."""
    items = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            items.append(parse_item(stripped))
        except ValueError as error:
            raise ValueError(f"{path}:{line_number}: {error}") from error
    return items


def find_matches(
    items: Sequence[Item],
    target_cents: int,
    min_items: int = 1,
    max_items: Optional[int] = None,
    limit: int = 20,
) -> list[tuple[Item, ...]]:
    """Return exact-price combinations in stable size and input order."""
    if target_cents < 0:
        raise ValueError("target must not be negative")
    if min_items < 1:
        raise ValueError("min_items must be positive")
    if limit < 1:
        raise ValueError("limit must be positive")
    upper = len(items) if max_items is None else max_items
    if upper < min_items:
        raise ValueError("max_items must be at least min_items")

    matches: list[tuple[Item, ...]] = []
    for size in range(min_items, min(upper, len(items)) + 1):
        for group in combinations(items, size):
            if sum(item.cents for item in group) == target_cents:
                matches.append(group)
                if len(matches) == limit:
                    return matches
    return matches


def match_record(group: Iterable[Item]) -> dict[str, object]:
    items = list(group)
    cents = sum(item.cents for item in items)
    return {
        "items": [{"name": item.name, "price": item.price} for item in items],
        "total": f"{cents // 100}.{cents % 100:02d}",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("items", nargs="*", metavar="NAME=PRICE", help="receipt item, such as 'Tea=2.50'")
    parser.add_argument("--target", required=True, help="subtotal to reconstruct, such as 10.25")
    parser.add_argument("--file", type=Path, help="read additional NAME=PRICE lines from a UTF-8 file")
    parser.add_argument("--min-items", type=int, default=1, help="smallest group to consider (default: 1)")
    parser.add_argument("--max-items", type=int, help="largest group to consider (default: all)")
    parser.add_argument("--limit", type=int, default=20, help="stop after this many matches (default: 20)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--version", action="version", version=f"receipt-recomposer {VERSION}")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        items = [parse_item(value) for value in args.items]
        if args.file:
            items.extend(load_items(args.file))
        if not items:
            raise ValueError("provide at least one item or --file")
        if len(items) > MAX_ITEMS:
            raise ValueError(f"at most {MAX_ITEMS} items are supported")
        target = parse_money(args.target)
        matches = find_matches(items, target, args.min_items, args.max_items, args.limit)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps({"target": f"{target // 100}.{target % 100:02d}", "matches": [match_record(group) for group in matches]}, indent=2))
    elif not matches:
        print(f"No exact combinations total ${target // 100}.{target % 100:02d}.")
    else:
        print(f"Exact combinations for ${target // 100}.{target % 100:02d}:")
        for number, group in enumerate(matches, 1):
            details = " + ".join(f"{item.name} (${item.price})" for item in group)
            print(f"{number}. {details}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
