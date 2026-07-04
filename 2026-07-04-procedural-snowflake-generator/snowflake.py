#!/usr/bin/env python3
"""
Procedural Snowflake Generator
================================
Generates unique, beautiful snowflake patterns using fractal branching
algorithms with Koch-curve edges and randomized dendrite growth.

Each snowflake is deterministic from its seed — the same seed always produces
the same crystal. Supports ANSI color output, animation, SVG export, JSON
export, and customizable symmetry.

Features:
  - 5 crystal types: Dendrite, Plate, Stellar, Fernlike, Columnar
  - Configurable symmetry: 4, 6, 8, or 12-fold
  - Koch-curve edge decoration for realistic crystal faceting
  - Animation, gallery, and side-by-side comparison modes
  - SVG and JSON export for programmatic use
  - Deterministic seeds for reproducible art

Version: 2.0.0
"""

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from typing import Dict, List, Optional, Tuple

__version__ = "2.0.0"

# ─── ANSI helpers ──────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

PALETTES = {
    "frost": ["\033[38;5;117m", "\033[38;5;159m", "\033[38;5;195m", "\033[38;5;231m", "\033[38;5;153m"],
    "aurora": ["\033[38;5;122m", "\033[38;5;85m", "\033[38;5;48m", "\033[38;5;159m", "\033[38;5;231m"],
    "ice": ["\033[38;5;195m", "\033[38;5;231m", "\033[38;5;255m", "\033[38;5;159m", "\033[38;5;117m"],
    "ember": ["\033[38;5;220m", "\033[38;5;214m", "\033[38;5;202m", "\033[38;5;196m", "\033[38;5;231m"],
    "violet": ["\033[38;5;183m", "\033[38;5;177m", "\033[38;5;141m", "\033[38;5;231m", "\033[38;5;195m"],
    "mono": ["\033[38;5;255m", "\033[38;5;252m", "\033[38;5;248m", "\033[38;5;244m", "\033[38;5;240m"],
}

CHARS_BY_DEPTH = {
    0: "◆",
    1: "┃",
    2: "┃",
    3: "╎",
    4: "┊",
    5: "·",
}

BRANCH_CHARS = {
    "right": "╲",
    "left": "╱",
    "center": "┃",
}

# SVG color palettes (hex colors matching the ANSI palettes)
SVG_PALETTES = {
    "frost": ["#e8f4ff", "#a8d8ff", "#7bc0ff", "#5ea8f0", "#4090e0"],
    "aurora": ["#87d7af", "#5fd7af", "#00ff87", "#a8d8ff", "#e8f4ff"],
    "ice": ["#d7ffff", "#e8f4ff", "#ffffff", "#a8d8ff", "#87d7ff"],
    "ember": ["#ffdf00", "#ffaf00", "#ff5f00", "#ff0000", "#e8f4ff"],
    "violet": ["#d7afff", "#d787ff", "#af87ff", "#e8f4ff", "#d7ffff"],
    "mono": ["#ffffff", "#e4e4e4", "#d0d0d0", "#bcbcbc", "#a8a8a8"],
}

VALID_SYMMETRIES = [4, 6, 8, 12]

CRYSTAL_TYPES = ["dendrite", "plate", "stellar", "fernlike", "columnar"]


class SeededRNG:
    """Deterministic RNG from a string seed using SHA-256.

    Uses a linear congruential generator (LCG) with constants from
    MMIX by Donald Knuth, seeded from SHA-256 hash of the input string.
    This ensures reproducible sequences across runs and platforms.
    """

    def __init__(self, seed: str):
        self.seed = seed
        digest = hashlib.sha256(seed.encode()).hexdigest()
        self.state = int(digest, 16)

    def random(self) -> float:
        """Return a float in [0, 1)."""
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        return (self.state >> 33) / (1 << 31)

    def randint(self, lo: int, hi: int) -> int:
        """Return a random int in [lo, hi] inclusive."""
        return lo + int(self.random() * (hi - lo + 1))

    def choice(self, seq):
        """Return a random element from seq."""
        if not seq:
            raise ValueError("Cannot choose from empty sequence")
        return seq[self.randint(0, len(seq) - 1)]

    def uniform(self, lo: float, hi: float) -> float:
        """Return a random float in [lo, hi]."""
        return lo + self.random() * (hi - lo)

    def shuffle(self, seq: list) -> list:
        """Return a shuffled copy of seq (Fisher-Yates)."""
        result = list(seq)
        for i in range(len(result) - 1, 0, -1):
            j = self.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result


