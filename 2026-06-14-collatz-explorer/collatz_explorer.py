#!/usr/bin/env python3
"""
Collatz Conjecture Explorer
============================
An interactive terminal tool that visualizes the Collatz conjecture (3n+1 problem)
through multiple ASCII visualization modes.

Given any positive integer n:
  - If n is even, the next term is n / 2
  - If n is odd, the next term is 3n + 1
The conjecture states that this sequence always reaches 1.

Modes:
  1. Sequence  — step-by-step sequence with parity indicators
  2. Path      — compact dot-graph showing rises and falls
  3. Histogram — bar chart of values reached in a sequence
  4. Tree      — reverse tree showing numbers that converge to a target
  5. Batch     — statistics across a range of starting numbers
  6. Hailstone — animated hailstone sequence chart (static render)
"""

import sys
import math
import argparse
from collections import defaultdict
from typing import List, Tuple, Dict, Optional

# ── Color helpers ──────────────────────────────────────────────────────────

ANSI = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "dim":     "\033[2m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "bg_blue": "\033[44m",
}


def color(name: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{ANSI.get(name, '')}{text}{ANSI['reset']}"


# ── Core Collatz functions ────────────────────────────────────────────────

def collatz_sequence(n: int) -> List[int]:
    """Return the full Collatz sequence starting from n down to 1."""
    if n < 1:
        raise ValueError("n must be a positive integer")
    seq = [n]
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        seq.append(n)
    return seq


def collatz_steps(n: int) -> int:
    """Return the number of steps for n to reach 1."""
    count = 0
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        count += 1
    return count


def collatz_max(n: int) -> int:
    """Return the maximum value reached in the Collatz sequence for n."""
    peak = n
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        if n > peak:
            peak = n
    return peak


# ── Reverse Collatz tree ──────────────────────────────────────────────────

def reverse_collatz_tree(target: int, depth: int) -> Dict[int, List[int]]:
    """
    Build a reverse tree: which numbers lead to `target` in <= `depth` steps?
    Returns a dict mapping step -> list of numbers that reach target in that many steps.
    """
    # BFS backwards from target
    layers: Dict[int, List[int]] = {0: [target]}
    visited = {target}
    for step in range(1, depth + 1):
        next_layer = []
        for val in layers[step - 1]:
            # Even predecessor: val * 2 (always works)
            pred_even = val * 2
            if pred_even not in visited:
                next_layer.append(pred_even)
                visited.add(pred_even)
            # Odd predecessor: (val - 1) / 3 works only if (val - 1) % 3 == 0
            # and result is odd and > 1
            if (val - 1) % 3 == 0:
                pred_odd = (val - 1) // 3
                if pred_odd > 1 and pred_odd % 2 == 1 and pred_odd not in visited:
                    next_layer.append(pred_odd)
                    visited.add(pred_odd)
        layers[step] = sorted(next_layer)
        if not next_layer:
            break
    return layers


# ── Visualization: Sequence ───────────────────────────────────────────────

def render_sequence(n: int, max_display: int = 50) -> str:
    """Render step-by-step Collatz sequence with parity indicators."""
    seq = collatz_sequence(n)
    total_steps = len(seq) - 1
    lines = []
    lines.append(color("bold", f"  Collatz Sequence for n = {n}"))
    lines.append(color("dim", f"  Steps to reach 1: {total_steps}"))
    lines.append(color("dim", f"  Peak value: {max(seq)}"))
    lines.append("")

    display = seq[:max_display]
    for i, val in enumerate(display):
        if i == 0:
            arrow = "START"
            parity = ""
        elif val == 1:
            arrow = "  →  "
            parity = color("green", " → 1! ")
        else:
            prev = seq[i - 1]
            if prev % 2 == 0:
                arrow = "  ÷2  "
                parity = color("cyan", f"{prev} → {val}")
            else:
                arrow = " ×3+1 "
                parity = color("yellow", f"{prev} → {val}")

        step_num = f"{i:>4}"
        val_str = f"{val:>12,}"
        lines.append(f"  {color('dim', step_num)}  {val_str}  {parity}")

    if len(seq) > max_display:
        lines.append(color("dim", f"  ... and {len(seq) - max_display} more steps"))

    lines.append("")
    lines.append(color("green", f"  ✓ Reached 1 in {total_steps} steps"))
    return "\n".join(lines)


# ── Visualization: Path ────────────────────────────────────────────────────

def render_path(n: int, width: int = 80) -> str:
    """Render a compact dot-graph showing rises and falls of the sequence."""
    seq = collatz_sequence(n)
    total_steps = len(seq) - 1
    height = min(30, total_steps + 2)
    lines = []
    lines.append(color("bold", f"  Collatz Path for n = {n}  (steps: {total_steps}, peak: {max(seq):,})"))
    lines.append("")

    if total_steps < 2:
        lines.append("  Too short to visualize meaningfully.")
        return "\n".join(lines)

    # Normalize values to 0..(height-1)
    max_val = max(seq)
    min_val = min(seq)
    val_range = max_val - min_val if max_val != min_val else 1

    # Build rows
    grid = [[' ' for _ in range(min(width, total_steps + 1))] for _ in range(height)]

    labels = []
    for i, val in enumerate(seq):
        if i >= width:
            break
        row = height - 1 - int((val - min_val) / val_range * (height - 1))
        col = min(i, width - 1)
        if 0 <= row < height and 0 <= col < len(grid[0]):
            if val == 1:
                grid[row][col] = color("green", "●")
            elif val == max_val:
                grid[row][col] = color("yellow", "▲")
            elif seq[i] % 2 == 0:
                grid[row][col] = color("cyan", "·")
            else:
                grid[row][col] = color("yellow", "·")

    for r, row in enumerate(grid):
        val_at_row = int(min_val + (height - 1 - r) / (height - 1) * val_range) if height > 1 else min_val
        label = f"{val_at_row:>10,}"
        if r == 0:
            label = f"{max_val:>10,}"
        elif r == height - 1:
            label = f"{min_val:>10,}"
        else:
            label = f"{'':>10}"
        line = f"  {label} │{''.join(row)}"
        lines.append(line)

    lines.append(f"  {'':>10} └{'─' * min(width, total_steps + 1)}")
    lines.append(f"  {'':>10}  Step 0{' ' * min(width - 8, 0)}{f'Step {total_steps}' if total_steps < width else ''}")

    return "\n".join(lines)


# ── Visualization: Histogram ──────────────────────────────────────────────

def render_histogram(n: int, bins: int = 20, bar_width: int = 50) -> str:
    """Render a horizontal histogram of values reached in the Collatz sequence."""
    seq = collatz_sequence(n)
    total_steps = len(seq) - 1
    lines = []
    lines.append(color("bold", f"  Collatz Value Histogram for n = {n}  (steps: {total_steps})"))
    lines.append("")

    if total_steps < 2:
        lines.append("  Too short to histogram meaningfully.")
        return "\n".join(lines)

    max_val = max(seq)
    min_val = 1
    log_max = math.log10(max_val) if max_val > 0 else 1

    # Use log-scale bins for better distribution
    bin_counts = [0] * bins
    for val in seq:
        if val <= 0:
            continue
        idx = min(int(math.log10(val) / log_max * (bins - 1)), bins - 1) if log_max > 0 else 0
        bin_counts[idx] += 1

    max_count = max(bin_counts) if bin_counts else 1

    for i in range(bins):
        low = 10 ** (log_max * i / bins) if i > 0 else 1
        high = 10 ** (log_max * (i + 1) / bins)
        count = bin_counts[i]
        bar_len = int(count / max_count * bar_width) if max_count > 0 else 0

        # Color the bar based on magnitude
        ratio = i / bins
        if ratio < 0.33:
            bar_color = "cyan"
        elif ratio < 0.66:
            bar_color = "yellow"
        else:
            bar_color = "red"

        label = f"{low:>8,.0f}-{high:>8,.0f}"
        bar = color(bar_color, "█" * bar_len)
        lines.append(f"  {label} │{bar} {count}")

    lines.append("")
    lines.append(color("dim", "  (log-scale bins showing value frequency in the hailstone sequence)"))
    return "\n".join(lines)


# ── Visualization: Tree ───────────────────────────────────────────────────

def render_tree(target: int, depth: int = 8, width: int = 80) -> str:
    """Render a reverse Collatz tree showing numbers that converge to target."""
    layers = reverse_collatz_tree(target, depth)
    lines = []
    lines.append(color("bold", f"  Reverse Collatz Tree: numbers that reach {target}"))
    lines.append("")

    for step in sorted(layers.keys()):
        nums = layers[step]
        if not nums:
            continue
        # Format numbers in columns
        num_strs = [str(n) for n in nums]
        col_width = max(len(s) for s in num_strs) + 2
        cols = width // col_width

        lines.append(color("cyan", f"  Step {step}:"))
        row = ""
        for i, ns in enumerate(num_strs):
            if i > 0 and i % max(cols, 1) == 0:
                lines.append(f"    {row}")
                row = ""
            row += f"{ns:>{col_width}}"
        if row:
            lines.append(f"    {row}")
        lines.append("")

    total = sum(len(v) for v in layers.values())
    lines.append(color("dim", f"  Total: {total} numbers converge to {target} within {depth} steps"))
    return "\n".join(lines)


# ── Visualization: Batch statistics ───────────────────────────────────────

def render_batch(start: int, end: int, width: int = 60) -> str:
    """Render batch statistics and bar chart for a range of starting numbers."""
    lines = []
    lines.append(color("bold", f"  Collatz Batch Statistics: n ∈ [{start}, {end}]"))
    lines.append("")

    data = []
    for n in range(start, end + 1):
        steps = collatz_steps(n)
        peak = collatz_max(n)
        data.append((n, steps, peak))

    steps_list = [d[1] for d in data]
    peaks_list = [d[2] for d in data]

    avg_steps = sum(steps_list) / len(steps_list)
    max_steps_n = max(data, key=lambda x: x[1])
    min_steps_n = min(data, key=lambda x: x[1])
    max_peak_n = max(data, key=lambda x: x[2])

    lines.append(f"  Average steps to reach 1:  {avg_steps:.1f}")
    lines.append(f"  Most steps:                n={max_steps_n[0]} → {max_steps_n[1]} steps")
    lines.append(f"  Fewest steps:              n={min_steps_n[0]} → {min_steps_n[1]} steps")
    lines.append(f"  Highest peak:              n={max_peak_n[0]} → {max_peak_n[2]:,}")
    lines.append("")

    # Bar chart of steps
    max_step = max(steps_list)
    lines.append(color("bold", "  Steps to reach 1:"))
    for n, steps, peak in data:
        bar_len = int(steps / max_step * width) if max_step > 0 else 0
        ratio = steps / max_step if max_step > 0 else 0
        if ratio < 0.33:
            bc = "green"
        elif ratio < 0.66:
            bc = "cyan"
        elif ratio < 0.85:
            bc = "yellow"
        else:
            bc = "red"
        bar = color(bc, "█" * bar_len)
        lines.append(f"  {n:>5} │{bar} {steps}")

    lines.append("")

    # Highlight interesting numbers
    lines.append(color("bold", "  Notable:"))
    # Numbers that take more than 2 * avg steps
    outliers = [(n, s) for n, s, p in data if s > avg_steps * 1.5]
    if outliers:
        lines.append(color("yellow", f"  Slow convergence (>1.5× avg): {', '.join(f'{n}({s} steps)' for n, s in outliers)}"))

    # Powers of 2 (fast convergence)
    powers_of_2 = [(n, s) for n, s, p in data if n & (n - 1) == 0 and n > 0]
    if powers_of_2:
        lines.append(color("cyan", f"  Powers of 2 (fast path):    {', '.join(f'{n}({s} steps)' for n, s in powers_of_2)}"))

    return "\n".join(lines)


# ── Visualization: Hailstone ──────────────────────────────────────────────

def render_hailstone(n: int, width: int = 80, height: int = 24) -> str:
    """Render a hailstone chart (value over time) using ASCII art."""
    seq = collatz_sequence(n)
    total_steps = len(seq) - 1
    lines = []
    lines.append(color("bold", f"  Hailstone Chart for n = {n}  (steps: {total_steps}, peak: {max(seq):,})"))
    lines.append("")

    if total_steps < 1:
        lines.append("  Trivial sequence.")
        return "\n".join(lines)

    # Sample sequence to fit width
    display_width = min(width, total_steps + 1)
    if len(seq) > display_width:
        indices = [int(i * (len(seq) - 1) / (display_width - 1)) for i in range(display_width)]
        sampled = [seq[i] for i in indices]
    else:
        sampled = seq
        indices = list(range(len(seq)))
        display_width = len(seq)

    max_val = max(sampled)

    # Build grid
    grid = [[' ' for _ in range(display_width)] for _ in range(height)]

    # Plot sampled values
    for col, val in enumerate(sampled):
        row = height - 1 - int((val - 1) / (max_val - 1) * (height - 1)) if max_val > 1 else height - 1
        row = max(0, min(height - 1, row))

        if val == 1:
            ch = color("green", "━")
        elif val == max_val:
            ch = color("red", "▲")
        elif val > n:
            ch = color("yellow", "╱")
        else:
            ch = color("cyan", "╲")
        grid[row][col] = ch

    # Draw horizontal axis and grid lines
    for r in range(height):
        val_at_row = int(1 + (height - 1 - r) / (height - 1) * (max_val - 1)) if height > 1 and max_val > 1 else 1
        label = f"{val_at_row:>9,}"
        if r == 0:
            label = f"{max_val:>9,}"
        elif r == height - 1:
            label = f"{'1':>9}"
        else:
            label = f"{'':>9}"

        line = f"  {label} │{''.join(grid[r])}"
        lines.append(line)

    lines.append(f"  {'':>9} └{'─' * display_width}")
    lines.append(f"  {'':>9}  Step 0{'Step ' + str(total_steps):>{display_width - 6}}")

    # Interesting stats
    lines.append("")
    odd_count = sum(1 for v in seq[:-1] if v % 2 == 1)
    even_count = sum(1 for v in seq[:-1] if v % 2 == 0)
    lines.append(f"  Odd operations (3n+1): {odd_count}   Even operations (n÷2): {even_count}   Ratio: {even_count/odd_count:.2f}:1" if odd_count > 0 else f"  Even operations (n÷2): {even_count}")
    lines.append(f"  Growth factor: peak {max(seq):,} is {max(seq)/n:.1f}× starting value")

    return "\n".join(lines)


# ── Interactive mode ───────────────────────────────────────────────────────

def interactive_mode():
    """Run an interactive exploration loop."""
    print(color("bold", "\n  ╔══════════════════════════════════════╗"))
    print(color("bold", "  ║    Collatz Conjecture Explorer       ║"))
    print(color("bold", "  ╚══════════════════════════════════════╝"))
    print()
    print("  Explore the famous 3n+1 problem!")
    print("  Given any positive integer n:")
    print(color("cyan",   "    If n is even → n ÷ 2"))
    print(color("yellow", "    If n is odd  → 3n + 1"))
    print(color("green", "    Conjecture: you will always reach 1"))
    print()

    modes = {
        "1": ("Sequence",   "Step-by-step sequence with parity"),
        "2": ("Path",       "Compact rise/fall dot-graph"),
        "3": ("Histogram",  "Value distribution histogram"),
        "4": ("Tree",       "Reverse convergence tree"),
        "5": ("Batch",      "Statistics across a range"),
        "6": ("Hailstone",  "Value-over-time hailstone chart"),
    }

    while True:
        print()
        print(color("bold", "  Visualization modes:"))
        for key, (name, desc) in modes.items():
            print(f"    {color('cyan', key)}. {color('bold', name):<12} — {color('dim', desc)}")
        print(f"    {color('cyan', 'q')}. Quit")
        print()

        choice = input(color("bold", "  Choose mode [1-6/q]: ")).strip().lower()
        if choice == 'q' or choice == '':
            print(color("dim", "  Goodbye! May all your sequences reach 1."))
            break

        if choice not in modes:
            print(color("red", "  Invalid choice."))
            continue

        if choice == "4":
            n = input("  Target number (default 1): ").strip()
            n = int(n) if n else 1
            d = input("  Tree depth (default 8): ").strip()
            d = int(d) if d else 8
            print()
            print(render_tree(n, d))
        elif choice == "5":
            start = input("  Start of range (default 1): ").strip()
            start = int(start) if start else 1
            end = input("  End of range (default 20): ").strip()
            end = int(end) if end else 20
            if end - start > 50:
                print(color("yellow", "  Clamping range to 50 numbers for readability."))
                end = start + 49
            print()
            print(render_batch(start, end))
        else:
            n = input("  Starting number (default 27): ").strip()
            n = int(n) if n else 27
            print()
            if choice == "1":
                print(render_sequence(n))
            elif choice == "2":
                print(render_path(n))
            elif choice == "3":
                print(render_histogram(n))
            elif choice == "6":
                print(render_hailstone(n))


# ── CLI entry point ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Collatz Conjecture Explorer — visualize the 3n+1 problem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Interactive mode
  %(prog)s -n 27 --mode hailstone   Hailstone chart for n=27
  %(prog)s -n 7 --mode sequence     Step-by-step for n=7
  %(prog)s --batch 1 20             Batch stats for range [1,20]
  %(prog)s --tree 1 --depth 10      Reverse tree from 1
        """
    )
    parser.add_argument("-n", "--number", type=int, default=None, help="Starting number (default: 27)")
    parser.add_argument("--mode", choices=["sequence", "path", "histogram", "tree", "batch", "hailstone"],
                        default="hailstone", help="Visualization mode (default: hailstone)")
    parser.add_argument("--batch", nargs=2, type=int, metavar=("START", "END"), help="Batch mode: range of numbers")
    parser.add_argument("--tree", type=int, metavar="TARGET", help="Tree mode: target number")
    parser.add_argument("--depth", type=int, default=8, help="Tree depth (default: 8)")
    parser.add_argument("--width", type=int, default=70, help="Chart width (default: 70)")
    parser.add_argument("--height", type=int, default=22, help="Chart height (default: 22)")
    parser.add_argument("--bins", type=int, default=15, help="Histogram bins (default: 15)")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    args = parser.parse_args()

    if args.no_color:
        # Override color function
        global ANSI
        ANSI = {k: "" for k in ANSI}

    # If no specific mode flags, run interactive
    if args.number is None and args.batch is None and args.tree is None:
        try:
            interactive_mode()
        except (KeyboardInterrupt, EOFError):
            print(color("dim", "\n  Goodbye!"))
        return

    # Determine mode and render
    if args.batch:
        start, end = args.batch
        if end - start > 50:
            print(f"Clamping range to 50 numbers for readability.")
            end = start + 49
        print(render_batch(start, end, width=args.width))
    elif args.tree:
        print(render_tree(args.tree, depth=args.depth, width=args.width))
    elif args.number:
        n = args.number
        if args.mode == "sequence":
            print(render_sequence(n))
        elif args.mode == "path":
            print(render_path(n, width=args.width))
        elif args.mode == "histogram":
            print(render_histogram(n, bins=args.bins, bar_width=args.width))
        elif args.mode == "hailstone":
            print(render_hailstone(n, width=args.width, height=args.height))


if __name__ == "__main__":
    main()