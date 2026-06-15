#!/usr/bin/env python3
"""
Terminal Mondrian Art Generator
================================
Recursively subdivides a canvas into rectangles and fills them with
primary colors in the style of Piet Mondrian's iconic compositions.
Renders using Unicode box-drawing characters and ANSI true-color escapes.

Supports multiple palettes, animation mode, and SVG/HTML export.

Version: 2.1.0
"""

import random
import sys
import os
import argparse
import math
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

__version__ = "2.1.0"

# ── ANSI helpers ──────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_SCREEN = "\033[2J\033[H"
SAVE_CURSOR = "\033[s"
RESTORE_CURSOR = "\033[u"

def fg_color(r: int, g: int, b: int) -> str:
    """Return ANSI 24-bit foreground color escape sequence."""
    return f"\033[38;2;{r};{g};{b}m"

def bg_color(r: int, g: int, b: int) -> str:
    """Return ANSI 24-bit background color escape sequence."""
    return f"\033[48;2;{r};{g};{b}m"

# ── Mondrian palettes ────────────────────────────────────────────────────

PALETTES = {
    "classic": {
        "red":     (206,  32,  41),
        "blue":    (  0,  54, 170),
        "yellow":  (255, 222,   0),
        "white":   (242, 242, 242),
        "black":   ( 20,  20,  20),
    },
    "neon": {
        "red":     (255,   0, 102),
        "blue":    (  0, 200, 255),
        "yellow":  (255, 255,   0),
        "white":   (230, 230, 230),
        "black":   ( 10,  10,  10),
    },
    "pastel": {
        "red":     (240, 128, 128),
        "blue":    (135, 186, 240),
        "yellow":  (255, 243, 176),
        "white":   (250, 250, 250),
        "black":   ( 80,  80,  80),
    },
    "seventies": {
        "red":     (180,  60,  50),
        "blue":    ( 40,  70, 140),
        "yellow":  (220, 190,  60),
        "white":   (230, 220, 210),
        "black":   ( 30,  30,  30),
    },
    "dark": {
        "red":     (220,  50,  50),
        "blue":    ( 30,  80, 220),
        "yellow":  (240, 200,  40),
        "white":   ( 40,  42,  54),
        "black":   (  0,   0,   0),
    },
}

# Default palette name
DEFAULT_PALETTE = "classic"

# Fill probability weights — more white = more authentic Mondrian feel
FILL_CHOICES = ["red", "blue", "yellow", "white", "white", "white", "white"]

# ── Data structures ───────────────────────────────────────────────────────

@dataclass
class Rect:
    """A rectangular region defined by top-left corner and dimensions."""
    x: int
    y: int
    w: int
    h: int

@dataclass
class Cell:
    """A single character cell in the canvas with foreground/background colors."""
    char: str = " "
    bg: Tuple[int, int, int] = (242, 242, 242)
    fg: Tuple[int, int, int] = (0, 0, 0)

