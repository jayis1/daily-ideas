#!/usr/bin/env python3
"""Turn text into a deterministic, inspectable ASCII garden of signals."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

VERSION = "1.1.1"
_SYMBOLS = "✦✧✺❋✿○◇"
_WORD_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)


@dataclass(frozen=True)
class Signal:
    """The stable visual properties derived for one distinct word."""

    word: str
    strength: int
    phase: int
    symbol: str


def _words(text: str) -> List[str]:
    """Extract words without accidentally keeping surrounding punctuation.

    NFC normalization keeps canonically equivalent spellings (for example,
    ``cafe\u0301`` and ``café``) together and prevents combining accents from
    being silently discarded by the token regular expression.
    """
    normalized = unicodedata.normalize("NFC", text)
    return [match.group(0).lower() for match in _WORD_RE.finditer(normalized)]


def analyze(text: str, seed: Optional[int] = None) -> List[Signal]:
    """Create one signal per distinct word, preserving first-seen order.

    With no seed, the complete input text is hashed, so repeated runs are
    reproducible. A supplied seed changes only the phase (the visual rhythm).
    """
    words = _words(text)
    default_seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)
    rng = random.Random(default_seed if seed is None else seed)
    seen: Set[str] = set()
    result: List[Signal] = []
    for word in words:
        if word in seen:
            continue
        seen.add(word)
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        result.append(Signal(word, 2 + digest[0] % 8, rng.randrange(8), _SYMBOLS[digest[1] % len(_SYMBOLS)]))
    return result


def summarize(signals: Sequence[Signal]) -> Dict[str, object]:
    """Return useful, machine-friendly aggregate information."""
    if not signals:
        return {"unique_signals": 0, "total_strength": 0, "average_strength": 0.0, "strongest": None}
    strongest = max(signals, key=lambda signal: signal.strength)
    total = sum(signal.strength for signal in signals)
    return {
        "unique_signals": len(signals),
        "total_strength": total,
        "average_strength": round(total / len(signals), 2),
        "strongest": strongest.word,
    }


def render(signals: Sequence[Signal], width: int = 72, height: int = 18) -> str:
    """Render signals on a bordered canvas, validating dimensions early."""
    if width < 24 or height < 6:
        raise ValueError("canvas must be at least 24x6")
    grid = [[" " for _ in range(width)] for _ in range(height)]
    mid = height // 2
    for x in range(width):
        grid[mid][x] = "─"
    count = len(signals)
    for index, signal in enumerate(signals):
        # Spread markers over the usable area, including the first and last.
        x = 2 if count <= 1 else 2 + round(index * (width - 5) / (count - 1))
        x = min(width - 3, x)
        amplitude = max(1, signal.strength * (height - 5) // 12)
        y = mid + round(math.sin(signal.phase * math.pi / 4) * amplitude)
        y = max(1, min(height - 2, y))
        grid[y][x] = signal.symbol
        for yy in range(min(y, mid), max(y, mid) + 1):
            if grid[yy][x] == " ":
                grid[yy][x] = "│"
        label = signal.word[:12]
        # Put a label after the flower when possible; near the right edge,
        # place it before the marker so it is not silently truncated.
        label_start = x + 1 if x + 1 + len(label) <= width - 1 else max(1, x - len(label) - 1)
        for offset, char in enumerate(label):
            if label_start + offset < width - 1:
                grid[y][label_start + offset] = char
    border = "+" + "-" * width + "+"
    return "\n".join([border] + ["|" + "".join(row) + "|" for row in grid] + [border])


def _write_json(path: str, text: str, signals: Sequence[Signal]) -> None:
    """Write a self-describing export and create a missing parent directory."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": VERSION, "text": text, "summary": summarize(signals), "signals": [asdict(signal) for signal in signals]}
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Grow an ASCII signal garden from text.")
    parser.add_argument("text", nargs="*", help="words to plant; reads stdin when omitted")
    parser.add_argument("--seed", type=int, help="reproducible phase seed")
    parser.add_argument("--width", type=int, default=72, help="canvas width (minimum 24; default: 72)")
    parser.add_argument("--height", type=int, default=18, help="canvas height (minimum 6; default: 18)")
    parser.add_argument("--json", metavar="FILE", help="also save signal data as JSON")
    parser.add_argument("--stats", action="store_true", help="print aggregate strength statistics")
    parser.add_argument("--version", action="version", version=f"Signal Garden {VERSION}")
    args = parser.parse_args(argv)
    try:
        text = " ".join(args.text) if args.text else sys.stdin.read().strip()
        signals = analyze(text, args.seed)
        print(render(signals, args.width, args.height))
        stats = summarize(signals)
        print(f"\n{stats['unique_signals']} unique signals | strongest: {stats['strongest'] or 'none'}")
        if args.stats:
            print(f"Total strength: {stats['total_strength']} | average: {stats['average_strength']:.2f}")
        if args.json:
            _write_json(args.json, text, signals)
            print(f"Saved {args.json}")
        return 0
    except (OSError, ValueError) as error:
        parser.error(str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
