#!/usr/bin/env python3
"""
Procedural Flag Generator
==========================
Generates random fictional country flags with various geometric patterns
and renders them as colorful Unicode block art in the terminal.

Patterns: horizontal stripes, vertical stripes, diagonal, cross, chevron,
saltire, circle, crescent, star, quarters, canton, and combinations.
"""

import random
import math
import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ─── Color definitions (ANSI 256-color) ──────────────────────────────
FLAG_COLORS = {
    "red":       196,
    "dark_red":  88,
    "green":     46,
    "dark_green": 22,
    "blue":      21,
    "dark_blue": 18,
    "yellow":    226,
    "gold":      220,
    "orange":    202,
    "white":     231,
    "black":     16,
    "brown":     130,
    "purple":    93,
    "cyan":      51,
    "teal":      37,
    "pink":      213,
    "maroon":    52,
    "navy":      17,
    "crimson":   161,
    "sky_blue":  117,
    "lime":      118,
    "ivory":     230,
    "coral":     209,
    "mauve":     139,
    "olive":     100,
    "scarlet":   160,
}

# Unicode full block for rendering
BLOCK = "█"
HALF_TOP = "▀"
HALF_BOT = "▄"

# Flag grid dimensions
FLAG_W = 60
FLAG_H = 40


def color_name(code: int) -> str:
    for name, c in FLAG_COLORS.items():
        if c == code:
            return name
    return str(code)


def fg(code: int) -> str:
    return f"\033[38;5;{code}m"


def bg(code: int) -> str:
    return f"\033[48;5;{code}m"


RESET = "\033[0m"


def pick_colors(n: int, exclude: Optional[List[int]] = None) -> List[int]:
    """Pick n distinct flag colors, avoiding those in exclude."""
    pool = [v for v in FLAG_COLORS.values() if exclude is None or v not in exclude]
    return random.sample(pool, min(n, len(pool)))


# ─── Pattern generators ──────────────────────────────────────────────

def pattern_horizontal_stripes(w: int, h: int, colors: List[int], n_stripes: int) -> List[List[int]]:
    """Horizontal stripes (like Germany, Netherlands)."""
    grid = [[0]*w for _ in range(h)]
    stripe_h = h // n_stripes
    for i in range(n_stripes):
        y_start = i * stripe_h
        y_end = h if i == n_stripes - 1 else (i + 1) * stripe_h
        for y in range(y_start, y_end):
            for x in range(w):
                grid[y][x] = colors[i % len(colors)]
    return grid


def pattern_vertical_stripes(w: int, h: int, colors: List[int], n_stripes: int) -> List[List[int]]:
    """Vertical stripes (like France, Italy, Nigeria)."""
    grid = [[0]*w for _ in range(h)]
    stripe_w = w // n_stripes
    for i in range(n_stripes):
        x_start = i * stripe_w
        x_end = w if i == n_stripes - 1 else (i + 1) * stripe_w
        for y in range(h):
            for x in range(x_start, x_end):
                grid[y][x] = colors[i % len(colors)]
    return grid


