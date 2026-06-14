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
  1. Sequence   — step-by-step sequence with parity indicators
  2. Path       — compact dot-graph showing rises and falls
  3. Histogram  — bar chart of values reached in a sequence
  4. Tree       — reverse tree showing numbers that converge to a target
  5. Batch      — statistics across a range of starting numbers
  6. Hailstone  — animated hailstone sequence chart (static render)
  7. Converge   — convergence speed chart showing steps to reach 1 for a range
  8. Density    — heat map of Collatz stopping times across a range
"""

import sys
import os
import math
import argparse
from collections import defaultdict
from typing import List, Tuple, Dict, Optional
from functools import lru_cache

__version__ = "1.1.0"

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

_color_enabled = True  # Global toggle, set by --no-color or NO_COLOR env var


def color(name: str, text: str) -> str:
    """Apply ANSI color to text if colors are enabled."""
    if not _color_enabled:
        return text
    return f"{ANSI.get(name, '')}{text}{ANSI['reset']}"


# ── Core Collatz functions ────────────────────────────────────────────────

def collatz_sequence(n: int) -> List[int]:
    """Return the full Collatz sequence starting from n down to 1.

    Args:
        n: A positive integer to start the sequence from.

    Returns:
        List of integers representing the Collatz sequence from n to 1.

    Raises:
        ValueError: If n is not a positive integer.
    """
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
    """Return the number of steps for n to reach 1 (stopping time).

    Uses memoization for performance on repeated calls.

    Args:
        n: A positive integer.

    Returns:
        The number of steps in the Collatz sequence before reaching 1.

    Raises:
        ValueError: If n is not a positive integer.
    """
    if n < 1:
        raise ValueError("n must be a positive integer")
    return _collatz_steps_cached(n)


@lru_cache(maxsize=2**20)
def _collatz_steps_cached(n: int) -> int:
    """Memoized helper for collatz_steps."""
    if n == 1:
        return 0
    if n % 2 == 0:
        return 1 + _collatz_steps_cached(n // 2)
    else:
        return 1 + _collatz_steps_cached(3 * n + 1)


def collatz_max(n: int) -> int:
    """Return the maximum value reached in the Collatz sequence for n.

    Args:
        n: A positive integer.

    Returns:
        The peak value in the Collatz sequence starting from n.

    Raises:
        ValueError: If n is not a positive integer.
    """
    if n < 1:
        raise ValueError("n must be a positive integer")
    peak = n
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        if n > peak:
            peak = n
    return peak


def collatz_stats(n: int) -> Dict[str, object]:
    """Compute comprehensive statistics about the Collatz sequence for n.

    Args:
        n: A positive integer.

    Returns:
        Dictionary with keys: steps, peak, growth_factor, odd_ops, even_ops,
        odd_even_ratio, reaches_1 (always True for valid input).
    """
    if n < 1:
        raise ValueError("n must be a positive integer")
    seq = collatz_sequence(n)
    odd_count = sum(1 for v in seq[:-1] if v % 2 == 1)
    even_count = sum(1 for v in seq[:-1] if v % 2 == 0)
    peak = max(seq)
    return {
        "steps": len(seq) - 1,
        "peak": peak,
        "growth_factor": peak / n if n > 0 else 0,
        "odd_ops": odd_count,
        "even_ops": even_count,
        "odd_even_ratio": even_count / odd_count if odd_count > 0 else float("inf"),
        "reaches_1": True,
    }


# ── Reverse Collatz tree ──────────────────────────────────────────────────

def reverse_collatz_tree(target: int, depth: int) -> Dict[int, List[int]]:
    """Build a reverse tree: which numbers lead to `target` in <= `depth` steps?

    Returns a dict mapping step -> list of numbers that reach target in that
    many steps. Built via BFS: from any value, the two possible predecessors
    are 2n (always valid) and (n-1)/3 (valid only when it produces an odd
    integer > 1).

    Args:
        target: The number to build the reverse tree from.
        depth: Maximum depth to search.

    Returns:
        Dictionary mapping step number to list of numbers at that step.
    """
    if target < 1:
        raise ValueError("target must be a positive integer")
    if depth < 1:
        raise ValueError("depth must be at least 1")
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
    """Render step-by-step Collatz sequence with parity indicators.

    Args:
        n: Starting number.
        max_display: Maximum number of steps to display before truncating.

    Returns:
        Multi-line string with the visualization.
    """
    seq = collatz_sequence(n)
    total_steps = len(seq) - 1
    lines = []
    lines.append(color("bold", f"  Collatz Sequence for n = {n}"))
    lines.append(color("dim", f"  Steps to reach 1: {total_steps}"))
    lines.append(color("dim", f"  Peak value: {max(seq):,}"))
    lines.append("")

    display = seq[:max_display]
    for i, val in enumerate(display):
        if i == 0:
            parity = color("green", "START")
        elif val == 1:
            parity = color("green", " → 1! ")
        else:
            prev = seq[i - 1]
            if prev % 2 == 0:
                parity = color("cyan", f"{prev:,} → {val:,}")
            else:
                parity = color("yellow", f"{prev:,} → {val:,}")

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
    """Render a compact dot-graph showing rises and falls of the sequence.

    Args:
        n: Starting number.
        width: Chart width in characters.

    Returns:
        Multi-line string with the visualization.
    """
    seq = collatz_sequence(n)
    total_steps = len(seq) - 1
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
    height = min(30, total_steps + 2)

    # Build grid
    grid = [[' ' for _ in range(min(width, total_steps + 1))] for _ in range(height)]

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
    """Render a horizontal histogram of values reached in the Collatz sequence.

    Uses log-scale bins for better distribution of widely-varying values.

    Args:
        n: Starting number.
        bins: Number of histogram bins.
        bar_width: Maximum bar width in characters.

    Returns:
        Multi-line string with the visualization.
    """
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
    """Render a reverse Collatz tree showing numbers that converge to target.

    Args:
        target: The target number for the reverse tree.
        depth: Maximum tree depth.
        width: Display width in characters.

    Returns:
        Multi-line string with the visualization.
    """
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
        cols = width // max(col_width, 1)

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
    """Render batch statistics and bar chart for a range of starting numbers.

    Args:
        start: First number in the range (inclusive).
        end: Last number in the range (inclusive).
        width: Bar chart width in characters.

    Returns:
        Multi-line string with the visualization.
    """
    if end < start:
        start, end = end, start
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
    # Numbers that take more than 1.5 * avg steps
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
    """Render a hailstone chart (value over time) using ASCII art.

    Args:
        n: Starting number.
        width: Chart width in characters.
        height: Chart height in characters.

    Returns:
        Multi-line string with the visualization.
    """
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
    if odd_count > 0:
        lines.append(f"  Odd operations (3n+1): {odd_count}   Even operations (n÷2): {even_count}   Ratio: {even_count/odd_count:.2f}:1")
    else:
        lines.append(f"  Even operations (n÷2): {even_count}")
    lines.append(f"  Growth factor: peak {max(seq):,} is {max(seq)/n:.1f}× starting value")

    return "\n".join(lines)


# ── Visualization: Convergence Speed ──────────────────────────────────────

def render_converge(start: int, end: int, width: int = 60, height: int = 24) -> str:
    """Render a chart showing Collatz stopping times (convergence speed) for a range.

    Creates an ASCII heat map where each position shows the stopping time for that
    number, revealing patterns in convergence speed across different starting values.

    Args:
        start: First number in range.
        end: Last number in range.
        width: Chart width in characters.
        height: Chart height in characters.

    Returns:
        Multi-line string with the visualization.
    """
    if end < start:
        start, end = end, start
    lines = []
    lines.append(color("bold", f"  Collatz Convergence Speed: n ∈ [{start}, {end}]"))
    lines.append("")

    # Compute stopping times
    stopping_times = {n: collatz_steps(n) for n in range(start, end + 1)}
    max_steps = max(stopping_times.values()) if stopping_times else 1
    min_steps = min(stopping_times.values()) if stopping_times else 0
    step_range = max_steps - min_steps if max_steps != min_steps else 1

    # ASCII heat map characters from low to high
    heat_chars = " ░▒▓█"

    # Determine how many numbers per row
    nums_per_row = width - 6  # leave room for row labels
    num_range = end - start + 1
    nums_per_row = max(1, min(nums_per_row, 50))

    lines.append(color("dim", f"  Min steps: {min_steps}  Max steps: {max_steps}  Avg: {sum(stopping_times.values())/len(stopping_times):.1f}"))
    lines.append("")

    # Legend
    legend = "  Legend: "
    for i, ch in enumerate(heat_chars):
        low = min_steps + (i / len(heat_chars)) * step_range
        high = min_steps + ((i + 1) / len(heat_chars)) * step_range
        legend += color("cyan" if i < 2 else "yellow" if i < 3 else "red", f"{ch}{int(low)}-{int(high)} ")
    lines.append(legend)
    lines.append("")

    # Heat map rows
    n = start
    while n <= end:
        row_nums = list(range(n, min(n + nums_per_row, end + 1)))
        row_str = f"  {n:>6} │"
        for num in row_nums:
            steps = stopping_times[num]
            normalized = (steps - min_steps) / step_range if step_range > 0 else 0
            idx = min(int(normalized * (len(heat_chars) - 1)), len(heat_chars) - 1)
            if idx < 2:
                ch = color("green", heat_chars[idx])
            elif idx < 3:
                ch = color("yellow", heat_chars[idx])
            else:
                ch = color("red", heat_chars[idx])
            row_str += ch
        lines.append(row_str)
        n += nums_per_row

    lines.append("")
    # Print top-5 slowest converging numbers
    slowest = sorted(stopping_times.items(), key=lambda x: -x[1])[:5]
    lines.append(color("bold", "  Slowest convergence:"))
    for n, steps in slowest:
        peak = collatz_max(n)
        lines.append(f"    n={n:>6}  steps={steps:>4}  peak={peak:>10,}")

    return "\n".join(lines)


# ── Visualization: Density ──────────────────────────────────────────────

def render_density(start: int, end: int, width: int = 60, height: int = 20) -> str:
    """Render a 2D density map of Collatz stopping times.

    Displays a 2D grid where the x-axis is the starting number and the y-axis
    represents stopping time, with characters colored by density.

    Args:
        start: First number in range.
        end: Last number in range.
        width: Chart width in characters.
        height: Chart height in characters.

    Returns:
        Multi-line string with the visualization.
    """
    if end < start:
        start, end = end, start
    lines = []
    lines.append(color("bold", f"  Collatz Density Map: n ∈ [{start}, {end}]"))
    lines.append("")

    num_range = end - start + 1
    max_steps = max(collatz_steps(n) for n in range(start, end + 1))
    min_steps = min(collatz_steps(n) for n in range(start, end + 1))
    step_range = max_steps - min_steps if max_steps != min_steps else 1

    # Sample columns to fit width
    if num_range <= width:
        col_step = 1
        cols = num_range
    else:
        col_step = num_range / width
        cols = width

    # Build grid
    grid = [[' ' for _ in range(cols)] for _ in range(height)]
    density_chars = " ·:;=+*#%@"

    for ci in range(cols):
        if num_range <= width:
            n = start + ci
        else:
            n = start + int(ci * col_step)
        steps = collatz_steps(n)
        row = height - 1 - int((steps - min_steps) / step_range * (height - 1))
        row = max(0, min(height - 1, row))
        ch_idx = min(int((steps - min_steps) / step_range * (len(density_chars) - 1)), len(density_chars) - 1) if step_range > 0 else 0
        ch = density_chars[ch_idx]
        if steps <= min_steps + step_range * 0.25:
            ch = color("green", ch)
        elif steps <= min_steps + step_range * 0.5:
            ch = color("cyan", ch)
        elif steps <= min_steps + step_range * 0.75:
            ch = color("yellow", ch)
        else:
            ch = color("red", ch)
        grid[row][ci] = ch

    for r in range(height):
        val = int(min_steps + (height - 1 - r) / (height - 1) * step_range) if height > 1 and step_range > 0 else 0
        label = f"{val:>6}"
        line = f"  {label} │{''.join(grid[r])}"
        lines.append(line)

    lines.append(f"  {'':>6} └{'─' * min(cols, width)}")
    lines.append(f"  {'':>6}  {start}{str(end):>{min(cols, width) - len(str(start))}}")
    lines.append("")
    lines.append(color("dim", f"  X-axis: starting number ({start}–{end})"))
    lines.append(color("dim", f"  Y-axis: stopping time (steps to reach 1)"))

    return "\n".join(lines)


# ── Stats mode ────────────────────────────────────────────────────────────

def render_stats(n: int) -> str:
    """Render detailed statistics about the Collatz sequence for a single number.

    Args:
        n: Starting number.

    Returns:
        Multi-line string with statistics.
    """
    stats = collatz_stats(n)
    seq = collatz_sequence(n)

    lines = []
    lines.append(color("bold", f"  Collatz Statistics for n = {n:,}"))
    lines.append("")
    lines.append(f"  Starting value:     {n:,}")
    lines.append(f"  Steps to reach 1:   {stats['steps']:,}")
    lines.append(f"  Peak value:         {stats['peak']:,}")
    lines.append(f"  Growth factor:      {stats['growth_factor']:.1f}×")
    lines.append(f"  Odd operations:     {stats['odd_ops']:,}")
    lines.append(f"  Even operations:    {stats['even_ops']:,}")
    if stats['odd_even_ratio'] != float('inf'):
        lines.append(f"  Even/Odd ratio:    {stats['odd_even_ratio']:.2f}:1")
    else:
        lines.append(f"  Even/Odd ratio:    N/A (no odd operations)")
    lines.append("")

    # Distribution summary
    above_start = sum(1 for v in seq if v > n)
    at_one = sum(1 for v in seq if v == 1)
    lines.append(f"  Values above start: {above_start:,} / {len(seq):,} ({100*above_start/len(seq):.1f}%)")
    lines.append(f"  Times at 1:         {at_one:,} (always 1 at end)")
    lines.append("")

    # Show the path parity pattern (first 40 operations)
    ops = []
    for i in range(min(40, len(seq) - 1)):
        if seq[i] % 2 == 0:
            ops.append(color("cyan", "÷"))
        else:
            ops.append(color("yellow", "×"))
    pattern = " ".join(ops)
    if len(seq) - 1 > 40:
        pattern += color("dim", f" ... +{len(seq) - 1 - 40} more")
    lines.append(f"  Operation pattern:  {pattern}")
    lines.append(color("dim", f"  (÷ = even/halve, × = odd/triple+1)"))

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
        "7": ("Converge",   "Convergence speed heat map"),
        "8": ("Density",    "2D density map of stopping times"),
        "s": ("Stats",      "Detailed statistics for a number"),
    }

    while True:
        print()
        print(color("bold", "  Visualization modes:"))
        for key, (name, desc) in modes.items():
            print(f"    {color('cyan', key)}. {color('bold', name):<12} — {color('dim', desc)}")
        print(f"    {color('cyan', 'q')}. Quit")
        print()

        choice = input(color("bold", "  Choose mode [1-8/s/q]: ")).strip().lower()
        if choice == 'q' or choice == '':
            print(color("dim", "  Goodbye! May all your sequences reach 1."))
            break

        if choice not in modes:
            print(color("red", "  Invalid choice."))
            continue

        try:
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
            elif choice == "7":
                start = input("  Start of range (default 1): ").strip()
                start = int(start) if start else 1
                end = input("  End of range (default 50): ").strip()
                end = int(end) if end else 50
                if end - start > 100:
                    print(color("yellow", "  Clamping range to 100 for readability."))
                    end = start + 99
                print()
                print(render_converge(start, end))
            elif choice == "8":
                start = input("  Start of range (default 1): ").strip()
                start = int(start) if start else 1
                end = input("  End of range (default 50): ").strip()
                end = int(end) if end else 50
                if end - start > 100:
                    print(color("yellow", "  Clamping range to 100 for readability."))
                    end = start + 99
                print()
                print(render_density(start, end))
            elif choice == "s":
                n = input("  Number to analyze (default 27): ").strip()
                n = int(n) if n else 27
                print()
                print(render_stats(n))
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
        except ValueError as e:
            print(color("red", f"  Error: {e}"))
        except KeyboardInterrupt:
            print(color("dim", "\n  Interrupted."))


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
  %(prog)s -n 27 --mode stats        Detailed statistics for n=27
  %(prog)s --batch 1 30              Batch stats for range [1,30]
  %(prog)s --tree 1 --depth 10       Reverse tree from 1
  %(prog)s --converge 1 50           Convergence speed chart
  %(prog)s --density 1 50            Density map of stopping times
  %(prog)s --export output.txt -n 27 --mode hailstone   Save to file
        """
    )
    parser.add_argument("-n", "--number", type=int, default=None, help="Starting number (default: 27)")
    parser.add_argument("--mode", choices=["sequence", "path", "histogram", "tree", "batch", "hailstone", "converge", "density", "stats"],
                        default="hailstone", help="Visualization mode (default: hailstone)")
    parser.add_argument("--batch", nargs=2, type=int, metavar=("START", "END"), help="Batch mode: range of numbers")
    parser.add_argument("--tree", type=int, metavar="TARGET", help="Tree mode: target number")
    parser.add_argument("--converge", nargs=2, type=int, metavar=("START", "END"), help="Converge mode: range of numbers")
    parser.add_argument("--density", nargs=2, type=int, metavar=("START", "END"), help="Density mode: range of numbers")
    parser.add_argument("--depth", type=int, default=8, help="Tree depth (default: 8)")
    parser.add_argument("--width", type=int, default=70, help="Chart width (default: 70)")
    parser.add_argument("--height", type=int, default=22, help="Chart height (default: 22)")
    parser.add_argument("--bins", type=int, default=15, help="Histogram bins (default: 15)")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--export", metavar="FILE", help="Save output to a file instead of stdout")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    global _color_enabled
    if args.no_color or os.environ.get("NO_COLOR"):
        _color_enabled = False

    # Validate inputs early
    if args.number is not None and args.number < 1:
        parser.error("Starting number must be a positive integer")

    # Helper to output either to stdout or file
    def output(text):
        if args.export:
            with open(args.export, "a", encoding="utf-8") as f:
                f.write(text + "\n")
            print(f"  Output appended to {args.export}")
        else:
            print(text)

    # If no specific mode flags, run interactive
    if args.number is None and args.batch is None and args.tree is None and args.converge is None and args.density is None:
        try:
            interactive_mode()
        except (KeyboardInterrupt, EOFError):
            print(color("dim", "\n  Goodbye!"))
        return

    # Determine mode and render
    try:
        if args.batch:
            start, end = args.batch
            if end - start > 50:
                print("Clamping range to 50 numbers for readability.")
                end = start + 49
            output(render_batch(start, end, width=args.width))
        elif args.tree:
            output(render_tree(args.tree, depth=args.depth, width=args.width))
        elif args.converge:
            start, end = args.converge
            if end - start > 100:
                print("Clamping range to 100 for readability.")
                end = start + 99
            output(render_converge(start, end, width=args.width, height=args.height))
        elif args.density:
            start, end = args.density
            if end - start > 100:
                print("Clamping range to 100 for readability.")
                end = start + 99
            output(render_density(start, end, width=args.width, height=args.height))
        elif args.number:
            n = args.number
            if args.mode == "sequence":
                output(render_sequence(n))
            elif args.mode == "path":
                output(render_path(n, width=args.width))
            elif args.mode == "histogram":
                output(render_histogram(n, bins=args.bins, bar_width=args.width))
            elif args.mode == "hailstone":
                output(render_hailstone(n, width=args.width, height=args.height))
            elif args.mode == "stats":
                output(render_stats(n))
            elif args.mode == "converge":
                # Default range around n for converge mode with -n
                start = max(1, n - 10)
                end = n + 10
                output(render_converge(start, end, width=args.width, height=args.height))
            elif args.mode == "density":
                start = max(1, n - 10)
                end = n + 10
                output(render_density(start, end, width=args.width, height=args.height))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()