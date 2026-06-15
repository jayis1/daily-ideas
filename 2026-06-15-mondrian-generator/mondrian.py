#!/usr/bin/env python3
"""
Terminal Mondrian Art Generator
================================
Recursively subdivides a canvas into rectangles and fills them with
primary colors in the style of Piet Mondrian's iconic compositions.
Renders using Unicode box-drawing characters and ANSI true-color escapes.

Supports multiple palettes, animation mode, SVG/HTML/PNG export,
custom palettes via JSON, and composition statistics.

Version: 3.0.0
"""

import random
import sys
import os
import argparse
import math
import time
import json
import struct
import zlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

__version__ = "3.0.1"

# ── ANSI helpers ──────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
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

PALETTES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
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
    "ocean": {
        "red":     (255,  99,  71),
        "blue":    (  0, 105, 148),
        "yellow":  (255, 224, 130),
        "white":   (224, 235, 245),
        "black":   ( 15,  30,  45),
    },
    "autumn": {
        "red":     (178,  34,  34),
        "blue":    ( 70,  90, 130),
        "yellow":  (218, 165,  32),
        "white":   (245, 235, 220),
        "black":   ( 45,  30,  20),
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

    def area(self) -> int:
        """Return the area of this rectangle."""
        return self.w * self.h

@dataclass
class Cell:
    """A single character cell in the canvas with foreground/background colors."""
    char: str = " "
    bg: Tuple[int, int, int] = (0, 0, 0)
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

            # Also detect border cells (filled black bg) as connections
            if not has_up and y > 0 and canvas.cells[y-1][x].fg == border_color:
                has_up = True
            if not has_down and y < canvas.height - 1 and canvas.cells[y+1][x].fg == border_color:
                has_down = True
            if not has_left and x > 0 and canvas.cells[y][x-1].fg == border_color:
                has_left = True
            if not has_right and x < canvas.width - 1 and canvas.cells[y][x+1].fg == border_color:
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

            # Corner T-junctions: a border cell at the edge of the canvas
            # where a line terminates at the outer border
            if cell.fg == border_color and cell.bg == border_color and cell.char == " ":
                # This is a filled border area — check if it's a junction
                connections = 0
                if has_up: connections += 1
                if has_down: connections += 1
                if has_left: connections += 1
                if has_right: connections += 1
                # If it's a junction of multiple lines, mark as cross
                if connections >= 3:
                    cell.char = "┼"
                elif has_up and has_down and not has_left and not has_right:
                    cell.char = "│"
                elif has_left and has_right and not has_up and not has_down:
                    cell.char = "─"


def draw_outer_border(canvas: MondrianCanvas, palette: dict):
    """Draw a thick border around the entire canvas.

    Safe for canvases of any size — skips cells that would be out of bounds.
    """
    border_color = palette["black"]

    for x in range(canvas.width):
        for bw in range(BORDER_W):
            # Top border rows
            top_row = bw
            if top_row < canvas.height:
                canvas.cells[top_row][x].char = "─"
                canvas.cells[top_row][x].fg = border_color
                canvas.cells[top_row][x].bg = border_color
            # Bottom border rows
            bot_row = canvas.height - 1 - bw
            if 0 <= bot_row < canvas.height:
                canvas.cells[bot_row][x].char = "─"
                canvas.cells[bot_row][x].fg = border_color
                canvas.cells[bot_row][x].bg = border_color
    for y in range(canvas.height):
        for bw in range(BORDER_W):
            # Left border columns
            left_col = bw
            if left_col < canvas.width:
                canvas.cells[y][left_col].char = "│"
                canvas.cells[y][left_col].fg = border_color
                canvas.cells[y][left_col].bg = border_color
            # Right border columns
            right_col = canvas.width - 1 - bw
            if 0 <= right_col < canvas.width:
                canvas.cells[y][right_col].char = "│"
                canvas.cells[y][right_col].fg = border_color
                canvas.cells[y][right_col].bg = border_color

    # Corner intersections
    for by in range(BORDER_W):
        for bx in range(BORDER_W):
            if by < canvas.height and bx < canvas.width:
                canvas.cells[by][bx].char = "┼"
            if by < canvas.height and (canvas.width - 1 - bx) >= 0:
                canvas.cells[by][canvas.width - 1 - bx].char = "┼"
            if (canvas.height - 1 - by) >= 0 and bx < canvas.width:
                canvas.cells[canvas.height - 1 - by][bx].char = "┼"
            if (canvas.height - 1 - by) >= 0 and (canvas.width - 1 - bx) >= 0:
                canvas.cells[canvas.height - 1 - by][canvas.width - 1 - bx].char = "┼"


def render(canvas: MondrianCanvas) -> str:
    """Render the canvas to a string with ANSI color escapes.

    Optimized to batch same-background cells together to reduce
    the number of ANSI escape sequences emitted.
    """
    lines = []
    for row in canvas.cells:
        parts = []
        prev_bg = None
        prev_fg = None
        for cell in row:
            r, g, b = cell.bg
            fr, fg_, fb = cell.fg
            # Only emit color changes when the color actually changes
            if (r, g, b) != prev_bg or (fr, fg_, fb) != prev_fg:
                bg_esc = bg_color(r, g, b)
                fg_esc = fg_color(fr, fg_, fb)
                parts.append(f"{fg_esc}{bg_esc}{cell.char}")
                prev_bg = (r, g, b)
                prev_fg = (fr, fg_, fb)
            else:
                parts.append(cell.char)
        lines.append("".join(parts) + RESET)
    return "\n".join(lines)


def render_plain(canvas: MondrianCanvas) -> str:
    """Render the canvas as plain text without ANSI escapes (for piping/export)."""
    lines = []
    for row in canvas.cells:
        line = "".join(cell.char for cell in row)
        lines.append(line)
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

def add_signature(canvas: MondrianCanvas, palette: dict, text: str = "MONDRIAN"):
    """Add a small signature text in the bottom-right area.

    Args:
        canvas: The canvas to add the signature to.
        palette: The color palette dict.
        text: Custom signature text (default: "MONDRIAN").
    """
    border_color = palette["black"]
    y = canvas.height - BORDER_W - 2
    if y < 0:
        return
    x_start = canvas.width - BORDER_W - len(text) - 2
    if x_start < BORDER_W:
        return
    for i, ch in enumerate(text):
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


def compute_coverage(canvas: MondrianCanvas, palette: dict) -> dict:
    """Compute the percentage coverage of each color in the paintable area.

    Returns a dict mapping color names to percentage of total non-border cells.
    """
    border_color = palette["black"]
    total_non_border = 0
    color_cells = {}

    for row in canvas.cells:
        for cell in row:
            if cell.bg != border_color:
                total_non_border += 1

    # Reverse lookup from RGB to name
    name_map = {v: k for k, v in palette.items()}

    for row in canvas.cells:
        for cell in row:
            bg = cell.bg
            if bg == border_color:
                continue
            name = name_map.get(bg, f"custom({bg[0]},{bg[1]},{bg[2]})")
            color_cells[name] = color_cells.get(name, 0) + 1

    if total_non_border == 0:
        return {name: 0.0 for name in color_cells}

    return {name: round(count / total_non_border * 100, 1)
            for name, count in color_cells.items()}


# ── SVG Export ────────────────────────────────────────────────────────────

def export_svg(canvas: MondrianCanvas, palette: dict, filename: str):
    """Export the canvas as an SVG file with proper Mondrian-style rectangles.

    Uses a flood-fill-like approach to merge adjacent same-color cells into
    larger rectangles, producing clean, compact SVG output.
    """
    border_color = palette["black"]
    cell_size = 10  # pixels per character cell

    svg_width = canvas.width * cell_size
    svg_height = canvas.height * cell_size

    lines = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        f'<rect x="0" y="0" width="{svg_width}" height="{svg_height}" fill="rgb({border_color[0]},{border_color[1]},{border_color[2]})"/>',
    ]

    # Find filled regions using flood-fill-like approach
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