@dataclass
class MondrianCanvas:
    """A 2D grid of cells representing the Mondrian composition."""
    width: int
    height: int
    cells: List[List[Cell]] = field(default_factory=list)

    def __post_init__(self):
        if self.width < 1 or self.height < 1:
            raise ValueError(f"Canvas dimensions must be >= 1, got {self.width}x{self.height}")
        self.cells = [
            [Cell() for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def fill_rect(self, rect: Rect, color_name: str, palette: dict):
        """Fill a rectangular region with a named color from the palette."""
        r, g, b = palette[color_name]
        for row in range(rect.y, rect.y + rect.h):
            for col in range(rect.x, rect.x + rect.w):
                if 0 <= row < self.height and 0 <= col < self.width:
                    self.cells[row][col].bg = (r, g, b)

    def draw_hline(self, y: int, x1: int, x2: int, palette: dict):
        """Draw a horizontal line segment on the canvas."""
        border_color = palette["black"]
        for x in range(x1, x2 + 1):
            if 0 <= y < self.height and 0 <= x < self.width:
                self.cells[y][x].char = "─"
                self.cells[y][x].fg = border_color

    def draw_vline(self, x: int, y1: int, y2: int, palette: dict):
        """Draw a vertical line segment on the canvas."""
        border_color = palette["black"]
        for y in range(y1, y2 + 1):
            if 0 <= y < self.height and 0 <= x < self.width:
                self.cells[y][x].char = "│"
                self.cells[y][x].fg = border_color

# ── Recursive subdivision ─────────────────────────────────────────────────

BORDER_W = 2  # 2-char thick borders for Mondrian feel

def subdivide(canvas: MondrianCanvas, rect: Rect, depth: int, max_depth: int,
              min_size: int, split_prob: float, palette: dict):
    """Recursively subdivide a rectangle and fill leaf regions with colors."""

    border_color = palette["black"]

    # Decide whether to split
    too_small = rect.w < min_size * 2 + BORDER_W or rect.h < min_size * 2 + BORDER_W
    too_deep = depth >= max_depth
    should_split = (not too_small) and (not too_deep) and (random.random() < split_prob)

    if not should_split:
        # Leaf node — fill with a color
        fill = random.choice(FILL_CHOICES)
        # Inset by border width
        inner = Rect(
            rect.x + BORDER_W,
            rect.y + BORDER_W,
            rect.w - 2 * BORDER_W,
            rect.h - 2 * BORDER_W,
        )
        if inner.w > 0 and inner.h > 0:
            canvas.fill_rect(inner, fill, palette)
        return

    # Choose split direction
    can_split_h = rect.h >= min_size * 2 + BORDER_W
    can_split_v = rect.w >= min_size * 2 + BORDER_W

    if can_split_h and can_split_v:
        # Prefer the longer axis for balanced compositions
        if rect.w > rect.h * 1.3:
            direction = "vertical"
        elif rect.h > rect.w * 1.3:
            direction = "horizontal"
        else:
            direction = random.choice(["horizontal", "vertical"])
    elif can_split_h:
        direction = "horizontal"
    elif can_split_v:
        direction = "vertical"
    else:
        # Can't split further
        fill = random.choice(FILL_CHOICES)
        inner = Rect(rect.x + BORDER_W, rect.y + BORDER_W,
                     rect.w - 2 * BORDER_W, rect.h - 2 * BORDER_W)
        if inner.w > 0 and inner.h > 0:
            canvas.fill_rect(inner, fill, palette)
        return

    if direction == "horizontal":
        # Split horizontally (top/bottom)
        min_pos = rect.y + BORDER_W + min_size
        max_pos = rect.y + rect.h - BORDER_W - min_size - BORDER_W
        if min_pos >= max_pos:
            fill = random.choice(FILL_CHOICES)
            inner = Rect(rect.x + BORDER_W, rect.y + BORDER_W,
                         rect.w - 2 * BORDER_W, rect.h - 2 * BORDER_W)
            if inner.w > 0 and inner.h > 0:
                canvas.fill_rect(inner, fill, palette)
            return
        split_y = random.randint(min_pos, max_pos)

        # Draw horizontal border at split_y..split_y+BORDER_W-1
        for dy in range(BORDER_W):
            for x in range(rect.x, rect.x + rect.w):
                if 0 <= split_y + dy < canvas.height and 0 <= x < canvas.width:
                    canvas.cells[split_y + dy][x].char = "─"
                    canvas.cells[split_y + dy][x].fg = border_color
                    canvas.cells[split_y + dy][x].bg = border_color

        top = Rect(rect.x, rect.y, rect.w, split_y - rect.y)
        bottom = Rect(rect.x, split_y + BORDER_W, rect.w,
                      rect.y + rect.h - split_y - BORDER_W)
        subdivide(canvas, top, depth + 1, max_depth, min_size, split_prob, palette)
        subdivide(canvas, bottom, depth + 1, max_depth, min_size, split_prob, palette)

    else:
        # Split vertically (left/right)
        min_pos = rect.x + BORDER_W + min_size
        max_pos = rect.x + rect.w - BORDER_W - min_size - BORDER_W
        if min_pos >= max_pos:
            fill = random.choice(FILL_CHOICES)
            inner = Rect(rect.x + BORDER_W, rect.y + BORDER_W,
                         rect.w - 2 * BORDER_W, rect.h - 2 * BORDER_W)
            if inner.w > 0 and inner.h > 0:
                canvas.fill_rect(inner, fill, palette)
            return
        split_x = random.randint(min_pos, max_pos)

        # Draw vertical border
        for dx in range(BORDER_W):
            for y in range(rect.y, rect.y + rect.h):
                if 0 <= y < canvas.height and 0 <= split_x + dx < canvas.width:
                    canvas.cells[y][split_x + dx].char = "│"
                    canvas.cells[y][split_x + dx].fg = border_color
                    canvas.cells[y][split_x + dx].bg = border_color

        left = Rect(rect.x, rect.y, split_x - rect.x, rect.h)
        right = Rect(split_x + BORDER_W, rect.y,
                     rect.x + rect.w - split_x - BORDER_W, rect.h)
        subdivide(canvas, left, depth + 1, max_depth, min_size, split_prob, palette)
        subdivide(canvas, right, depth + 1, max_depth, min_size, split_prob, palette)


def fix_intersections(canvas: MondrianCanvas, palette: dict):
    """Second pass: wherever ─ and │ cross, place the correct box-drawing char."""
    border_color = palette["black"]

    for y in range(canvas.height):
        for x in range(canvas.width):
            cell = canvas.cells[y][x]
            # Check if this cell is part of a border (has black fg/bg)
            if cell.fg != border_color and cell.bg != border_color:
                continue

            is_h = cell.char == "─"
            is_v = cell.char == "│"

            # Check neighbors
            has_up = y > 0 and canvas.cells[y-1][x].char == "│"
            has_down = y < canvas.height - 1 and canvas.cells[y+1][x].char == "│"
            has_left = x > 0 and canvas.cells[y][x-1].char == "─"
            has_right = x < canvas.width - 1 and canvas.cells[y][x+1].char == "─"

            # Also check 2-wide borders
            if not has_up and y > 1 and canvas.cells[y-2][x].char == "│":
                has_up = True
            if not has_down and y < canvas.height - 2 and canvas.cells[y+2][x].char == "│":
                has_down = True
            if not has_left and x > 1 and canvas.cells[y][x-2].char == "─":
                has_left = True
            if not has_right and x < canvas.width - 2 and canvas.cells[y][x+2].char == "─":
                has_right = True

            if is_h and has_up and has_down:
                cell.char = "┼"
            elif is_h and has_up:
                cell.char = "┴"
            elif is_h and has_down:
                cell.char = "┬"
            elif is_v and has_left and has_right:
                cell.char = "┼"
            elif is_v and has_left:
                cell.char = "┤"
            elif is_v and has_right:
                cell.char = "├"


def draw_outer_border(canvas: MondrianCanvas, palette: dict):
    """Draw a thick border around the entire canvas."""
    border_color = palette["black"]

    for x in range(canvas.width):
        for bw in range(BORDER_W):
            canvas.cells[bw][x].char = "─"
            canvas.cells[bw][x].fg = border_color
            canvas.cells[bw][x].bg = border_color
            canvas.cells[canvas.height - 1 - bw][x].char = "─"
            canvas.cells[canvas.height - 1 - bw][x].fg = border_color
            canvas.cells[canvas.height - 1 - bw][x].bg = border_color
    for y in range(canvas.height):
        for bw in range(BORDER_W):
            canvas.cells[y][bw].char = "│"
            canvas.cells[y][bw].fg = border_color
            canvas.cells[y][bw].bg = border_color
            canvas.cells[y][canvas.width - 1 - bw].char = "│"
            canvas.cells[y][canvas.width - 1 - bw].fg = border_color
            canvas.cells[y][canvas.width - 1 - bw].bg = border_color

    # Corner intersections
    for by in range(BORDER_W):
        for bx in range(BORDER_W):
            canvas.cells[by][bx].char = "┼"
            canvas.cells[by][canvas.width - 1 - bx].char = "┼"
            canvas.cells[canvas.height - 1 - by][bx].char = "┼"
            canvas.cells[canvas.height - 1 - by][canvas.width - 1 - bx].char = "┼"


def render(canvas: MondrianCanvas) -> str:
    """Render the canvas to a string with ANSI color escapes."""
    lines = []
    for row in canvas.cells:
        parts = []
        for cell in row:
            r, g, b = cell.bg
            fr, fg_, fb = cell.fg
            bg_esc = bg_color(r, g, b)
            fg_esc = fg_color(fr, fg_, fb)
            parts.append(f"{fg_esc}{bg_esc}{cell.char}")
        lines.append("".join(parts) + RESET)
    return "\n".join(lines)


def render_partial(canvas: MondrianCanvas, rows: int) -> str:
    """Render only the first N rows of the canvas (for animation)."""
    lines = []
    for row in canvas.cells[:rows]:
        parts = []
        for cell in row:
            r, g, b = cell.bg
            fr, fg_, fb = cell.fg
            bg_esc = bg_color(r, g, b)
            fg_esc = fg_color(fr, fg_, fb)
            parts.append(f"{fg_esc}{bg_esc}{cell.char}")
        lines.append("".join(parts) + RESET)
    return "\n".join(lines)


# ── Signature watermark ───────────────────────────────────────────────────

def add_signature(canvas: MondrianCanvas, palette: dict):
    """Add a small 'MONDRIAN' signature in the bottom-right area."""
    sig = "MONDRIAN"
    border_color = palette["black"]
    y = canvas.height - BORDER_W - 2
    if y < 0:
        return
    x_start = canvas.width - BORDER_W - len(sig) - 2
    if x_start < BORDER_W:
        return
    for i, ch in enumerate(sig):
        x = x_start + i
        if 0 <= y < canvas.height and 0 <= x < canvas.width:
            canvas.cells[y][x].char = ch
            canvas.cells[y][x].fg = border_color


# ── Statistics ────────────────────────────────────────────────────────────

def count_regions(canvas: MondrianCanvas, palette: dict) -> dict:
    """Count the number of colored regions and their colors in the canvas."""
    white_color = palette["white"]
    border_color = palette["black"]
    color_counts = {}
    total_colored = 0

    for row in canvas.cells:
        for cell in row:
            bg = cell.bg
            if bg != white_color and bg != border_color:
                total_colored += 1
                color_counts[bg] = color_counts.get(bg, 0) + 1

    # Map RGB back to color names
    name_map = {v: k for k, v in palette.items() if k != "white" and k != "black"}
    result = {}
    for rgb, count in color_counts.items():
        name = name_map.get(rgb, f"custom({rgb[0]},{rgb[1]},{rgb[2]})")
        result[name] = result.get(name, 0) + count

    return {"total_cells": total_colored, "colors": result}


# ── SVG Export ────────────────────────────────────────────────────────────

def export_svg(canvas: MondrianCanvas, palette: dict, filename: str):
    """Export the canvas as an SVG file with proper Mondrian-style rectangles."""
    border_color = palette["black"]
    white_color = palette["white"]
    cell_size = 10  # pixels per character cell

    svg_width = canvas.width * cell_size
    svg_height = canvas.height * cell_size

    lines = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        f'<rect x="0" y="0" width="{svg_width}" height="{svg_height}" fill="rgb({border_color[0]},{border_color[1]},{border_color[2]})"/>',
    ]

    # Find filled regions using flood-fill-like approach
    # Simplified: render each cell as a small rectangle
    visited = [[False] * canvas.width for _ in range(canvas.height)]

    for y in range(canvas.height):
        for x in range(canvas.width):
            if visited[y][x]:
                continue

            cell = canvas.cells[y][x]
            bg = cell.bg

            # Skip border cells (they're the black lines)
            if bg == border_color:
                visited[y][x] = True
                continue

            # Find the extent of this color region (horizontal scan)
            x_end = x
            while x_end < canvas.width and not visited[y][x_end] and canvas.cells[y][x_end].bg == bg:
                x_end += 1

            # Find vertical extent
            y_end = y + 1
            row_match = True
            while row_match and y_end < canvas.height:
                for cx in range(x, x_end):
                    if visited[y_end][cx] or canvas.cells[y_end][cx].bg != bg:
                        row_match = False
                        break
                if row_match:
                    y_end += 1

            # Mark visited
            for ry in range(y, y_end):
                for rx in range(x, x_end):
                    visited[ry][rx] = True

            # Draw the rectangle
            r, g, b = bg
            rx = x * cell_size
            ry_pos = y * cell_size
            rw = (x_end - x) * cell_size
            rh = (y_end - y) * cell_size
            lines.append(f'<rect x="{rx}" y="{ry_pos}" width="{rw}" height="{rh}" fill="rgb({r},{g},{b})"/>')

    lines.append('</svg>')

    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def export_html(canvas: MondrianCanvas, palette: dict, filename: str):
    """Export the canvas as a standalone HTML file with inline CSS grid rendering."""
    border_color = palette["black"]
    cell_size = 10

    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<title>Mondrian Composition</title>',
        '<style>',
        'body { margin: 0; display: flex; justify-content: center; align-items: center;',
        '       min-height: 100vh; background: #1a1a1a; }',
        f'.mondrian {{ display: grid; grid-template-columns: repeat({canvas.width}, {cell_size}px);',
        f'              grid-template-rows: repeat({canvas.height}, {cell_size}px); }}',
        f'.cell {{ width: {cell_size}px; height: {cell_size}px; font-size: 1px; }}',
        '.border-cell { line-height: 1; }',
        '</style>',
        '</head>',
        '<body>',
        '<div class="mondrian">',
    ]

    for row in canvas.cells:
        for cell in row:
            r, g, b = cell.bg
            # Border cells get a distinct class for styling
            if cell.fg == border_color and cell.bg == border_color:
                html_parts.append(f'<div class="cell border-cell" style="background:rgb({r},{g},{b})"></div>')
            else:
                html_parts.append(f'<div class="cell" style="background:rgb({r},{g},{b})"></div>')

    html_parts.extend([
        '</div>',
        '</body>',
        '</html>',
    ])

    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))