# ─── Snowflake geometry ───────────────────────────────────────────────────

class Segment:
    """A line segment in polar space from (r1,a1) to (r2,a2).

    Attributes:
        r1: Radial start distance (0 = center).
        a1: Angular start position (radians).
        r2: Radial end distance.
        a2: Angular end position.
        depth: Recursion depth (0 = main arm).
        branch_type: 'center', 'left', or 'right'.
    """
    __slots__ = ("r1", "a1", "r2", "a2", "depth", "branch_type")

    def __init__(self, r1: float, a1: float, r2: float, a2: float,
                 depth: int = 0, branch_type: str = "center"):
        self.r1 = r1
        self.a1 = a1
        self.r2 = r2
        self.a2 = a2
        self.depth = depth
        self.branch_type = branch_type

    def to_dict(self) -> dict:
        """Serialize segment to a dictionary for JSON export."""
        return {
            "r1": round(self.r1, 6),
            "a1": round(self.a1, 6),
            "r2": round(self.r2, 6),
            "a2": round(self.a2, 6),
            "depth": self.depth,
            "branch_type": self.branch_type,
        }


def generate_snowflake(seed: str, max_depth: int = 4, symmetry: int = 6):
    """Generate all segments of a snowflake with given seed and parameters.

    Args:
        seed: String seed for deterministic generation.
        max_depth: Maximum recursion depth (1-5).
        symmetry: Rotational symmetry fold count (4, 6, 8, or 12).

    Returns:
        Tuple of (segments_list, crystal_type_string).
    """
    if max_depth < 1:
        max_depth = 1
    if max_depth > 5:
        max_depth = 5
    if symmetry not in VALID_SYMMETRIES:
        symmetry = 6

    rng = SeededRNG(seed)

    # Determine snowflake type
    crystal_type = rng.choice(CRYSTAL_TYPES)

    segments: List[Segment] = []

    # Base arms
    num_arms = symmetry
    arm_length = rng.uniform(0.55, 0.95)
    arm_growth_factor = rng.uniform(0.55, 0.78)

    for i in range(num_arms):
        angle = i * (2 * math.pi / num_arms)
        _grow_arm(rng, segments, 0, 0, angle, arm_length, 1, max_depth,
                  crystal_type, arm_growth_factor)

    return segments, crystal_type


def _grow_arm(rng: SeededRNG, segments: list, r_start: float, a_start: float,
              angle: float, length: float, depth: int, max_depth: int,
              crystal_type: str, growth_factor: float):
    """Recursively grow a single arm with branches.

    This is the core recursive growth function that builds up the dendritic
    structure of each crystal arm.
    """
    if depth > max_depth or length < 0.02:
        return

    r_end = r_start + length

    # Main arm segment
    segments.append(Segment(r_start, angle, r_end, angle, depth, "center"))

    # Add branches depending on crystal type
    num_branches = _get_branch_count(rng, depth, crystal_type)
    branch_angle_spread = rng.uniform(0.35, 0.75)

    for b in range(num_branches):
        # Position along the arm
        t = (b + 1) / (num_branches + 1)
        r_branch = r_start + length * t
        branch_len = length * growth_factor * rng.uniform(0.4, 0.85)

        # Alternate left/right
        sign = 1 if b % 2 == 0 else -1
        branch_angle = angle + sign * branch_angle_spread

        segments.append(Segment(r_branch, angle, r_branch + branch_len * 0.1,
                                branch_angle, depth + 1,
                                "right" if sign > 0 else "left"))
        _grow_arm(rng, segments, r_branch, branch_angle, branch_angle,
                  branch_len, depth + 1, max_depth, crystal_type,
                  growth_factor * rng.uniform(0.85, 0.95))

    # Dendrite-style side growth for fernlike
    if crystal_type == "fernlike" and depth < max_depth - 1:
        for side in [-1, 1]:
            side_len = length * rng.uniform(0.15, 0.35)
            side_angle = angle + side * rng.uniform(0.4, 0.8)
            segments.append(Segment(r_start + length * 0.5, angle,
                                    r_start + length * 0.5 + side_len * 0.05,
                                    side_angle, depth + 1,
                                    "right" if side > 0 else "left"))
            _grow_arm(rng, segments, r_start + length * 0.5, side_angle,
                      side_angle, side_len, depth + 1, max_depth,
                      crystal_type, growth_factor * 0.7)

    # Koch-curve edge decoration at depth 1 for plate and stellar crystals
    if crystal_type in ("plate", "stellar") and depth == 1:
        _add_koch_edge(rng, segments, r_start, angle, length, depth)