def export_png(canvas: MondrianCanvas, palette: dict, filename: str, cell_size: int = 10):
    """Export the canvas as a PNG file using pure Python (no external dependencies).

    Creates a pixel-by-pixel rendering of the Mondrian composition at the
    specified cell size (each character cell becomes a cell_size×cell_size block).

    Args:
        canvas: The MondrianCanvas to export.
        palette: The color palette dict.
        filename: Output file path.
        cell_size: Pixels per character cell (default: 10).
    """
    width_px = canvas.width * cell_size
    height_px = canvas.height * cell_size

    # Build raw pixel data row by row (RGB)
    raw_rows = []
    for row in canvas.cells:
        # Each cell row expands to cell_size pixel rows
        pixel_row_parts = []
        for cell in row:
            r, g, b = cell.bg
            pixel_row_parts.extend([bytes([r, g, b])] * cell_size)
        pixel_row = b"".join(pixel_row_parts)
        # Repeat this row cell_size times
        for _ in range(cell_size):
            raw_rows.append(pixel_row)

    raw_data = b"".join(raw_rows)

    # Build PNG file
    def _make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        """Create a PNG chunk with length, type, data, and CRC."""
        chunk_data = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(chunk_data) & 0xFFFFFFFF)
        length = struct.pack(">I", len(data))
        return length + chunk_data + crc

    # PNG signature
    png_sig = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk: width, height, bit_depth=8, color_type=2 (RGB), compression=0, filter=0, interlace=0
    ihdr_data = struct.pack(">IIBBBBB", width_px, height_px, 8, 2, 0, 0, 0)
    ihdr = _make_chunk(b"IHDR", ihdr_data)

    # IDAT chunk: filter byte (0=None) + raw data per row, then zlib compress
    # Add filter byte 0 (None) at start of each row
    filtered = b""
    row_size = width_px * 3
    for i in range(height_px):
        start = i * row_size
        end = start + row_size
        filtered += b"\x00" + raw_data[start:end]

    compressed = zlib.compress(filtered, 9)
    idat = _make_chunk(b"IDAT", compressed)

    # IEND chunk
    iend = _make_chunk(b"IEND", b"")

    with open(filename, "wb") as f:
        f.write(png_sig + ihdr + idat + iend)