# ── Main generation function ─────────────────────────────────────────────

def generate_mondrian(width=80, height=34, seed=None, split_prob=0.85,
                      max_depth=6, min_size=6, palette_name=None,
                      no_signature=False):
    """Generate a Mondrian-style composition and return it as an ANSI string.

    Args:
        width: Canvas width in characters.
        height: Canvas height in rows.
        seed: Random seed for reproducible art.
        split_prob: Probability of splitting a region (0.0–1.0).
        max_depth: Maximum subdivision depth.
        min_size: Minimum region size before splitting stops.
        palette_name: Name of the color palette to use.
        no_signature: If True, omit the MONDRIAN signature watermark.

    Returns:
        Tuple of (ansi_art_string, canvas_object, palette_dict).
    """
    if seed is not None:
        random.seed(seed)

    palette = PALETTES.get(palette_name or DEFAULT_PALETTE, PALETTES[DEFAULT_PALETTE])

    canvas = MondrianCanvas(width=width, height=height)

    # Fill entire canvas with white first
    white_color = palette["white"]
    for row in canvas.cells:
        for cell in row:
            cell.bg = white_color

    # The paintable area (inside outer border)
    inner = Rect(
        BORDER_W, BORDER_W,
        width - 2 * BORDER_W,
        height - 2 * BORDER_W
    )

    subdivide(canvas, inner, depth=0, max_depth=max_depth,
              min_size=min_size, split_prob=split_prob, palette=palette)
    draw_outer_border(canvas, palette)
    fix_intersections(canvas, palette)
    if not no_signature:
        add_signature(canvas, palette)

    return render(canvas), canvas, palette