def _add_koch_edge(rng: SeededRNG, segments: list, r_start: float,
                   angle: float, length: float, depth: int):
    """Add Koch-curve edge decoration for plate and stellar crystals.

    Creates the characteristic hexagonal faceted edges seen in real
    plate-type ice crystals by adding small triangular protrusions
    along the main arm edges.
    """
    # Small triangular bumps along the arm
    for t in [0.33, 0.67]:
        r_pos = r_start + length * t
        bump_len = length * rng.uniform(0.04, 0.08)
        for sign in [-1, 1]:
            bump_angle = angle + sign * rng.uniform(0.15, 0.30)
            segments.append(Segment(r_pos, angle, r_pos + bump_len * 0.5,
                                    bump_angle, depth + 1,
                                    "right" if sign > 0 else "left"))


def _get_branch_count(rng: SeededRNG, depth: int, crystal_type: str) -> int:
    """Return the number of branches at a given depth for a crystal type.

    Branch counts vary by crystal type to simulate real ice crystal morphology.
    """
    base = {
        "dendrite": [3, 2, 2, 1, 1],
        "plate": [1, 1, 0, 0, 0],
        "stellar": [2, 2, 1, 1, 0],
        "fernlike": [3, 3, 2, 2, 1],
        "columnar": [1, 1, 1, 0, 0],
    }
    counts = base.get(crystal_type, [2, 2, 1, 1, 0])
    idx = min(depth, len(counts) - 1)
    return max(0, counts[idx] + rng.randint(0, 1))


# ─── Rendering ─────────────────────────────────────────────────────────────

