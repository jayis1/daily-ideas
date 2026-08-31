#!/usr/bin/env python3
"""Turn text into a deterministic ASCII garden of signals."""
from __future__ import annotations
import argparse, hashlib, json, math, random
from dataclasses import asdict, dataclass
from typing import Optional

@dataclass
class Signal:
    word: str
    strength: int
    phase: int
    symbol: str

def analyze(text: str, seed: Optional[int] = None) -> list[Signal]:
    """Create one signal per distinct word, preserving first-seen order."""
    words = [w.strip(".,!?;:()[]{}\"").lower() for w in text.split()]
    words = [w for w in words if w]
    seen = set(); result = []
    rng = random.Random(seed if seed is not None else int(hashlib.sha256(text.encode()).hexdigest()[:12], 16))
    symbols = "✦✧✺❋✿○◇"
    for word in words:
        if word in seen: continue
        seen.add(word)
        digest = hashlib.sha256(word.encode()).digest()
        result.append(Signal(word, 2 + digest[0] % 8, rng.randrange(8), symbols[digest[1] % len(symbols)]))
    return result

def render(signals: list[Signal], width: int = 72, height: int = 18) -> str:
    if width < 24 or height < 6: raise ValueError("canvas must be at least 24x6")
    grid = [[" " for _ in range(width)] for _ in range(height)]
    mid = height // 2
    for x in range(width):
        grid[mid][x] = "─"
    for i, signal in enumerate(signals):
        x = 2 + (i * max(3, (width - 6) // max(1, len(signals))))
        x = min(width - 3, x)
        amplitude = max(1, signal.strength * (height - 5) // 12)
        y = mid + round(math.sin(signal.phase * math.pi / 4) * amplitude)
        y = max(1, min(height - 2, y))
        grid[y][x] = signal.symbol
        for yy in range(min(y, mid), max(y, mid) + 1):
            if grid[yy][x] == " ": grid[yy][x] = "│"
        label = signal.word[: max(1, min(12, width - x - 2))]
        for j, char in enumerate(label):
            if x + 1 + j < width: grid[y][x + 1 + j] = char
    border = "+" + "-" * width + "+"
    return "\n".join([border] + ["|" + "".join(row) + "|" for row in grid] + [border])

def main() -> None:
    parser = argparse.ArgumentParser(description="Grow an ASCII signal garden from text.")
    parser.add_argument("text", nargs="*", help="words to plant; reads stdin when omitted")
    parser.add_argument("--seed", type=int, help="reproducible phase seed")
    parser.add_argument("--width", type=int, default=72)
    parser.add_argument("--height", type=int, default=18)
    parser.add_argument("--json", metavar="FILE", help="also save signal data as JSON")
    args = parser.parse_args()
    text = " ".join(args.text) if args.text else input("Plant a sentence: ")
    signals = analyze(text, args.seed)
    print(render(signals, args.width, args.height))
    print(f"\n{len(signals)} unique signals | strongest: {max(signals, key=lambda s: s.strength).word if signals else 'none'}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump({"text": text, "signals": [asdict(s) for s in signals]}, handle, indent=2)
        print(f"Saved {args.json}")

if __name__ == "__main__": main()
