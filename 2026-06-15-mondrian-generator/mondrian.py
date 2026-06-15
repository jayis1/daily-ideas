#!/usr/bin/env python3
"""
Terminal Mondrian Art Generator
================================
Recursively subdivides a canvas into rectangles and fills them with
primary colors in the style of Piet Mondrian's iconic compositions.
Renders using Unicode box-drawing characters and ANSI true-color escapes.
"""

import random
import sys
import os
import argparse
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ── ANSI helpers ──────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"

def fg_color(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"

def bg_color(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"

# ── Mondrian palette ─────────────────────────────────────────────────────

PALETTE = {
    "red":      (206,  32,  41),
    "blue":     (  0,  54, 170),
    "yellow":   (255, 222,   0),
    "white":    (242, 242, 242),
    "black":    ( 20,  20,  20),
}

BORDER_COLOR = PALETTE["black"]

FILL_CHOICES = ["red", "blue", "yellow", "white", "white", "white", "white"]
# More white → more authentic Mondrian feel

# ── Data structures ───────────────────────────────────────────────────────

@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

@dataclass
class Cell:
    """A single character cell in the canvas."""
    char: str = " "
    bg: Tuple[int, int, int] = PALETTE["white"]
    fg: Tuple[int, int, int] = (0, 0, 0)

@dataclass
class MondrianCanvas:
    width: int
    height: int
    cells: List[List[Cell]] = field(default_factory=list)

    def __post_init__(self):
        self.cells = [
            [Cell() for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def fill_rect(self, rect: Rect, color_name: str):
        r, g, b = PALETTE[color_name]
        for row in range(rect.y, rect.y + rect.h):
            for col in range(rect.x, rect.x + rect.w):
                if 0 <= row < self.height and 0 <= col < self.width:
                    self.cells[row][col].bg = (r, g, b)

    def draw_hline(self, y: int, x1: int, x2: int):
        for x in range(x1, x2 + 1):
            if 0 <= y < self.height and 0 <= x < self.width:
                self.cells[y][x].char = "─"
                self.cells[y][x].fg = BORDER_COLOR
                # Make the line "thicker" by coloring bg too
                # Actually, we'll draw 2-line thick borders

    def draw_vline(self, x: int, y1: int, y2: int):
        for y in range(y1, y2 + 1):
            if 0 <= y < self.height and 0 <= x < self.width:
                self.cells[y][x].char = "│"
                self.cells[y][x].fg = BORDER_COLOR

    def draw_cross(self, x: int, y: int):
        if 0 <= y < self.height and 0 <= x < self.width:
            self.cells[y][x].char = "┼"
            self.cells[y][x].fg = BORDER_COLOR

    def draw_tdown(self, x: int, y: int):
        if 0 <= y < self.height and 0 <= x < self.width:
            self.cells[y][x].char = "┬"
            self.cells[y][x].fg = BORDER_COLOR

    def draw_tup(self, x: int, y: int):
        if 0 <= y < self.height and 0 <= x < self.width:
            self.cells[y][x].char = "┴"
            self.cells[y][x].fg = BORDER_COLOR

    def draw_tright(self, x: int, y: int):
        if 0 <= y < self.height and 0 <= x < self.width:
            self.cells[y][x].char = "├"
            self.cells[y][x].fg = BORDER_COLOR

    def draw_tleft(self, x: int, y: int):
        if 0 <= y < self.height and 0 <= x < self.width:
            self.cells[y][x].char = "┤"
            self.cells[y][x].fg = BORDER_COLOR

# ── Recursive subdivision ─────────────────────────────────────────────────

BORDER_W = 2  # 2-char thick borders for Mondrian feel

def subdivide(canvas: MondrianCanvas, rect: Rect, depth: int, max_depth: int,
              min_size: int, split_prob: float):
    """Recursively subdivide a rectangle and fill leaf regions with colors."""

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
            canvas.fill_rect(inner, fill)
        return

    # Choose split direction
    can_split_h = rect.h >= min_size * 2 + BORDER_W
    can_split_v = rect.w >= min_size * 2 + BORDER_W

    if can_split_h and can_split_v:
        # Prefer the longer axis
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
            canvas.fill_rect(inner, fill)
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
                canvas.fill_rect(inner, fill)
            return
        split_y = random.randint(min_pos, max_pos)

        # Draw horizontal border at split_y..split_y+BORDER_W-1
        for dy in range(BORDER_W):
            for x in range(rect.x, rect.x + rect.w):
                if 0 <= split_y + dy < canvas.height and 0 <= x < canvas.width:
                    canvas.cells[split_y + dy][x].char = "─"
                    canvas.cells[split_y + dy][x].fg = BORDER_COLOR
                    canvas.cells[split_y + dy][x].bg = BORDER_COLOR

        # Corners / intersections handled after all splits

        top = Rect(rect.x, rect.y, rect.w, split_y - rect.y)
        bottom = Rect(rect.x, split_y + BORDER_W, rect.w,
                      rect.y + rect.h - split_y - BORDER_W)
        subdivide(canvas, top, depth + 1, max_depth, min_size, split_prob)
        subdivide(canvas, bottom, depth + 1, max_depth, min_size, split_prob)

    else:
        # Split vertically (left/right)
        min_pos = rect.x + BORDER_W + min_size
        max_pos = rect.x + rect.w - BORDER_W - min_size - BORDER_W
        if min_pos >= max_pos:
            fill = random.choice(FILL_CHOICES)
            inner = Rect(rect.x + BORDER_W, rect.y + BORDER_W,
                         rect.w - 2 * BORDER_W, rect.h - 2 * BORDER_W)
            if inner.w > 0 and inner.h > 0:
                canvas.fill_rect(inner, fill)
            return
        split_x = random.randint(min_pos, max_pos)

        # Draw vertical border
        for dx in range(BORDER_W):
            for y in range(rect.y, rect.y + rect.h):
                if 0 <= y < canvas.height and 0 <= split_x + dx < canvas.width:
                    canvas.cells[y][split_x + dx].char = "│"
                    canvas.cells[y][split_x + dx].fg = BORDER_COLOR
                    canvas.cells[y][split_x + dx].bg = BORDER_COLOR

        left = Rect(rect.x, rect.y, split_x - rect.x, rect.h)
        right = Rect(split_x + BORDER_W, rect.y,
                     rect.x + rect.w - split_x - BORDER_W, rect.h)
        subdivide(canvas, left, depth + 1, max_depth, min_size, split_prob)
        subdivide(canvas, right, depth + 1, max_depth, min_size, split_prob)


def fix_intersections(canvas: MondrianCanvas):
    """Second pass: wherever ─ and │ cross, place the correct box-drawing char."""
    for y in range(canvas.height):
        for x in range(canvas.width):
            cell = canvas.cells[y][x]
            # We check if this cell is part of a border (has black fg/bg)
            if cell.fg != BORDER_COLOR and cell.bg != BORDER_COLOR:
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

    # Fix corners: where border meets the edge of canvas
    # Already handled by outer border drawing


def draw_outer_border(canvas: MondrianCanvas):
    """Draw a thick border around the entire canvas."""
    for x in range(canvas.width):
        for bw in range(BORDER_W):
            canvas.cells[bw][x].char = "─"
            canvas.cells[bw][x].fg = BORDER_COLOR
            canvas.cells[bw][x].bg = BORDER_COLOR
            canvas.cells[canvas.height - 1 - bw][x].char = "─"
            canvas.cells[canvas.height - 1 - bw][x].fg = BORDER_COLOR
            canvas.cells[canvas.height - 1 - bw][x].bg = BORDER_COLOR
    for y in range(canvas.height):
        for bw in range(BORDER_W):
            canvas.cells[y][bw].char = "│"
            canvas.cells[y][bw].fg = BORDER_COLOR
            canvas.cells[y][bw].bg = BORDER_COLOR
            canvas.cells[y][canvas.width - 1 - bw].char = "│"
            canvas.cells[y][canvas.width - 1 - bw].fg = BORDER_COLOR
            canvas.cells[y][canvas.width - 1 - bw].bg = BORDER_COLOR

    # Corner intersections
    for by in range(BORDER_W):
        for bx in range(BORDER_W):
            canvas.cells[by][bx].char = "┼"
            canvas.cells[by][canvas.width - 1 - bx].char = "┼"
            canvas.cells[canvas.height - 1 - by][bx].char = "┼"
            canvas.cells[canvas.height - 1 - by][canvas.width - 1 - bx].char = "┼"


def render(canvas: MondrianCanvas) -> str:
    """Render the canvas to a string with ANSI escapes."""
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


# ── Signature watermark ───────────────────────────────────────────────────

def add_signature(canvas: MondrianCanvas):
    """Add a small 'MONDRIAN' signature in the bottom-right area."""
    sig = "MONDRIAN"
    # Find a white-ish cell area in the bottom rows
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
            canvas.cells[y][x].fg = BORDER_COLOR


# ── Main ──────────────────────────────────────────────────────────────────

def generate_mondrian(width=80, height=34, seed=None, split_prob=0.85,
                      max_depth=6, min_size=6):
    if seed is not None:
        random.seed(seed)

    canvas = MondrianCanvas(width=width, height=height)

    # Fill entire canvas with white first
    for row in canvas.cells:
        for cell in row:
            cell.bg = PALETTE["white"]

    # The paintable area (inside outer border)
    inner = Rect(
        BORDER_W, BORDER_W,
        width - 2 * BORDER_W,
        height - 2 * BORDER_W
    )

    subdivide(canvas, inner, depth=0, max_depth=max_depth,
              min_size=min_size, split_prob=split_prob)
    draw_outer_border(canvas)
    fix_intersections(canvas)
    add_signature(canvas)

    return render(canvas)


def main():
    parser = argparse.ArgumentParser(
        description="Terminal Mondrian Art Generator — creates De Stijl compositions in your terminal"
    )
    parser.add_argument("-W", "--width", type=int, default=None,
                        help="Canvas width in characters (default: auto-detect terminal width)")
    parser.add_argument("-H", "--height", type=int, default=None,
                        help="Canvas height in rows (default: auto-detect terminal height)")
    parser.add_argument("-s", "--seed", type=int, default=None,
                        help="Random seed for reproducible art")
    parser.add_argument("-p", "--split-prob", type=float, default=0.85,
                        help="Probability of splitting a region (0.0-1.0, default: 0.85)")
    parser.add_argument("-d", "--max-depth", type=int, default=6,
                        help="Maximum subdivision depth (default: 6)")
    parser.add_argument("-m", "--min-size", type=int, default=6,
                        help="Minimum region size before splitting stops (default: 6)")
    parser.add_argument("-n", "--count", type=int, default=1,
                        help="Number of compositions to generate (default: 1)")
    parser.add_argument("--no-clear", action="store_true",
                        help="Don't clear screen before drawing")

    args = parser.parse_args()

    # Determine terminal size
    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        cols, rows = 80, 34

    width = args.width or cols
    height = args.height or (rows - 1)

    if not args.no_clear:
        # Clear screen
        sys.stdout.write("\033[2J\033[H")

    for i in range(args.count):
        seed = (args.seed + i) if args.seed is not None else None
        art = generate_mondrian(
            width=width,
            height=height,
            seed=seed,
            split_prob=args.split_prob,
            max_depth=args.max_depth,
            min_size=args.min_size,
        )
        print(art)
        if i < args.count - 1:
            print()
            input("Press Enter for next composition...")


if __name__ == "__main__":
    main()