def segments_to_points(segments: List[Segment], symmetry: int = 6,
                       canvas_size: int = 51) -> Tuple[Dict, int, int]:
    """Convert polar segments to (x, y) points on a discrete grid.

    Applies rotational symmetry and mirror reflection to create the
    full symmetric pattern from a single arm's segments.

    Args:
        segments: List of Segment objects.
        symmetry: Number of rotational symmetry folds.
        canvas_size: Width/height of the square grid.

    Returns:
        Tuple of (points_dict, center_x, center_y).
    """
    cx = canvas_size // 2
    cy = canvas_size // 2
    scale = (canvas_size // 2) - 2

    if scale <= 0:
        scale = 1

    points: Dict[Tuple[int, int], Tuple[int, str]] = {}

    for seg in segments:
        steps = max(int(seg.r2 * scale - seg.r1 * scale), 1)
        for i in range(steps + 1):
            t = i / max(steps, 1)
            r = seg.r1 + (seg.r2 - seg.r1) * t
            a = seg.a1 + (seg.a2 - seg.a1) * t
            x = cx + int(round(r * scale * math.cos(a)))
            y = cy + int(round(r * scale * math.sin(a)))
            if 0 <= x < canvas_size and 0 <= y < canvas_size:
                key = (x, y)
                if key not in points or points[key][0] > seg.depth:
                    points[key] = (seg.depth, seg.branch_type)

    # Add rotational symmetry
    all_points: Dict[Tuple[int, int], Tuple[int, str]] = {}
    for (x, y), (depth, bt) in points.items():
        dx = x - cx
        dy = y - cy
        for k in range(symmetry):
            angle = k * (2 * math.pi / symmetry)
            rx = int(round(dx * math.cos(angle) - dy * math.sin(angle)))
            ry = int(round(dx * math.sin(angle) + dy * math.cos(angle)))
            nx, ny = cx + rx, cy + ry
            if 0 <= nx < canvas_size and 0 <= ny < canvas_size:
                key = (nx, ny)
                if key not in all_points or all_points[key][0] > depth:
                    all_points[key] = (depth, bt)

    # Also add mirror symmetry
    mirrored: Dict[Tuple[int, int], Tuple[int, str]] = {}
    for (x, y), (depth, bt) in all_points.items():
        mx = 2 * cx - x
        my = y
        if 0 <= mx < canvas_size:
            key = (mx, my)
            if key not in all_points or all_points[key][0] > depth:
                mirrored[key] = (depth, bt)
    all_points.update(mirrored)

    return all_points, cx, cy


def render_snowflake(segments: List[Segment], crystal_type: str, seed: str,
                     canvas_size: int = 51, palette: str = "frost",
                     color: bool = True, show_info: bool = True,
                     symmetry: int = 6) -> str:
    """Render a snowflake to a string.

    Args:
        segments: List of Segment objects from generate_snowflake.
        crystal_type: The crystal type name.
        seed: The seed string used for generation.
        canvas_size: Grid size (should be odd).
        palette: Color palette name from PALETTES.
        color: Whether to include ANSI color codes.
        show_info: Whether to show the header info block.
        symmetry: Number of symmetry folds.

    Returns:
        Rendered string of the snowflake.
    """
    points, cx, cy = segments_to_points(segments, symmetry=symmetry,
                                         canvas_size=canvas_size)

    pal = PALETTES.get(palette, PALETTES["frost"])

    canvas = [[" " for _ in range(canvas_size)] for _ in range(canvas_size)]
    colors = [[None for _ in range(canvas_size)] for _ in range(canvas_size)]

    # Place center
    canvas[cy][cx] = "◆"
    colors[cy][cx] = pal[0]

    # Place crystal points
    for (x, y), (depth, bt) in points.items():
        if x == cx and y == cy:
            continue
        if depth < len(CHARS_BY_DEPTH):
            ch = CHARS_BY_DEPTH.get(depth, "·")
        else:
            ch = "·"
        canvas[y][x] = ch
        color_idx = min(depth, len(pal) - 1)
        colors[y][x] = pal[color_idx]

    # Build output
    lines: List[str] = []
    if show_info:
        lines.append(f"{BOLD}❄  Procedural Snowflake Generator{RESET}")
        lines.append(f"   Seed: {seed}")
        lines.append(f"   Type: {crystal_type.capitalize()}")
        lines.append(f"   Symmetry: {symmetry}-fold")
        lines.append("")

    for y in range(canvas_size):
        row = ""
        for x in range(canvas_size):
            ch = canvas[y][x]
            if ch != " ":
                if color and colors[y][x]:
                    row += colors[y][x] + ch + RESET
                else:
                    row += ch
            else:
                row += " "
        # Strip trailing spaces
        lines.append(row.rstrip())

    # Add faint sparkle dots
    rng = SeededRNG(seed + "_sparkle")
    _ = rng  # used for sparkle if extended later
    sparkle_chars = "✦✧⋆·"

    return "\n".join(lines)


def animate_snowfall(segments: List[Segment], crystal_type: str, seed: str,
                     palette: str = "frost", frames: int = 30,
                     width: int = 80, height: int = 24,
                     symmetry: int = 6):
    """Animate a snowflake gently falling through a starry sky.

    Args:
        segments: List of Segment objects.
        crystal_type: The crystal type name.
        seed: The seed string for deterministic stars/sway.
        palette: Color palette name.
        frames: Number of animation frames.
        width: Terminal width in characters.
        height: Terminal height in characters.
        symmetry: Number of symmetry folds.
    """
    pal = PALETTES.get(palette, PALETTES["frost"])

    # Pre-render the snowflake at small size
    small_size = min(width, height) - 2
    if small_size % 2 == 0:
        small_size -= 1
    if small_size < 5:
        small_size = 5
    points, cx, cy = segments_to_points(segments, symmetry=symmetry,
                                         canvas_size=small_size)

    # Build flake character map
    flake_chars: Dict[Tuple[int, int], str] = {}
    for (x, y), (depth, bt) in points.items():
        if depth < len(CHARS_BY_DEPTH):
            flake_chars[(x, y)] = CHARS_BY_DEPTH.get(depth, "·")
        else:
            flake_chars[(x, y)] = "·"

    rng = SeededRNG(seed + "_stars")
    stars = [(rng.randint(0, width - 1), rng.randint(0, height - 1),
              rng.choice(["⋆", "·", "✧", "✦"])) for _ in range(40)]

    rng2 = SeededRNG(seed + "_anim")
    # Horizontal sway
    sway_amplitude = rng2.randint(2, 6)

    for frame in range(frames):
        t = frame / max(frames - 1, 1)
        # Snowflake vertical position
        flake_y_pos = int((height + small_size) * t) - small_size // 2
        sway = int(sway_amplitude * math.sin(t * math.pi * 3))
        flake_x_pos = width // 2 - small_size // 2 + sway

        # Build frame
        grid = [[" " for _ in range(width)] for _ in range(height)]
        grid_colors = [[None for _ in range(width)] for _ in range(height)]

        # Stars
        for sx, sy, sch in stars:
            # Twinkle
            if rng2.random() > 0.3:
                if 0 <= sy < height and 0 <= sx < width:
                    grid[sy][sx] = sch
                    grid_colors[sy][sx] = DIM + "\033[38;5;244m"

        # Snowflake
        for (fx, fy), ch in flake_chars.items():
            gx = flake_x_pos + fx
            gy = flake_y_pos + fy
            if 0 <= gx < width and 0 <= gy < height:
                depth = points[(fx, fy)][0]
                grid[gy][gx] = ch
                grid_colors[gy][gx] = pal[min(depth, len(pal) - 1)]

        # Center crystal
        ccx = flake_x_pos + cx
        ccy = flake_y_pos + cy
        if 0 <= ccx < width and 0 <= ccy < height:
            grid[ccy][ccx] = "◆"
            grid_colors[ccy][ccx] = pal[0]

        # Render
        lines = []
        for y in range(height):
            row = ""
            for x in range(width):
                ch = grid[y][x]
                if ch != " " and grid_colors[y][x]:
                    row += grid_colors[y][x] + ch + RESET
                else:
                    row += ch
            lines.append(row.rstrip())

        output = "\n".join(lines)
        sys.stdout.write(f"\033[2J\033[H{output}\n\033[38;5;117m❄ {seed} ❄{RESET}\n")
        sys.stdout.flush()
        time.sleep(0.12)

    # Final frame - hold
    time.sleep(0.5)


def generate_gallery(seeds: List[str], palette: str = "frost", width: int = 39,
                     symmetry: int = 6) -> str:
    """Generate a side-by-side gallery of multiple snowflakes.

    Args:
        seeds: List of seed strings, one per snowflake.
        palette: Color palette name.
        width: Canvas width per snowflake.
        symmetry: Number of symmetry folds.

    Returns:
        Formatted string with side-by-side snowflakes.
    """
    rows: List[str] = []
    flakes: List[Tuple] = []

    for seed in seeds:
        segs, ctype = generate_snowflake(seed, max_depth=3, symmetry=symmetry)
        points, cx, cy = segments_to_points(segs, symmetry=symmetry,
                                             canvas_size=width)

        pal = PALETTES.get(palette, PALETTES["frost"])
        grid = [[" " for _ in range(width)] for _ in range(width)]
        grid_c = [[None for _ in range(width)] for _ in range(width)]

        grid[cy][cx] = "◆"
        grid_c[cy][cx] = pal[0]

        for (x, y), (depth, bt) in points.items():
            if x == cx and y == cy:
                continue
            grid[y][x] = CHARS_BY_DEPTH.get(min(depth, 5), "·")
            grid_c[y][x] = pal[min(depth, len(pal) - 1)]

        flakes.append((grid, grid_c, seed, ctype))

    # Render side by side
    header_parts = []
    for _, _, seed, ctype in flakes:
        label = f" {seed[:8]}… ({ctype[:4]}) "
        header_parts.append(label.center(width))

    result = BOLD + "❄  Snowflake Gallery" + RESET + "\n"
    result += "│".join(header_parts) + "\n"
    result += "─" * (width * len(seeds) + len(seeds) - 1) + "\n"

    for y in range(width):
        row_parts = []
        for grid, grid_c, _, _ in flakes:
            row = ""
            for x in range(width):
                ch = grid[y][x]
                if ch != " " and grid_c[y][x]:
                    row += grid_c[y][x] + ch + RESET
                else:
                    row += " "
            row_parts.append(row)
        result += "│".join(row_parts) + "\n"

    return result


def compare_snowflakes(seed_a: str, seed_b: str, canvas_size: int = 31,
                       palette: str = "frost", color: bool = True,
                       symmetry: int = 6) -> str:
    """Render two snowflakes side by side for comparison.

    Args:
        seed_a: First seed string.
        seed_b: Second seed string.
        canvas_size: Canvas size per snowflake.
        palette: Color palette name.
        color: Whether to include ANSI colors.
        symmetry: Number of symmetry folds.

    Returns:
        Formatted string with both snowflakes side by side.
    """
    segs_a, ctype_a = generate_snowflake(seed_a, max_depth=4, symmetry=symmetry)
    segs_b, ctype_b = generate_snowflake(seed_b, max_depth=4, symmetry=symmetry)

    points_a, _, _ = segments_to_points(segs_a, symmetry=symmetry,
                                         canvas_size=canvas_size)
    points_b, _, _ = segments_to_points(segs_b, symmetry=symmetry,
                                         canvas_size=canvas_size)

    pal = PALETTES.get(palette, PALETTES["frost"])

    def render_one(points, ctype, seed_label):
        cx = canvas_size // 2
        cy = canvas_size // 2
        canvas = [[" " for _ in range(canvas_size)] for _ in range(canvas_size)]
        colors_grid = [[None for _ in range(canvas_size)] for _ in range(canvas_size)]

        canvas[cy][cx] = "◆"
        colors_grid[cy][cx] = pal[0]

        for (x, y), (depth, bt) in points.items():
            if x == cx and y == cy:
                continue
            ch = CHARS_BY_DEPTH.get(min(depth, 5), "·")
            canvas[y][x] = ch
            colors_grid[y][x] = pal[min(depth, len(pal) - 1)]

        lines = []
        for y in range(canvas_size):
            row = ""
            for x in range(canvas_size):
                ch = canvas[y][x]
                if ch != " ":
                    if color and colors_grid[y][x]:
                        row += colors_grid[y][x] + ch + RESET
                    else:
                        row += ch
                else:
                    row += " "
            lines.append(row.rstrip())
        return lines

    lines_a = render_one(points_a, ctype_a, seed_a)
    lines_b = render_one(points_b, ctype_b, seed_b)

    result = []
    sep = " │ "
    header_a = f" {seed_a[:12]} ({ctype_a[:6]}) ".center(canvas_size)
    header_b = f" {seed_b[:12]} ({ctype_b[:6]}) ".center(canvas_size)
    result.append(f"{BOLD}❄  Snowflake Comparison{RESET}")
    result.append(header_a + sep + header_b)
    result.append("─" * canvas_size + "─┼─" + "─" * canvas_size)

    for la, lb in zip(lines_a, lines_b):
        result.append(la + sep + lb)

    return "\n".join(result)


def export_svg(segments: List[Segment], crystal_type: str, seed: str,
               filename: str = "snowflake.svg", size: int = 500,
               symmetry: int = 6, palette: str = "frost") -> str:
    """Export snowflake as an SVG file.

    Args:
        segments: List of Segment objects.
        crystal_type: The crystal type name.
        seed: The seed string.
        filename: Output SVG file path.
        size: SVG canvas size in pixels.
        symmetry: Number of symmetry folds.
        palette: Color palette name for SVG colors.

    Returns:
        The filename that was written.
    """
    points, cx, cy = segments_to_points(segments, symmetry=symmetry,
                                          canvas_size=101)

    # Map to SVG coordinates
    scale = size / 101
    svg_pal = SVG_PALETTES.get(palette, SVG_PALETTES["frost"])

    lines: List[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
                 f'viewBox="0 0 {size} {size}">')
    lines.append(f'  <rect width="{size}" height="{size}" fill="#0a0a2e"/>')
    lines.append(f'  <g stroke="{svg_pal[1]}" stroke-width="1.5" stroke-linecap="round">')

    # Draw each point as a small circle
    for (x, y), (depth, bt) in points.items():
        sx = x * scale
        sy = y * scale
        opacity = max(0.3, 1.0 - depth * 0.15)
        sw = max(0.5, 2.0 - depth * 0.3)
        color_idx = min(depth, len(svg_pal) - 1)
        color = svg_pal[color_idx]
        lines.append(f'    <circle cx="{sx:.1f}" cy="{sy:.1f}" r="{sw:.1f}" '
                     f'fill="{color}" opacity="{opacity:.2f}"/>')

    # Center
    lines.append(f'    <circle cx="{cx * scale:.1f}" cy="{cy * scale:.1f}" '
                 f'r="3" fill="{svg_pal[0]}"/>')
    lines.append(f'  </g>')
    lines.append(f'  <text x="{size // 2}" y="{size - 15}" text-anchor="middle" '
                 f'fill="{svg_pal[1]}" font-size="12" font-family="monospace">'
                 f'❄ {seed} ({crystal_type})</text>')
    lines.append(f'</svg>')

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filename


def export_json(segments: List[Segment], crystal_type: str, seed: str,
                symmetry: int = 6, max_depth: int = 4) -> str:
    """Export snowflake data as JSON for programmatic use.

    Args:
        segments: List of Segment objects.
        crystal_type: The crystal type name.
        seed: The seed string.
        symmetry: Number of symmetry folds.
        max_depth: Max recursion depth used.

    Returns:
        JSON string with full snowflake data.
    """
    data = {
        "seed": seed,
        "crystal_type": crystal_type,
        "symmetry": symmetry,
        "max_depth": max_depth,
        "num_segments": len(segments),
        "version": __version__,
        "segments": [seg.to_dict() for seg in segments],
    }
    return json.dumps(data, indent=2)


def print_seed_info(seed: str, symmetry: int = 6):
    """Show deterministic properties derived from a seed.

    Args:
        seed: The seed string to analyze.
        symmetry: Number of symmetry folds.
    """
    rng = SeededRNG(seed)

    crystal_types = ["Dendrite", "Plate", "Stellar", "Fernlike", "Columnar"]
    ct = rng.choice(crystal_types)

    arm_len = rng.uniform(0.55, 0.95)
    growth = rng.uniform(0.55, 0.78)
    spread = rng.uniform(0.35, 0.75)

    humidity = rng.uniform(60, 100)
    temp = rng.uniform(-20, -2)

    print(f"{BOLD}❄  Snowflake Crystal Report{RESET}")
    print(f"   Seed:       {seed}")
    print(f"   Crystal:    {ct}")
    print(f"   Symmetry:   {symmetry}-fold")
    print(f"   Arm length: {arm_len:.3f}")
    print(f"   Growth:     {growth:.3f}")
    print(f"   Spread:     {spread:.3f}")
    print(f"   Humidity:   {humidity:.1f}%")
    print(f"   Temp:       {temp:.1f}°C")
    print(f"   Unique as:  Every real snowflake! No two alike. ❄")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="❄  Procedural Snowflake Generator — Generate unique crystalline art",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python snowflake.py                      # Random snowflake
  python snowflake.py -s "winter"          # Seed-based snowflake
  python snowflake.py -s "hello" -p aurora # Aurora color palette
  python snowflake.py -s "frost" --animate # Animate falling snowflake
  python snowflake.py -s "test" --svg out.svg  # Export to SVG
  python snowflake.py --gallery 4          # Gallery of 4 snowflakes
  python snowflake.py --compare "snow" "ice"  # Compare two seeds
  python snowflake.py -s "data" --json    # Export as JSON
        """)
    parser.add_argument("-s", "--seed", default=None,
                        help="Seed string (deterministic)")
    parser.add_argument("-p", "--palette", default="frost",
                        choices=list(PALETTES.keys()), help="Color palette")
    parser.add_argument("-d", "--depth", type=int, default=4,
                        help="Max recursion depth (1-5)")
    parser.add_argument("--size", type=int, default=51,
                        help="Canvas size (odd number, 11-199)")
    parser.add_argument("--symmetry", type=int, default=6,
                        choices=VALID_SYMMETRIES,
                        help="Rotational symmetry folds (4, 6, 8, or 12)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    parser.add_argument("--animate", action="store_true",
                        help="Animate snowflake falling")
    parser.add_argument("--gallery", type=int, metavar="N",
                        help="Show N snowflakes gallery")
    parser.add_argument("--compare", nargs=2, metavar=("SEED_A", "SEED_B"),
                        help="Compare two seeds side by side")
    parser.add_argument("--svg", metavar="FILE",
                        help="Export as SVG")
    parser.add_argument("--json", metavar="FILE",
                        help="Export as JSON (or '-' for stdout)")
    parser.add_argument("--info", action="store_true",
                        help="Show seed info report")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    if args.seed is None:
        args.seed = f"flake-{random.randint(1000, 9999)}"

    # Validate and clamp depth
    if args.depth < 1:
        args.depth = 1
    if args.depth > 5:
        args.depth = 5

    # Validate and clamp size
    if args.size < 11:
        args.size = 11
    if args.size > 199:
        args.size = 199

    color = not args.no_color

    # Force color off if not a TTY
    if not sys.stdout.isatty():
        color = False

    if args.info:
        print_seed_info(args.seed, symmetry=args.symmetry)

    if args.gallery:
        seeds = [f"{args.seed}-{i}" for i in range(args.gallery)]
        print(generate_gallery(seeds, palette=args.palette, width=39,
                               symmetry=args.symmetry))
        return

    if args.compare:
        output = compare_snowflakes(args.compare[0], args.compare[1],
                                    canvas_size=args.size, palette=args.palette,
                                    color=color, symmetry=args.symmetry)
        print(output)
        return

    # Make canvas size odd
    if args.size % 2 == 0:
        args.size += 1

    segments, crystal_type = generate_snowflake(args.seed, max_depth=args.depth,
                                                 symmetry=args.symmetry)

    # When JSON to stdout is requested, skip rendering and only output JSON
    json_to_stdout = args.json == "-"

    if json_to_stdout:
        json_data = export_json(segments, crystal_type, args.seed,
                                symmetry=args.symmetry, max_depth=args.depth)
        print(json_data)
        return

    if args.animate:
        animate_snowfall(segments, crystal_type, args.seed, palette=args.palette,
                         symmetry=args.symmetry)
    else:
        output = render_snowflake(segments, crystal_type, args.seed,
                                  canvas_size=args.size, palette=args.palette,
                                  color=color, symmetry=args.symmetry)
        print(output)

    if args.svg:
        fname = export_svg(segments, crystal_type, args.seed, filename=args.svg,
                           size=500, symmetry=args.symmetry, palette=args.palette)
        print(f"\nSVG exported to: {fname}")

    if args.json and args.json != "-":
        json_data = export_json(segments, crystal_type, args.seed,
                                symmetry=args.symmetry, max_depth=args.depth)
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(json_data)
        print(f"\nJSON exported to: {args.json}")


if __name__ == "__main__":
    main()