def pattern_diagonal(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """Diagonal split (like Republic of the Congo)."""
    grid = [[0]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            diag = (x / w) - (y / h)
            grid[y][x] = colors[0] if diag < 0 else colors[1]
    return grid


def pattern_cross(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """Nordic cross (like Sweden, Finland, Norway)."""
    grid = [[0]*w for _ in range(h)]
    bg_color = colors[0]
    cross_color = colors[1]
    # Cross center offset to the hoist side
    cx = w // 3
    cy = h // 2
    cross_w = max(w // 8, 3)
    cross_h = max(h // 6, 2)

    for y in range(h):
        for x in range(w):
            in_vertical = abs(x - cx) <= cross_w
            in_horizontal = abs(y - cy) <= cross_h
            if in_vertical or in_horizontal:
                grid[y][x] = cross_color
            else:
                grid[y][x] = bg_color
    return grid


def pattern_saltire(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """X-shaped cross (like Scotland, Jamaica)."""
    grid = [[0]*w for _ in range(h)]
    bg_color = colors[0]
    x_color = colors[1]
    thickness = max(min(w, h) // 10, 2)

    for y in range(h):
        for x in range(w):
            # Distance from each diagonal
            d1 = abs(y * w - x * h) / max(w, 1)
            d2 = abs(y * w + x * h - h * w) / max(w, 1)
            if d1 < thickness * h / 2 or d2 < thickness * h / 2:
                grid[y][x] = x_color
            else:
                grid[y][x] = bg_color
    return grid


def pattern_chevron(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """Chevron on the hoist side (like Czech Republic, Philippines)."""
    grid = [[0]*w for _ in range(h)]
    bg_color = colors[0]
    chevron_color = colors[1]
    chevron_depth = w // 3

    for y in range(h):
        for x in range(w):
            # V-shape: at the hoist side
            mid_y = h / 2
            chevron_edge = chevron_depth - abs(y - mid_y) * (chevron_depth / mid_y)
            if x < chevron_edge:
                grid[y][x] = chevron_color
            else:
                grid[y][x] = bg_color
    return grid


def pattern_quarters(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """Four quarters (like Panama, Dominican Republic)."""
    grid = [[0]*w for _ in range(h)]
    mid_x = w // 2
    mid_y = h // 2
    c = [colors[0], colors[1], colors[2], colors[3]]

    for y in range(h):
        for x in range(w):
            if y < mid_y:
                if x < mid_x:
                    grid[y][x] = c[0]
                else:
                    grid[y][x] = c[1]
            else:
                if x < mid_x:
                    grid[y][x] = c[2]
                else:
                    grid[y][x] = c[3]
    return grid


def pattern_circle(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """Central circle (like Japan, Bangladesh, Palau)."""
    grid = [[0]*w for _ in range(h)]
    bg_color = colors[0]
    circle_color = colors[1]
    cx, cy = w // 2, h // 2
    radius = min(w, h) // 4

    for y in range(h):
        for x in range(w):
            # Adjust for aspect ratio (chars are ~2:1)
            dx = (x - cx)
            dy = (y - cy) * 2  # compensate for character aspect ratio
            if dx*dx + dy*dy <= radius*radius * 4:
                grid[y][x] = circle_color
            else:
                grid[y][x] = bg_color
    return grid


def pattern_crescent(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """Crescent moon (like Turkey, Pakistan, Tunisia)."""
    grid = [[0]*w for _ in range(h)]
    bg_color = colors[0]
    crescent_color = colors[1]
    cx, cy = w // 2 - 3, h // 2
    radius = min(w, h) // 4

    for y in range(h):
        for x in range(w):
            dx = (x - cx)
            dy = (y - cy) * 2
            # Outer circle
            dist_outer = dx*dx + dy*dy
            # Inner circle (offset to create crescent)
            dx2 = (x - cx - radius // 2)
            dy2 = (y - cy) * 2
            dist_inner = dx2*dx2 + dy2*dy2

            r_outer_sq = (radius * 2) ** 2
            r_inner_sq = int((radius * 1.5) ** 2)

            if dist_outer <= r_outer_sq and dist_inner > r_inner_sq:
                grid[y][x] = crescent_color
            else:
                grid[y][x] = bg_color
    return grid


def pattern_star_field(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """Star on a field (like many national flags)."""
    grid = [[0]*w for _ in range(h)]
    bg_color = colors[0]
    star_color = colors[1]
    cx, cy = w // 2, h // 2
    outer_r = min(w, h) // 4
    inner_r = outer_r * 0.4
    n_points = 5

    # Precompute star polygon points
    star_points = []
    for i in range(n_points * 2):
        angle = math.pi / 2 + i * math.pi / n_points
        r = outer_r if i % 2 == 0 else inner_r
        star_points.append((cx + r * math.cos(angle) / 1.0,
                            cy - r * math.sin(angle) / 1.0 * 0.5))

    def point_in_star(px, py):
        # Ray casting algorithm
        n = len(star_points)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = star_points[i]
            xj, yj = star_points[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    for y in range(h):
        for x in range(w):
            if point_in_star(x, y):
                grid[y][x] = star_color
            else:
                grid[y][x] = bg_color
    return grid


def pattern_canton(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """Canton (small rectangle in upper hoist) on stripes (like USA, Liberia)."""
    # First generate horizontal stripes
    n_stripes = random.choice([3, 5, 7, 13])
    stripe_colors = []
    c_pool = pick_colors(2)
    for i in range(n_stripes):
        stripe_colors.append(c_pool[i % 2])
    grid = pattern_horizontal_stripes(w, h, stripe_colors, n_stripes)

    # Then overlay canton
    canton_color = colors[0]
    canton_w = w // 2
    canton_h = h // 2 if n_stripes > 5 else h // 3

    for y in range(min(canton_h, h)):
        for x in range(min(canton_w, w)):
            grid[y][x] = canton_color

    return grid


def pattern_diamond(w: int, h: int, colors: List[int]) -> List[List[int]]:
    """Central diamond shape (like flag of Nepal-ish, Rhodesia)."""
    grid = [[0]*w for _ in range(h)]
    bg_color = colors[0]
    diamond_color = colors[1]
    cx, cy = w // 2, h // 2

    for y in range(h):
        for x in range(w):
            # Manhattan distance from center, scaled for aspect
            dx = abs(x - cx) / (w / 2)
            dy = abs(y - cy) / (h / 2)
            if dx + dy <= 0.6:
                grid[y][x] = diamond_color
            else:
                grid[y][x] = bg_color
    return grid


# ─── Emblem overlays ──────────────────────────────────────────────────

def overlay_star(grid: List[List[int]], color: int, cx: int, cy: int, size: int = None):
    """Overlay a 5-pointed star on the grid."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    outer_r = size or min(w, h) // 6
    inner_r = outer_r * 0.4
    n_points = 5

    star_points = []
    for i in range(n_points * 2):
        angle = math.pi / 2 + i * math.pi / n_points
        r = outer_r if i % 2 == 0 else inner_r
        star_points.append((cx + r * math.cos(angle),
                            cy - r * math.sin(angle) * 0.5))

    def point_in_star(px, py):
        n = len(star_points)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = star_points[i]
            xj, yj = star_points[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    for y in range(h):
        for x in range(w):
            if point_in_star(x, y):
                grid[y][x] = color


def overlay_circle(grid: List[List[int]], color: int, cx: int, cy: int, radius: int = None):
    """Overlay a circle on the grid."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    r = radius or min(w, h) // 6

    for y in range(h):
        for x in range(w):
            dx = (x - cx)
            dy = (y - cy) * 2
            if dx*dx + dy*dy <= r*r * 4:
                grid[y][x] = color


def overlay_crescent(grid: List[List[int]], color: int, cx: int, cy: int, radius: int = None):
    """Overlay a crescent on the grid."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    r = radius or min(w, h) // 6

    for y in range(h):
        for x in range(w):
            dx = (x - cx)
            dy = (y - cy) * 2
            dist_outer = dx*dx + dy*dy

            dx2 = (x - cx - r // 2)
            dy2 = (y - cy) * 2
            dist_inner = dx2*dx2 + dy2*dy2

            r_outer_sq = (r * 2) ** 2
            r_inner_sq = int((r * 1.5) ** 2)

            if dist_outer <= r_outer_sq and dist_inner > r_inner_sq:
                grid[y][x] = color


def overlay_small_stars(grid: List[List[int]], color: int, n: int = 5):
    """Scatter n small stars on the grid."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0

    positions = []
    for _ in range(n):
        for attempt in range(20):
            sx = random.randint(w // 6, w - w // 6)
            sy = random.randint(h // 6, h - h // 6)
            # Check minimum distance from other stars
            ok = True
            for px, py in positions:
                if abs(sx - px) < w // 8 and abs(sy - py) < h // 8:
                    ok = False
                    break
            if ok:
                positions.append((sx, sy))
                break
        else:
            positions.append((random.randint(w // 6, w - w // 6),
                             random.randint(h // 6, h - h // 6)))

    for sx, sy in positions:
        overlay_star(grid, color, sx, sy, size=min(w, h) // 12)


# ─── Country name generator ──────────────────────────────────────────

PREFIXES = [
    "Northern", "Southern", "Eastern", "Western", "Greater", "Lesser",
    "Upper", "Lower", "New", "Old", "Grand", "Free", "United",
    "Democratic", "Federal", "Sovereign", "Ancient", "Noble",
    "Royal", "Sacred", "Golden", "Silver", "Iron", "Crimson",
    "Emerald", "Azure", "Amber", "Violet"
]

ROOTS = [
    "Alto", "Astra", "Vala", "Nova", "Lira", "Drak", "Mira",
    "Sola", "Terra", "Ventu", "Kora", "Nemi", "Rhu", "Zela",
    "Pela", "Arca", "Ori", "Feno", "Gala", "Thal", "Mora",
    "Bora", "Sana", "Delo", "Vira", "Luma", "Kena", "Asha",
    "Tano", "Rena", "Cala", "Duna", "Faro", "Gima", "Halo",
    "Iona", "Jura", "Kora", "Luma"
]

SUFFIXES = [
    "land", "nia", "ria", "stan", "burg", "ia", "heim", "gard",
    "dor", "mar", "ton", "vale", "mont", "mere", "ford", "wick",
    "dale", "fell", "haven", "reach", "crest", "moor", "shire",
    "land", " Isles", " Republic", " Federation"
]


def generate_country_name() -> str:
    """Generate a random fictional country name."""
    parts = []
    # 40% chance of prefix
    if random.random() < 0.4:
        parts.append(random.choice(PREFIXES))
    # Always have a root
    root = random.choice(ROOTS)
    # 60% chance of compounding roots
    if random.random() < 0.6:
        root2 = random.choice(ROOTS)
        if root2 != root:
            root = root + root2.lower()
    # Always have a suffix (80% chance)
    if random.random() < 0.8:
        suffix = random.choice(SUFFIXES)
        root = root + suffix
    parts.append(root)
    return " ".join(parts)


# ─── Flag generation ──────────────────────────────────────────────────

@dataclass
class Flag:
    name: str
    grid: List[List[int]]
    colors_used: List[int]
    pattern_type: str
    has_emblem: bool = False
    emblem_type: str = ""


def generate_flag(seed=None) -> Flag:
    """Generate a random flag."""
    if seed is not None:
        random.seed(seed)

    w, h = FLAG_W, FLAG_H

    # Choose a base pattern
    pattern_funcs = [
        ("horizontal_stripes", lambda: pattern_horizontal_stripes(w, h, pick_colors(random.choice([2, 3, 5])), random.choice([2, 3, 5]))),
        ("vertical_stripes", lambda: pattern_vertical_stripes(w, h, pick_colors(random.choice([2, 3])), random.choice([2, 3]))),
        ("diagonal", lambda: pattern_diagonal(w, h, pick_colors(2))),
        ("cross", lambda: pattern_cross(w, h, pick_colors(2))),
        ("saltire", lambda: pattern_saltire(w, h, pick_colors(2))),
        ("chevron", lambda: pattern_chevron(w, h, pick_colors(2))),
        ("quarters", lambda: pattern_quarters(w, h, pick_colors(4))),
        ("circle", lambda: pattern_circle(w, h, pick_colors(2))),
        ("crescent", lambda: pattern_crescent(w, h, pick_colors(2))),
        ("star", lambda: pattern_star_field(w, h, pick_colors(2))),
        ("canton", lambda: pattern_canton(w, h, pick_colors(3))),
        ("diamond", lambda: pattern_diamond(w, h, pick_colors(2))),
    ]

    pattern_name, pattern_fn = random.choice(pattern_funcs)
    grid = pattern_fn()

    # Collect base colors
    colors_used = list(set(cell for row in grid for cell in row))

    # 50% chance of adding an emblem overlay
    has_emblem = False
    emblem_type = ""
    emblem_color = random.choice(pick_colors(1))
    # Make sure emblem color contrasts with most common background
    from collections import Counter
    color_counts = Counter(cell for row in grid for cell in row)
    bg_color = color_counts.most_common(1)[0][0]
    if emblem_color == bg_color:
        emblem_color = random.choice(pick_colors(1, exclude=[bg_color]))

    if random.random() < 0.5:
        emblem_choice = random.choice(["star", "circle", "crescent", "stars"])
        cx = w // 2 + random.randint(-w // 8, w // 8)
        cy = h // 2 + random.randint(-h // 8, h // 8)

        if emblem_choice == "star":
            overlay_star(grid, emblem_color, cx, cy)
            has_emblem = True
            emblem_type = "star"
        elif emblem_choice == "circle":
            overlay_circle(grid, emblem_color, cx, cy)
            has_emblem = True
            emblem_type = "circle"
        elif emblem_choice == "crescent":
            overlay_crescent(grid, emblem_color, cx, cy)
            has_emblem = True
            emblem_type = "crescent"
        elif emblem_choice == "stars":
            n_stars = random.randint(3, 7)
            overlay_small_stars(grid, emblem_color, n_stars)
            has_emblem = True
            emblem_type = f"{n_stars} stars"

    # Update colors_used
    colors_used = list(set(cell for row in grid for cell in row))

    name = generate_country_name()

    return Flag(
        name=name,
        grid=grid,
        colors_used=sorted(colors_used),
        pattern_type=pattern_name,
        has_emblem=has_emblem,
        emblem_type=emblem_type,
    )


# ─── Rendering ───────────────────────────────────────────────────────

def render_flag(flag: Flag) -> str:
    """Render a Flag to a colored string using Unicode half-blocks for 2x vertical resolution."""
    grid = flag.grid
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    lines = []

    # Process rows in pairs for half-block rendering
    for y in range(0, h - 1, 2):
        row = []
        for x in range(w):
            top_color = grid[y][x]
            bot_color = grid[y + 1][x]
            if top_color == bot_color:
                # Same color: use full block
                row.append(f"{fg(top_color)}{BLOCK}")
            else:
                # Different colors: use half-block
                # ▀ shows top color as fg, bottom as bg
                row.append(f"{fg(top_color)}{bg(bot_color)}{HALF_TOP}")
        lines.append("".join(row) + RESET)

    # If odd number of rows, handle the last row
    if h % 2 == 1:
        row = []
        for x in range(w):
            row.append(f"{fg(grid[h-1][x])}{BLOCK}")
        lines.append("".join(row) + RESET)

    # Add flag name below
    name_str = f"  {flag.name}"
    lines.append("")
    lines.append(f"\033[1;37m{name_str}\033[0m")

    # Add pattern info
    info = f"  Pattern: {flag.pattern_type}"
    if flag.has_emblem:
        info += f" + {flag.emblem_type}"
    lines.append(f"\033[2;37m{info}\033[0m")

    # Add color legend
    legend = "  Colors: "
    for c in flag.colors_used:
        legend += f"{fg(c)}{BLOCK}{BLOCK}{BLOCK} {color_name(c)}  "
    legend += RESET
    lines.append(legend)

    return "\n".join(lines)


def render_flag_ascii(flag: Flag) -> str:
    """Render a Flag as simple ASCII art (for non-terminal contexts)."""
    grid = flag.grid
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0

    # Map colors to simple characters
    char_map = {}
    chars = "#@%&*+=~^:-."
    for i, c in enumerate(sorted(flag.colors_used)):
        char_map[c] = chars[i % len(chars)]

    lines = []
    # Draw border
    lines.append("+" + "-" * w + "+")
    for y in range(h):
        line = "|"
        for x in range(w):
            line += char_map.get(grid[y][x], "?")
        line += "|"
        lines.append(line)
    lines.append("+" + "-" * w + "+")
    lines.append(f"  {flag.name} ({flag.pattern_type})")

    return "\n".join(lines)


# ─── Gallery mode ─────────────────────────────────────────────────────

def render_gallery(n: int = 4, seed=None):
    """Render a gallery of n flags side by side."""
    if seed is not None:
        random.seed(seed)

    flags = [generate_flag() for _ in range(n)]

    # Render each flag and show them vertically
    for i, flag in enumerate(flags):
        if i > 0:
            print("\n")
        print(f"\033[1;36m═══ Flag {i+1} ═══\033[0m")
        print(render_flag(flag))

    return flags


# ─── Flag of the Day ──────────────────────────────────────────────────

def flag_of_the_day() -> Flag:
    """Generate a deterministic flag based on today's date."""
    import datetime
    today = datetime.date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    return generate_flag(seed=seed)


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Flag Generator - Create random fictional country flags!"
    )
    parser.add_argument("-n", "--count", type=int, default=1,
                        help="Number of flags to generate (default: 1)")
    parser.add_argument("-s", "--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("-g", "--gallery", action="store_true",
                        help="Generate a gallery of 4 flags")
    parser.add_argument("--daily", action="store_true",
                        help="Generate the flag of the day (deterministic)")
    parser.add_argument("--ascii", action="store_true",
                        help="Output as ASCII art instead of colored terminal")
    parser.add_argument("-W", "--width", type=int, default=60,
                        help="Flag width in characters (default: 60)")
    parser.add_argument("-H", "--height", type=int, default=40,
                        help="Flag height in characters (default: 40)")
    parser.add_argument("--name", type=str, default=None,
                        help="Custom country name")

    args = parser.parse_args()

    global FLAG_W, FLAG_H
    FLAG_W = args.width
    FLAG_H = args.height

    if args.gallery:
        render_gallery(n=4, seed=args.seed)
        return

    if args.daily:
        flag = flag_of_the_day()
    else:
        flag = generate_flag(seed=args.seed)

    if args.name:
        flag.name = args.name

    if args.count > 1:
        flags = [flag]
        for i in range(1, args.count):
            flags.append(generate_flag())
        for i, f in enumerate(flags):
            if i > 0:
                print("\n")
            print(f"\033[1;36m═══ Flag {i+1} ═══\033[0m")
            if args.ascii:
                print(render_flag_ascii(f))
            else:
                print(render_flag(f))
    else:
        if args.ascii:
            print(render_flag_ascii(flag))
        else:
            print(render_flag(flag))


if __name__ == "__main__":
    main()