# ── Animation mode ────────────────────────────────────────────────────────

def animate_mondrian(width=80, height=34, seed=None, split_prob=0.85,
                     max_depth=6, min_size=6, palette_name=None,
                     no_signature=False, delay=0.03):
    """Animate the Mondrian composition being drawn row by row."""
    palette = PALETTES.get(palette_name or DEFAULT_PALETTE, PALETTES[DEFAULT_PALETTE])

    ansi_art, canvas, palette = generate_mondrian(
        width=width, height=height, seed=seed,
        split_prob=split_prob, max_depth=max_depth,
        min_size=min_size, palette_name=palette_name,
        no_signature=no_signature
    )

    # Draw progressively, row by row
    try:
        sys.stdout.write(HIDE_CURSOR)
        sys.stdout.write(CLEAR_SCREEN)
        sys.stdout.flush()

        for row_num in range(1, canvas.height + 1):
            partial = render_partial(canvas, row_num)
            # Move cursor to top-left and redraw
            sys.stdout.write(f"\033[H{partial}")
            sys.stdout.flush()
            time.sleep(delay)

        print()  # newline after completion
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()


# ── CLI ───────────────────────────────────────────────────────────────────

def validate_positive(value, name, min_val=1):
    """Validate that a numeric argument is positive."""
    iv = int(value)
    if iv < min_val:
        raise argparse.ArgumentTypeError(f"{name} must be >= {min_val}, got {iv}")
    return iv


