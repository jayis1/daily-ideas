#!/usr/bin/env python3
"""Keyboard Heatmap Analyzer.

Analyze text and render a terminal heatmap showing which QWERTY keys get used.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

RESET = "\033[0m"
LEVEL_COLORS = [
    "\033[38;5;238m",  # very low
    "\033[38;5;109m",
    "\033[38;5;150m",
    "\033[38;5;221m",
    "\033[38;5;208m",
    "\033[38;5;196m",  # very high
]

KEY_ROWS = [
    list("1234567890-="),
    list("qwertyuiop[]\\"),
    list("asdfghjkl;'"),
    list("zxcvbnm,./"),
    [" "],
]

SHIFT_MAP = {
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    "{": "[",
    "}": "]",
    "|": "\\",
    ":": ";",
    '"': "'",
    "<": ",",
    ">": ".",
    "?": "/",
    "~": "`",
}

ROW_NAMES = {
    0: "number row",
    1: "top row",
    2: "home row",
    3: "bottom row",
    4: "thumb",
}

KEY_META = {
    "1": (0, "left", "left pinky"),
    "2": (0, "left", "left ring"),
    "3": (0, "left", "left middle"),
    "4": (0, "left", "left index"),
    "5": (0, "left", "left index"),
    "6": (0, "right", "right index"),
    "7": (0, "right", "right index"),
    "8": (0, "right", "right middle"),
    "9": (0, "right", "right ring"),
    "0": (0, "right", "right pinky"),
    "-": (0, "right", "right pinky"),
    "=": (0, "right", "right pinky"),
    "q": (1, "left", "left pinky"),
    "w": (1, "left", "left ring"),
    "e": (1, "left", "left middle"),
    "r": (1, "left", "left index"),
    "t": (1, "left", "left index"),
    "y": (1, "right", "right index"),
    "u": (1, "right", "right index"),
    "i": (1, "right", "right middle"),
    "o": (1, "right", "right ring"),
    "p": (1, "right", "right pinky"),
    "[": (1, "right", "right pinky"),
    "]": (1, "right", "right pinky"),
    "\\": (1, "right", "right pinky"),
    "a": (2, "left", "left pinky"),
    "s": (2, "left", "left ring"),
    "d": (2, "left", "left middle"),
    "f": (2, "left", "left index"),
    "g": (2, "left", "left index"),
    "h": (2, "right", "right index"),
    "j": (2, "right", "right index"),
    "k": (2, "right", "right middle"),
    "l": (2, "right", "right ring"),
    ";": (2, "right", "right pinky"),
    "'": (2, "right", "right pinky"),
    "z": (3, "left", "left pinky"),
    "x": (3, "left", "left ring"),
    "c": (3, "left", "left middle"),
    "v": (3, "left", "left index"),
    "b": (3, "left", "left index"),
    "n": (3, "right", "right index"),
    "m": (3, "right", "right index"),
    ",": (3, "right", "right middle"),
    ".": (3, "right", "right ring"),
    "/": (3, "right", "right pinky"),
    " ": (4, "thumbs", "thumbs"),
}

PRESETS = {
    "code": "def heatmap(text): return {char: text.count(char) for char in set(text)}\nprint(heatmap('keyboard analytics!'))",
    "poem": "silver rain on midnight rails / soft static in the summer wires",
    "pangram": "Sphinx of black quartz, judge my vow. Pack my box with five dozen liquor jugs!",
}


@dataclass
class Analysis:
    counts: Counter[str]
    unmapped: Counter[str]
    total_mapped: int
    total_input: int
    row_usage: Counter[str]
    hand_usage: Counter[str]
    finger_usage: Counter[str]
    bigrams: Counter[str]
    same_finger_bigrams: Counter[str]


def normalize_char(char: str) -> str | None:
    lowered = char.lower()
    if lowered in KEY_META:
        return lowered
    return SHIFT_MAP.get(char)


def iter_normalized_chars(text: str) -> Iterable[str]:
    for char in text:
        normalized = normalize_char(char)
        if normalized is not None:
            yield normalized


def analyze_text(text: str) -> Analysis:
    counts: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    normalized_chars: list[str] = []

    for char in text:
        normalized = normalize_char(char)
        if normalized is None:
            unmapped[char] += 1
            continue
        counts[normalized] += 1
        normalized_chars.append(normalized)

    row_usage: Counter[str] = Counter()
    hand_usage: Counter[str] = Counter()
    finger_usage: Counter[str] = Counter()

    for key, amount in counts.items():
        row_index, hand, finger = KEY_META[key]
        row_usage[ROW_NAMES[row_index]] += amount
        hand_usage[hand] += amount
        finger_usage[finger] += amount

    bigrams = Counter(
        "".join(pair)
        for pair in zip(normalized_chars, normalized_chars[1:])
    )
    same_finger_bigrams = Counter(
        pair for pair, amount in bigrams.items()
        if KEY_META[pair[0]][2] == KEY_META[pair[1]][2]
        for _ in range(amount)
    )

    return Analysis(
        counts=counts,
        unmapped=unmapped,
        total_mapped=sum(counts.values()),
        total_input=len(text),
        row_usage=row_usage,
        hand_usage=hand_usage,
        finger_usage=finger_usage,
        bigrams=bigrams,
        same_finger_bigrams=same_finger_bigrams,
    )


def intensity_level(count: int, max_count: int) -> int:
    if count <= 0 or max_count <= 0:
        return 0
    ratio = count / max_count
    if ratio < 0.15:
        return 1
    if ratio < 0.3:
        return 2
    if ratio < 0.5:
        return 3
    if ratio < 0.75:
        return 4
    return 5


def style(text: str, level: int, use_color: bool) -> str:
    if not use_color or level <= 0:
        return text
    return f"{LEVEL_COLORS[level]}{text}{RESET}"


def format_key(key: str, count: int, max_count: int, use_color: bool) -> str:
    label = "space" if key == " " else key
    cell = f"{label:>5}:{count:<3}"
    return style(cell, intensity_level(count, max_count), use_color)


def render_heatmap(analysis: Analysis, use_color: bool = True) -> str:
    max_count = max(analysis.counts.values(), default=0)
    lines = []
    for row in KEY_ROWS[:-1]:
        rendered = " ".join(format_key(key, analysis.counts.get(key, 0), max_count, use_color) for key in row)
        lines.append(rendered)
    lines.append(format_key(" ", analysis.counts.get(" ", 0), max_count, use_color))
    return "\n".join(lines)


def percentage(counter: Counter[str], total: int) -> list[tuple[str, int, float]]:
    if total == 0:
        return [(name, amount, 0.0) for name, amount in counter.most_common()]
    return [(name, amount, amount / total * 100.0) for name, amount in counter.most_common()]


def build_report(analysis: Analysis, top_n: int = 8) -> str:
    lines = [
        f"input chars:   {analysis.total_input}",
        f"mapped keys:   {analysis.total_mapped}",
        f"unique keys:   {len(analysis.counts)}",
        f"space share:   {analysis.counts.get(' ', 0) / analysis.total_mapped * 100:.1f}%" if analysis.total_mapped else "space share:   0.0%",
        "",
        "row usage:",
    ]
    for row, amount, pct in percentage(analysis.row_usage, analysis.total_mapped):
        lines.append(f"  - {row:<11} {amount:>4} ({pct:>5.1f}%)")
    lines.append("hand usage:")
    for hand, amount, pct in percentage(analysis.hand_usage, analysis.total_mapped):
        lines.append(f"  - {hand:<11} {amount:>4} ({pct:>5.1f}%)")
    lines.append("finger hotspots:")
    for finger, amount, pct in percentage(analysis.finger_usage, analysis.total_mapped)[:top_n]:
        lines.append(f"  - {finger:<12} {amount:>4} ({pct:>5.1f}%)")
    lines.append("top keys:")
    for key, amount in analysis.counts.most_common(top_n):
        label = "space" if key == " " else key
        lines.append(f"  - {label:<12} {amount}")
    lines.append("top bigrams:")
    for pair, amount in analysis.bigrams.most_common(top_n):
        shown = pair.replace(" ", "␠")
        lines.append(f"  - {shown:<12} {amount}")
    lines.append("same-finger bigrams:")
    same_finger = analysis.same_finger_bigrams.most_common(top_n)
    if same_finger:
        for pair, amount in same_finger:
            shown = pair.replace(" ", "␠")
            lines.append(f"  - {shown:<12} {amount}")
    else:
        lines.append("  - none detected")
    if analysis.unmapped:
        lines.append("unmapped chars:")
        for char, amount in analysis.unmapped.most_common(top_n):
            label = repr(char)
            lines.append(f"  - {label:<12} {amount}")
    return "\n".join(lines)


def read_inputs(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.preset:
        parts.append(PRESETS[args.preset])
    if args.file:
        parts.append(Path(args.file).read_text(encoding="utf-8"))
    if args.text:
        parts.append(" ".join(args.text))
    if not parts:
        parts.append("Typewriters dream in rows of amber light while coders sculpt tiny thunderclouds.")
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze text and render a terminal keyboard heatmap.")
    parser.add_argument("text", nargs="*", help="Text to analyze.")
    parser.add_argument("--file", help="Path to a UTF-8 text file to analyze.")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="Analyze a built-in sample.")
    parser.add_argument("--top", type=int, default=8, help="How many top items to show in reports.")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = read_inputs(args)
    analysis = analyze_text(text)
    print("KEYBOARD HEATMAP ANALYZER")
    print("=" * 26)
    print(render_heatmap(analysis, use_color=not args.no_color))
    print()
    print(build_report(analysis, top_n=max(1, args.top)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