# ── Palette listing ───────────────────────────────────────────────────────

def list_palettes():
    """Print a formatted list of available palettes with ANSI color swatches."""
    print(f"\n{BOLD}Available Mondrian Palettes{RESET}\n")
    for name, palette in PALETTES.items():
        marker = " (default)" if name == DEFAULT_PALETTE else ""
        print(f"  {BOLD}{name}{RESET}{marker}")
        swatch_parts = []
        for color_name, rgb in palette.items():
            r, g, b = rgb
            swatch = f"  {bg_color(r, g, b)}   {RESET} {color_name}: rgb({r},{g},{b})"
            swatch_parts.append(swatch)
        print("\n".join(swatch_parts))
        print()


def parse_custom_palette(json_str: str) -> dict:
    """Parse a custom palette from a JSON string.

    The JSON must be an object with keys 'red', 'blue', 'yellow', 'white', 'black',
    each mapping to an array of 3 integers [R, G, B] (0-255).

    Example: '{"red":[255,0,0],"blue":[0,0,255],"yellow":[255,255,0],"white":[255,255,255],"black":[0,0,0]}'
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for custom palette: {e}")

    required = {"red", "blue", "yellow", "white", "black"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Custom palette missing colors: {', '.join(sorted(missing))}. Required: {', '.join(sorted(required))}")

    extra = set(data.keys()) - required
    if extra:
        raise ValueError(f"Custom palette has unknown colors: {', '.join(sorted(extra))}. Only {', '.join(sorted(required))} are allowed")

    palette = {}
    for key in required:
        val = data[key]
        if not isinstance(val, list) or len(val) != 3:
            raise ValueError(f"Color '{key}' must be a list of 3 integers, got: {val}")
        r, g, b = val
        for component, name in zip([r, g, b], ["R", "G", "B"]):
            if not isinstance(component, int) or component < 0 or component > 255:
                raise ValueError(f"Color '{key}' {name} value must be an integer 0-255, got: {component}")
        palette[key] = (r, g, b)

    return palette


# ── Main generation function ─────────────────────────────────────────────

def generate_mondrian(width=80, height=34, seed=None, split_prob=0.85,
                      max_depth=6, min_size=6, palette_name=None,
                      no_signature=False, custom_palette=None):
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
        custom_palette: Optional dict override for the palette colors.

    Returns:
        Tuple of (ansi_art_string, canvas_object, palette_dict).
    """
    if seed is not None:
        random.seed(seed)

    # Validate dimensions — canvas must be large enough for the outer border
    min_dim = 2 * BORDER_W + 1  # At least border + 1 cell inner
    if width < min_dim or height < min_dim:
        raise ValueError(
            f"Canvas dimensions must be at least {min_dim}×{min_dim} "
            f"(got {width}×{height}). The outer border requires {BORDER_W} "
            f"cells on each side."
        )

    palette = custom_palette or PALETTES.get(palette_name or DEFAULT_PALETTE, PALETTES[DEFAULT_PALETTE])

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
                     no_signature=False, delay=0.03, custom_palette=None):
    """Animate the Mondrian composition being drawn row by row."""
    palette = custom_palette or PALETTES.get(palette_name or DEFAULT_PALETTE, PALETTES[DEFAULT_PALETTE])

    ansi_art, canvas, palette = generate_mondrian(
        width=width, height=height, seed=seed,
        split_prob=split_prob, max_depth=max_depth,
        min_size=min_size, palette_name=palette_name,
        no_signature=no_signature, custom_palette=custom_palette
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
  %(prog)s --export svg -o art.svg   # Export as SVG file
  %(prog)s --export png -o art.png   # Export as PNG file
  %(prog)s --export html -o art.html # Export as HTML file
  %(prog)s --list-palettes           # Show available color palettes
  %(prog)s --custom-palette '{"red":[255,0,0],"blue":[0,0,255],"yellow":[255,255,0],"white":[255,255,255],"black":[0,0,0]}'
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
    parser.add_argument("--custom-palette", type=str, default=None,
                        help="Custom palette as JSON (overrides --palette). "
                             "Format: '{\"red\":[R,G,B],\"blue\":[R,G,B],\"yellow\":[R,G,B],\"white\":[R,G,B],\"black\":[R,G,B]}'")
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
    parser.add_argument("--export", type=str, choices=["svg", "html", "png"], default=None,
                        help="Export format (svg, html, or png) instead of terminal rendering")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output file path for --export (default: mondrian.<format>)")
    parser.add_argument("--stats", action="store_true",
                        help="Print composition statistics after rendering")
    parser.add_argument("--list-palettes", action="store_true",
                        help="List available palettes with color swatches and exit")
    parser.add_argument("--plain", action="store_true",
                        help="Output plain text without ANSI escapes (for piping)")
    parser.add_argument("--cell-size", type=int, default=10,
                        help="Cell size in pixels for PNG export (default: 10)")

    args = parser.parse_args()

    # Handle --list-palettes
    if args.list_palettes:
        list_palettes()
        return

    # Parse custom palette
    custom_palette = None
    if args.custom_palette:
        try:
            custom_palette = parse_custom_palette(args.custom_palette)
        except ValueError as e:
            parser.error(str(e))

    # Validate split probability
    if not 0.0 <= args.split_prob <= 1.0:
        parser.error("--split-prob must be between 0.0 and 1.0")

    # Validate min-size
    if args.min_size < 1:
        parser.error("--min-size must be >= 1")

    # Validate delay
    if args.delay < 0:
        parser.error("--delay must be >= 0")

    # Validate cell-size
    if args.cell_size < 1:
        parser.error("--cell-size must be >= 1")

    # Validate count
    if args.count < 1:
        parser.error("--count must be >= 1")

    # Validate max-depth
    if args.max_depth < 0:
        parser.error("--max-depth must be >= 0")

    # Validate width and height (when explicitly provided)
    if args.width is not None and args.width < 1:
        parser.error("--width must be >= 1")
    if args.height is not None and args.height < 1:
        parser.error("--height must be >= 1")

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

    # Determine palette name (for display purposes)
    palette_display = "custom" if custom_palette else args.palette

    # Handle export mode
    if args.export:
        seed = args.seed if args.seed is not None else random.randint(0, 2**31)
        ansi_art, canvas, palette = generate_mondrian(
            width=width, height=height, seed=seed,
            split_prob=args.split_prob, max_depth=args.max_depth,
            min_size=args.min_size, palette_name=args.palette,
            no_signature=args.no_signature, custom_palette=custom_palette
        )
        if args.output:
            outfile = args.output
        else:
            outfile = f"mondrian.{args.export}"
        if args.export == "svg":
            export_svg(canvas, palette, outfile)
        elif args.export == "html":
            export_html(canvas, palette, outfile)
        elif args.export == "png":
            export_png(canvas, palette, outfile, cell_size=args.cell_size)
        print(f"Exported Mondrian composition to {outfile} (seed={seed})")
        if args.stats:
            stats = count_regions(canvas, palette)
            coverage = compute_coverage(canvas, palette)
            print(f"\n{BOLD}Composition statistics:{RESET}")
            print(f"  Seed: {seed}")
            print(f"  Canvas: {width}×{height}")
            print(f"  Palette: {palette_display}")
            for color_name, cell_count in stats["colors"].items():
                pct = coverage.get(color_name, 0.0)
                print(f"  {color_name}: {cell_count} cells ({pct}%)")
            total_colored = stats["total_cells"]
            total_cells = width * height
            border_cells = sum(
                1 for row in canvas.cells for cell in row
                if cell.fg == palette["black"]
            )
            print(f"  Border cells: {border_cells} ({round(border_cells / total_cells * 100, 1)}%)")
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
                no_signature=args.no_signature, delay=args.delay,
                custom_palette=custom_palette
            )
            if i < args.count - 1:
                input("Press Enter for next composition...")
        return

    # Normal terminal rendering
    if not args.no_clear and not args.plain:
        sys.stdout.write(CLEAR_SCREEN)

    for i in range(args.count):
        seed = (args.seed + i) if args.seed is not None else None
        ansi_art, canvas, palette = generate_mondrian(
            width=width, height=height, seed=seed,
            split_prob=args.split_prob, max_depth=args.max_depth,
            min_size=args.min_size, palette_name=args.palette,
            no_signature=args.no_signature, custom_palette=custom_palette
        )

        if args.plain:
            print(render_plain(canvas))
        else:
            print(ansi_art)

        if args.stats:
            stats = count_regions(canvas, palette)
            coverage = compute_coverage(canvas, palette)
            print(f"\n{BOLD}Composition statistics:{RESET}")
            print(f"  Seed: {seed}")
            print(f"  Canvas: {width}×{height}")
            print(f"  Palette: {palette_display}")
            for color_name, cell_count in stats["colors"].items():
                pct = coverage.get(color_name, 0.0)
                print(f"  {color_name}: {cell_count} cells ({pct}%)")
            total_colored = stats["total_cells"]
            total_cells = width * height
            border_cells = sum(
                1 for row in canvas.cells for cell in row
                if cell.fg == palette["black"]
            )
            print(f"  Border cells: {border_cells} ({round(border_cells / total_cells * 100, 1)}%)")
            print()
        if i < args.count - 1:
            print()
            input("Press Enter for next composition...")


if __name__ == "__main__":
    main()