def main():
    parser = argparse.ArgumentParser(
        description="Terminal Mondrian Art Generator — creates De Stijl compositions in your terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                          # Fill terminal with Mondrian art
  %(prog)s -s 42                    # Reproducible composition with seed 42
  %(prog)s -p neon                  # Use the neon color palette
  %(prog)s -W 100 -H 40             # Custom canvas size
  %(prog)s --animate                 # Animate the drawing process
  %(prog)s --export svg output.svg   # Export as SVG file
  %(prog)s --export html output.html # Export as HTML file
"""
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument("-W", "--width", type=int, default=None,
                        help="Canvas width in characters (default: auto-detect terminal width)")
    parser.add_argument("-H", "--height", type=int, default=None,
                        help="Canvas height in rows (default: auto-detect terminal height)")
    parser.add_argument("-s", "--seed", type=int, default=None,
                        help="Random seed for reproducible art")
    parser.add_argument("-p", "--palette", type=str, default=DEFAULT_PALETTE,
                        choices=list(PALETTES.keys()),
                        help=f"Color palette (default: {DEFAULT_PALETTE})")
    parser.add_argument("--split-prob", type=float, default=0.85,
                        help="Probability of splitting a region (0.0-1.0, default: 0.85)")
    parser.add_argument("-d", "--max-depth", type=int, default=6,
                        help="Maximum subdivision depth (default: 6)")
    parser.add_argument("-m", "--min-size", type=int, default=6,
                        help="Minimum region size before splitting stops (default: 6)")
    parser.add_argument("-n", "--count", type=int, default=1,
                        help="Number of compositions to generate (default: 1)")
    parser.add_argument("--no-clear", action="store_true",
                        help="Don't clear screen before drawing")
    parser.add_argument("--no-signature", action="store_true",
                        help="Omit the MONDRIAN signature watermark")
    parser.add_argument("--animate", action="store_true",
                        help="Animate the composition being drawn row by row")
    parser.add_argument("--delay", type=float, default=0.03,
                        help="Delay in seconds between animation frames (default: 0.03)")
    parser.add_argument("--export", type=str, choices=["svg", "html"], default=None,
                        help="Export format (svg or html) instead of terminal rendering")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output file path for --export (default: mondrian.svg or mondrian.html)")
    parser.add_argument("--stats", action="store_true",
                        help="Print composition statistics after rendering")

    args = parser.parse_args()

    # Validate split probability
    if not 0.0 <= args.split_prob <= 1.0:
        parser.error("--split-prob must be between 0.0 and 1.0")

    # Validate min-size
    if args.min_size < 2:
        parser.error("--min-size must be >= 2")

    # Validate delay
    if args.delay < 0:
        parser.error("--delay must be >= 0")

    # Determine terminal size
    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        cols, rows = 80, 34

    width = args.width or cols
    height = args.height or (rows - 1)

    # Validate dimensions
    min_width = 2 * BORDER_W + args.min_size
    min_height = 2 * BORDER_W + args.min_size
    if width < min_width:
        parser.error(f"Width must be at least {min_width} (2×border + min_size)")
    if height < min_height:
        parser.error(f"Height must be at least {min_height} (2×border + min_size)")

    # Handle export mode
    if args.export:
        seed = args.seed if args.seed is not None else random.randint(0, 2**31)
        ansi_art, canvas, palette = generate_mondrian(
            width=width, height=height, seed=seed,
            split_prob=args.split_prob, max_depth=args.max_depth,
            min_size=args.min_size, palette_name=args.palette,
            no_signature=args.no_signature
        )
        if args.output:
            outfile = args.output
        else:
            outfile = f"mondrian.{args.export}"
        if args.export == "svg":
            export_svg(canvas, palette, outfile)
        else:
            export_html(canvas, palette, outfile)
        print(f"Exported Mondrian composition to {outfile} (seed={seed})")
        if args.stats:
            stats = count_regions(canvas, palette)
            print(f"\n{BOLD}Composition statistics:{RESET}")
            print(f"  Seed: {seed}")
            print(f"  Canvas: {width}×{height}")
            print(f"  Palette: {args.palette}")
            for color_name, cell_count in stats["colors"].items():
                print(f"  {color_name}: {cell_count} cells")
            print()
        return

    # Handle animation mode
    if args.animate:
        for i in range(args.count):
            seed = (args.seed + i) if args.seed is not None else None
            animate_mondrian(
                width=width, height=height, seed=seed,
                split_prob=args.split_prob, max_depth=args.max_depth,
                min_size=args.min_size, palette_name=args.palette,
                no_signature=args.no_signature, delay=args.delay
            )
            if i < args.count - 1:
                input("Press Enter for next composition...")
        return

    # Normal terminal rendering
    if not args.no_clear:
        sys.stdout.write(CLEAR_SCREEN)

    for i in range(args.count):
        seed = (args.seed + i) if args.seed is not None else None
        ansi_art, canvas, palette = generate_mondrian(
            width=width, height=height, seed=seed,
            split_prob=args.split_prob, max_depth=args.max_depth,
            min_size=args.min_size, palette_name=args.palette,
            no_signature=args.no_signature
        )
        print(ansi_art)
        if args.stats:
            stats = count_regions(canvas, palette)
            print(f"\n{BOLD}Composition statistics:{RESET}")
            print(f"  Seed: {seed}")
            print(f"  Canvas: {width}×{height}")
            print(f"  Palette: {args.palette}")
            for color_name, cell_count in stats["colors"].items():
                print(f"  {color_name}: {cell_count} cells")
            print()
        if i < args.count - 1:
            print()
            input("Press Enter for next composition...")


if __name__ == "__main__":
    main()