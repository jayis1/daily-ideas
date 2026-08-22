#!/usr/bin/env python3
"""Keyboard Heatmap Analyzer.

Analyze text and render a terminal heatmap showing which QWERTY keys get used.
The tool can read direct text, files, or stdin and emit either a terminal report
or structured JSON for downstream tooling.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

VERSION = "1.1.0"
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

# Approximate QWERTY touch-typing assignments. These power ergonomic summaries.
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

# Very rough cost model: home-row, alternating typing tends to feel easier.
ROW_EFFORT = {
    "number row": 1.45,
    "top row": 1.15,
    "home row": 1.0,
    "bottom row": 1.2,
    "thumb": 0.7,
}
FINGER_EFFORT = {
    "left pinky": 1.45,
    "left ring": 1.2,
    "left middle": 1.05,
    "left index": 1.0,
    "right index": 1.0,
    "right middle": 1.05,
    "right ring": 1.2,
    "right pinky": 1.45,
    "thumbs": 0.7,
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
    same_hand_bigrams: Counter[str]
    row_jump_bigrams: Counter[str]
    hand_alternation_count: int
    hand_repeat_count: int
    effort_score: float


def normalize_char(char: str) -> str | None:
    """Map an input character onto the supported QWERTY key set."""
    lowered = char.lower()
    if lowered in KEY_META:
        return lowered
    return SHIFT_MAP.get(char)


def iter_normalized_chars(text: str) -> Iterable[str]:
    """Yield normalized, keyboard-mapped characters from *text*."""
    for char in text:
        normalized = normalize_char(char)
        if normalized is not None:
            yield normalized


def analyze_text(text: str) -> Analysis:
    """Produce frequency and ergonomic statistics for the given text."""
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
    effort_score = 0.0

    for key, amount in counts.items():
        row_index, hand, finger = KEY_META[key]
        row_name = ROW_NAMES[row_index]
        row_usage[row_name] += amount
        hand_usage[hand] += amount
        finger_usage[finger] += amount
        effort_score += amount * ROW_EFFORT[row_name] * FINGER_EFFORT[finger]

    bigrams = Counter("".join(pair) for pair in zip(normalized_chars, normalized_chars[1:]))
    same_finger_bigrams: Counter[str] = Counter()
    same_hand_bigrams: Counter[str] = Counter()
    row_jump_bigrams: Counter[str] = Counter()
    hand_alternation_count = 0
    hand_repeat_count = 0

    for pair, amount in bigrams.items():
        left_key, right_key = pair[0], pair[1]
        left_row, left_hand, left_finger = KEY_META[left_key]
        right_row, right_hand, right_finger = KEY_META[right_key]

        if left_finger == right_finger:
            same_finger_bigrams[pair] = amount
        if left_hand == right_hand:
            same_hand_bigrams[pair] = amount
            if left_hand != "thumbs":
                hand_repeat_count += amount
        elif "thumbs" not in (left_hand, right_hand):
            hand_alternation_count += amount
        if left_row != right_row:
            row_jump_bigrams[pair] = amount

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
        same_hand_bigrams=same_hand_bigrams,
        row_jump_bigrams=row_jump_bigrams,
        hand_alternation_count=hand_alternation_count,
        hand_repeat_count=hand_repeat_count,
        effort_score=effort_score,
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
    """Render a simple keyboard-shaped heatmap table."""
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


def safe_rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator <= 0 else numerator / denominator * 100.0


def build_report(analysis: Analysis, top_n: int = 8) -> str:
    eligible_hand_bigrams = analysis.hand_alternation_count + analysis.hand_repeat_count
    same_finger_total = sum(analysis.same_finger_bigrams.values())
    row_jump_total = sum(analysis.row_jump_bigrams.values())
    left_right_delta = abs(analysis.hand_usage.get("left", 0) - analysis.hand_usage.get("right", 0))
    lines = [
        f"input chars:   {analysis.total_input}",
        f"mapped keys:   {analysis.total_mapped}",
        f"unique keys:   {len(analysis.counts)}",
        (
            f"space share:   {analysis.counts.get(' ', 0) / analysis.total_mapped * 100:.1f}%"
            if analysis.total_mapped else "space share:   0.0%"
        ),
        "",
        "ergonomic summary:",
        f"  - effort score:        {analysis.effort_score:.2f}",
        f"  - effort / 100 keys:   {(analysis.effort_score / analysis.total_mapped * 100):.2f}" if analysis.total_mapped else "  - effort / 100 keys:   0.00",
        f"  - hand alternation:    {safe_rate(analysis.hand_alternation_count, eligible_hand_bigrams):.1f}%",
        f"  - same-finger share:   {safe_rate(same_finger_total, sum(analysis.bigrams.values())):.1f}%",
        f"  - row-jump share:      {safe_rate(row_jump_total, sum(analysis.bigrams.values())):.1f}%",
        f"  - left/right delta:    {left_right_delta}",
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
    lines.append("row-jump bigrams:")
    row_jumps = analysis.row_jump_bigrams.most_common(top_n)
    if row_jumps:
        for pair, amount in row_jumps:
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


def serialize_analysis(analysis: Analysis, top_n: int) -> dict[str, object]:
    """Convert an Analysis object into JSON-friendly structures."""
    eligible_hand_bigrams = analysis.hand_alternation_count + analysis.hand_repeat_count
    payload: dict[str, object] = {
        "counts": dict(analysis.counts),
        "unmapped": dict(analysis.unmapped),
        "total_mapped": analysis.total_mapped,
        "total_input": analysis.total_input,
        "row_usage": dict(analysis.row_usage),
        "hand_usage": dict(analysis.hand_usage),
        "finger_usage": dict(analysis.finger_usage),
        "bigrams": dict(analysis.bigrams),
        "same_finger_bigrams": dict(analysis.same_finger_bigrams),
        "same_hand_bigrams": dict(analysis.same_hand_bigrams),
        "row_jump_bigrams": dict(analysis.row_jump_bigrams),
        "hand_alternation_count": analysis.hand_alternation_count,
        "hand_repeat_count": analysis.hand_repeat_count,
        "effort_score": analysis.effort_score,
    }
    payload["summary"] = {
        "top_keys": analysis.counts.most_common(top_n),
        "top_bigrams": analysis.bigrams.most_common(top_n),
        "hand_alternation_percent": round(safe_rate(analysis.hand_alternation_count, eligible_hand_bigrams), 3),
        "same_finger_percent": round(safe_rate(sum(analysis.same_finger_bigrams.values()), sum(analysis.bigrams.values())), 3),
        "row_jump_percent": round(safe_rate(sum(analysis.row_jump_bigrams.values()), sum(analysis.bigrams.values())), 3),
        "effort_per_100_keys": round((analysis.effort_score / analysis.total_mapped * 100), 3) if analysis.total_mapped else 0.0,
    }
    return payload


def read_text_file(path_str: str) -> str:
    path = Path(path_str)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"error: file not found: {path}") from exc
    except IsADirectoryError as exc:
        raise SystemExit(f"error: expected a file, got directory: {path}") from exc
    except UnicodeDecodeError as exc:
        raise SystemExit(f"error: could not decode UTF-8 from file: {path}") from exc


def stdin_has_data() -> bool:
    return not sys.stdin.isatty()


def read_inputs(args: argparse.Namespace) -> str:
    """Combine requested text sources into one analysis corpus."""
    parts: list[str] = []
    if args.preset:
        parts.append(PRESETS[args.preset])
    if args.file:
        parts.append(read_text_file(args.file))
    if args.text:
        parts.append(" ".join(args.text))
    if args.stdin or (stdin_has_data() and not parts):
        piped = sys.stdin.read()
        if piped:
            parts.append(piped)
    if not parts:
        parts.append("Typewriters dream in rows of amber light while coders sculpt tiny thunderclouds.")
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze text and render a terminal keyboard heatmap.",
    )
    parser.add_argument("text", nargs="*", help="Text to analyze.")
    parser.add_argument("--file", help="Path to a UTF-8 text file to analyze.")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="Analyze a built-in sample.")
    parser.add_argument("--stdin", action="store_true", help="Read text from standard input, even if other sources are also provided.")
    parser.add_argument("--top", type=int, default=8, help="How many top items to show in reports.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of the terminal heatmap report.")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args()
    if args.top < 1:
        parser.error("--top must be at least 1")
    return args


def main() -> int:
    args = parse_args()
    text = read_inputs(args)
    analysis = analyze_text(text)
    if args.json:
        print(json.dumps(serialize_analysis(analysis, top_n=args.top), indent=2, sort_keys=True))
        return 0
    print("KEYBOARD HEATMAP ANALYZER")
    print("=" * 26)
    print(render_heatmap(analysis, use_color=not args.no_color))
    print()
    print(build_report(analysis, top_n=args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
