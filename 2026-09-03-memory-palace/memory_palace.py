#!/usr/bin/env python3
"""Build and explore a keyword-linked memory palace from plain text."""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "had", "has", "have", "he", "her", "his", "i", "in", "is", "it",
    "its", "of", "on", "or", "our", "that", "the", "their", "this", "to", "was",
    "we", "were", "will", "with", "you", "your", "not", "they", "them", "there",
}
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")


@dataclass
class Room:
    number: int
    title: str
    text: str
    keywords: list[str]


@dataclass
class Link:
    left: int
    right: int
    shared: list[str]
    weight: int


def words(text: str) -> list[str]:
    return [w.lower().strip("'-") for w in WORD_RE.findall(text)]


def split_rooms(text: str) -> list[str]:
    """Split on blank lines, or sentences when the input is a single paragraph."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) > 1:
        return blocks
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    return sentences or blocks


def title_for(text: str, number: int) -> str:
    first = re.sub(r"[^A-Za-z0-9 ]", "", text.splitlines()[0]).strip()
    return " ".join(first.split()[:5]).title() or f"Room {number}"


def keywords_for(text: str, limit: int = 5) -> list[str]:
    counts: dict[str, int] = {}
    for word in words(text):
        if word not in STOPWORDS:
            counts[word] = counts.get(word, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def build_palace(text: str, min_shared: int = 1) -> tuple[list[Room], list[Link]]:
    rooms = [Room(i + 1, title_for(block, i + 1), block, keywords_for(block))
             for i, block in enumerate(split_rooms(text))]
    links: list[Link] = []
    for left in range(len(rooms)):
        for right in range(left + 1, len(rooms)):
            shared = sorted(set(rooms[left].keywords) & set(rooms[right].keywords))
            if len(shared) >= min_shared:
                links.append(Link(left + 1, right + 1, shared, len(shared)))
    return rooms, links


def render_map(rooms: list[Room], links: list[Link]) -> str:
    """Render a compact, deterministic graph without terminal-specific packages."""
    neighbors = {room.number: [] for room in rooms}
    for link in links:
        neighbors[link.left].append(link.right)
        neighbors[link.right].append(link.left)
    lines = ["MEMORY PALACE", "=" * 60]
    for room in rooms:
        edges = ", ".join(f"#{n}" for n in sorted(neighbors[room.number])) or "(alone)"
        keys = ", ".join(room.keywords) or "no keywords"
        lines.append(f"#{room.number:02d} {room.title} [{keys}]")
        lines.append(f"     doors: {edges}")
    if links:
        lines += ["", "SHARED THREADS", "-" * 60]
        for link in sorted(links, key=lambda x: (-x.weight, x.left, x.right)):
            lines.append(f"#{link.left} <-> #{link.right}: {', '.join(link.shared)}")
    return "\n".join(lines)


def export_data(rooms: list[Room], links: list[Link]) -> dict:
    return {"rooms": [asdict(room) for room in rooms], "links": [asdict(link) for link in links]}


def interactive(rooms: list[Room], links: list[Link]) -> None:
    by_number = {room.number: room for room in rooms}
    while True:
        print("\n" + render_map(rooms, links))
        answer = input("\nEnter a room number, 'random', or 'q': ").strip().lower()
        if answer in {"q", "quit", "exit"}:
            return
        if answer == "random":
            room = random.choice(rooms)
        elif answer.isdigit() and int(answer) in by_number:
            room = by_number[int(answer)]
        else:
            print("Choose a listed room number, random, or q.")
            continue
        print(f"\nROOM #{room.number}: {room.title}\n{'-' * 60}\n{room.text}")
        print(f"Keywords: {', '.join(room.keywords) or 'none'}")


def sample_text() -> str:
    return """The lighthouse keeper records every storm in a red notebook. The lamp turns slowly above the sleeping harbor.

A brass key is hidden beneath the third stair. It opens the old observatory, where a telescope points toward Mars.

Mars is only a red dot tonight, but the notebook describes a garden there. The garden grows clocks instead of flowers.

Every clock keeps the same time as the lighthouse lamp. When the bells ring, the keeper remembers a door that was never built."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path, help="text file; omit to use the built-in example")
    parser.add_argument("--min-shared", type=int, default=1, metavar="N", help="keywords required to make a door (default: 1)")
    parser.add_argument("--map", action="store_true", help="print the palace and exit")
    parser.add_argument("--json", action="store_true", help="export the palace as JSON")
    parser.add_argument("--seed", type=int, help="seed random room selection")
    args = parser.parse_args(argv)
    if args.min_shared < 1:
        parser.error("--min-shared must be at least 1")
    if args.seed is not None:
        random.seed(args.seed)
    try:
        text = args.file.read_text(encoding="utf-8") if args.file else sample_text()
    except OSError as exc:
        print(f"memory-palace: {exc}", file=sys.stderr)
        return 2
    rooms, links = build_palace(text, args.min_shared)
    if not rooms:
        print("memory-palace: no rooms found", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(export_data(rooms, links), indent=2))
    elif args.map:
        print(render_map(rooms, links))
    else:
        interactive(rooms, links)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
