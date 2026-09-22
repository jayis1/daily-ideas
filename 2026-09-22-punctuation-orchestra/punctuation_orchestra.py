#!/usr/bin/env python3
"""Turn punctuation into a tiny, deterministic ASCII orchestra score."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


VERSION = "1.1.0"

PERCUSSION = {
    ".": ("kick", "boom"),
    ",": ("hat", "tss"),
    "!": ("crash", "KRAK"),
    "?": ("bell", "ding"),
    ":": ("rim", "tik"),
    ";": ("tom", "tok"),
    "-": ("shaker", "sha"),
}
MELODY = {
    "a": "C", "b": "D", "c": "E", "d": "F", "e": "G",
    "f": "A", "g": "B",
}


@dataclass(frozen=True)
class Hit:
    position: int
    symbol: str
    instrument: str
    sound: str


def extract_hits(text: str, limit: int | None = None) -> list[Hit]:
    """Return punctuation hits in source order, optionally capped.

    A cap keeps a pasted essay from producing an unwieldy score while still
    preserving the original character positions in the returned hits.
    """
    if limit is not None and limit < 0:
        raise ValueError("max-hits must be zero or greater")
    if limit == 0:
        return []
    hits = []
    for position, symbol in enumerate(text):
        if symbol in PERCUSSION:
            instrument, sound = PERCUSSION[symbol]
            hits.append(Hit(position, symbol, instrument, sound))
            if limit is not None and len(hits) >= limit:
                break
    return hits


def melody(text: str) -> str:
    """Map the first seven letter classes in the text to a simple melody."""
    notes = [MELODY[ch.lower()] for ch in text if ch.lower() in MELODY]
    return "-".join(notes[:16]) or "(no melody)"


def render(text: str, width: int = 64, max_hits: int | None = None) -> str:
    """Render a human-readable score without terminal control codes."""
    if width < 20:
        raise ValueError("width must be at least 20")
    hits = extract_hits(text, max_hits)
    title = text.strip().replace("\n", " ") or "(silent manuscript)"
    title = title[:width]
    lines = ["PUNCTUATION ORCHESTRA", f'"{title}"', ""]
    lines.append(f"Melody : {melody(text)}")
    if not hits:
        lines.append("Rhythm : (no punctuation — the orchestra is waiting)")
        return "\n".join(lines)
    lines.append("Rhythm : " + " | ".join(f"{h.symbol} {h.sound}" for h in hits))
    lines.append("")
    lines.append("Conductor's notes:")
    for hit in hits:
        lines.append(f"  beat {hit.position + 1:>2}: {hit.instrument:<7} {hit.sound}")
    return "\n".join(lines)


def as_json(text: str, max_hits: int | None = None) -> str:
    """Return the score as stable, machine-readable JSON."""
    hits = extract_hits(text, max_hits)
    payload = {
        "text": text,
        "melody": melody(text),
        "hits": [
            {"position": h.position, "symbol": h.symbol,
             "instrument": h.instrument, "sound": h.sound}
            for h in hits
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def read_input(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text:
        return " ".join(args.text)
    raise ValueError("provide TEXT or --file PATH")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("text", nargs="*", help="phrase to arrange")
    inputs.add_argument("--file", help="read the phrase from a UTF-8 text file")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of the score")
    parser.add_argument("--width", type=int, default=64, help="title width (minimum 20)")
    parser.add_argument(
        "--max-hits",
        type=int,
        metavar="N",
        help="include at most N percussion hits (default: all)",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = read_input(args)
        output = (
            as_json(text, args.max_hits)
            if args.json
            else render(text, args.width, args.max_hits)
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
