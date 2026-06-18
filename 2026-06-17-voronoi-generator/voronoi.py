#!/usr/bin/env python3
"""
ASCII Voronoi Diagram Generator

Generates beautiful Voronoi tessellations in the terminal using Unicode
block characters and ANSI 256-color mode. Supports multiple distance metrics,
seed placement strategies, and rendering modes.

A Voronoi diagram partitions a plane into regions based on distance to
a set of "seed" points — each region contains all points closer to its
seed than to any other.
"""

__version__ = "1.1.0"

import argparse
import math
import os
import random
import sys
import time

# ── ANSI Utilities ──────────────────────────────────────────────────────────

ESC = "\033["

def ansi_fg(idx):
    """ANSI 256-color foreground escape."""
    return f"{ESC}38;5;{idx}m"

def ansi_bg(idx):
    """ANSI 256-color background escape."""
    return f"{ESC}48;5;{idx}m"

RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"

# Unicode block characters for sub-cell resolution (top/bottom half blocks)
UPPER_HALF = "▀"
LOWER_HALF = "▄"
FULL_BLOCK = "█"

# ── Color Palettes ───────────────────────────────────────────────────────────

def palette_rainbow(n):
    """Generate n evenly-spaced colors around the hue wheel."""
    colors = []
    for i in range(n):
        h = (i / n) * 360
        r, g, b = _hsv_to_rgb(h, 0.85, 0.9)
        colors.append(_rgb_to_256(r, g, b))
    return colors

def palette_pastel(n):
    """Soft pastel palette."""
    colors = []
    for i in range(n):
        h = (i / n) * 360
        r, g, b = _hsv_to_rgb(h, 0.4, 0.95)
        colors.append(_rgb_to_256(r, g, b))
    return colors

def palette_neon(n):
    """Bright neon palette on dark backgrounds."""
    colors = []
    for i in range(n):
        h = (i / n) * 360
        r, g, b = _hsv_to_rgb(h, 1.0, 1.0)
        colors.append(_rgb_to_256(r, g, b))
    return colors

def palette_earth(n):
    """Earthy tones — browns, greens, blues."""
    base_hues = [30, 45, 60, 90, 120, 180, 200, 220]
    colors = []
    for i in range(n):
        h = base_hues[i % len(base_hues)] + random.uniform(-10, 10)
        s = random.uniform(0.4, 0.7)
        v = random.uniform(0.5, 0.8)
        r, g, b = _hsv_to_rgb(h % 360, s, v)
        colors.append(_rgb_to_256(r, g, b))
    return colors

def palette_ocean(n):
    """Ocean blues and greens."""
    colors = []
    for i in range(n):
        h = 170 + (i / n) * 70  # 170-240
        s = 0.6 + 0.3 * math.sin(i * 0.7)
        v = 0.5 + 0.4 * math.sin(i * 0.5)
        r, g, b = _hsv_to_rgb(h, min(s, 1), min(v, 1))
        colors.append(_rgb_to_256(r, g, b))
    return colors

def palette_fire(n):
    """Reds, oranges, yellows."""
    colors = []
    for i in range(n):
        h = (i / n) * 60  # 0-60
        s = 0.8 + 0.2 * math.sin(i)
        v = 0.7 + 0.3 * math.cos(i * 0.8)
        r, g, b = _hsv_to_rgb(h, min(s, 1), min(v, 1))
        colors.append(_rgb_to_256(r, g, b))
    return colors

PALETTES = {
    "rainbow": palette_rainbow,
    "pastel": palette_pastel,
    "neon": palette_neon,
    "earth": palette_earth,
    "ocean": palette_ocean,
    "fire": palette_fire,
}

# ── Color Math ───────────────────────────────────────────────────────────────

def _hsv_to_rgb(h, s, v):
    """HSV (h in degrees, s/v in 0-1) → RGB (0-255 each)."""
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:    r1, g1, b1 = c, x, 0
    elif h < 120: r1, g1, b1 = x, c, 0
    elif h < 180: r1, g1, b1 = 0, c, x
    elif h < 240: r1, g1, b1 = 0, x, c
    elif h < 300: r1, g1, b1 = x, 0, c
    else:         r1, g1, b1 = c, 0, x
    return int((r1+m)*255), int((g1+m)*255), int((b1+m)*255)

def _rgb_to_256(r, g, b):
    """Map an RGB color to the nearest ANSI 256-color index."""
    # Use the 6x6x6 color cube (indices 16-231)
    best = 16
    best_dist = float('inf')
    for i in range(16, 232):
        cr = ((i - 16) // 36) * 51
        cg = (((i - 16) % 36) // 6) * 51
        cb = ((i - 16) % 6) * 51
        d = (r - cr)**2 + (g - cg)**2 + (b - cb)**2
        if d < best_dist:
            best_dist = d
            best = i
    return best

# ── Distance Metrics ────────────────────────────────────────────────────────

def dist_euclidean(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def dist_manhattan(x1, y1, x2, y2):
    return abs(x1-x2) + abs(y1-y2)

def dist_chebyshev(x1, y1, x2, y2):
    return max(abs(x1-x2), abs(y1-y2))

def dist_minkowski3(x1, y1, x2, y2):
    return (abs(x1-x2)**3 + abs(y1-y2)**3) ** (1/3)

def dist_cosine(x1, y1, x2, y2):
    """Angle-based distance — treats points as vectors from origin.

    For zero-magnitude vectors (origin point), falls back to Euclidean
    distance to avoid degenerate cosine values.
    """
    m1_sq = x1*x1 + y1*y1
    m2_sq = x2*x2 + y2*y2
    # If either vector has zero magnitude, cosine similarity is undefined;
    # fall back to Euclidean distance (normalized) to give a sensible result.
    if m1_sq < 1e-20 or m2_sq < 1e-20:
        return math.sqrt((x1-x2)**2 + (y1-y2)**2)
    dot = x1*x2 + y1*y2
    cos_sim = dot / (math.sqrt(m1_sq) * math.sqrt(m2_sq))
    # Clamp to [-1, 1] to handle floating-point drift
    cos_sim = max(-1.0, min(1.0, cos_sim))
    return 1 - cos_sim  # cosine distance

DISTANCES = {
    "euclidean": dist_euclidean,
    "manhattan": dist_manhattan,
    "chebyshev": dist_chebyshev,
    "minkowski3": dist_minkowski3,
    "cosine": dist_cosine,
}

# ── Seed Generators ─────────────────────────────────────────────────────────

def seeds_random(n, w, h):
    """Random uniform placement."""
    return [(random.uniform(0, w), random.uniform(0, h)) for _ in range(n)]

def seeds_grid(n, w, h):
    """Approximate grid with jitter."""
    cols = max(1, int(math.sqrt(n * w / h)))
    rows = max(1, math.ceil(n / cols))
    seeds = []
    for r in range(rows):
        for c in range(cols):
            if len(seeds) >= n:
                break
            x = (c + 0.5) * w / cols + random.uniform(-w/(3*cols), w/(3*cols))
            y = (r + 0.5) * h / rows + random.uniform(-h/(3*rows), h/(3*rows))
            seeds.append((x, y))
    return seeds[:n]

def seeds_circular(n, w, h):
    """Seeds arranged in concentric circles."""
    cx, cy = w / 2, h / 2
    seeds = [(cx, cy)] if n > 0 else []
    remaining = n - 1
    ring = 1
    while remaining > 0:
        count = min(remaining, ring * 6)
        for i in range(count):
            angle = 2 * math.pi * i / count
            radius = ring * min(w, h) / (2 * math.sqrt(n) + 2)
            seeds.append((cx + radius * math.cos(angle),
                          cy + radius * math.sin(angle)))
        remaining -= count
        ring += 1
    return seeds

def seeds_spiral(n, w, h):
    """Seeds along a Fibonacci/golden spiral."""
    cx, cy = w / 2, h / 2
    seeds = []
    golden_angle = math.pi * (3 - math.sqrt(5))
    scale = min(w, h) / (2 * math.sqrt(n) + 2)
    for i in range(n):
        r = scale * math.sqrt(i)
        theta = i * golden_angle
        seeds.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
    return seeds

def seeds_clusters(n, w, h):
    """Clustered seeds — a few cluster centers with points nearby."""
    n_clusters = max(3, n // 5)
    centers = [(random.uniform(w*0.1, w*0.9), random.uniform(h*0.1, h*0.9))
               for _ in range(n_clusters)]
    seeds = []
    for i in range(n):
        cx, cy = random.choice(centers)
        seeds.append((cx + random.gauss(0, w/20), cy + random.gauss(0, h/20)))
    return seeds

SEED_TYPES = {
    "random": seeds_random,
    "grid": seeds_grid,
    "circular": seeds_circular,
    "spiral": seeds_spiral,
    "clusters": seeds_clusters,
}

# ── Voronoi Computation ──────────────────────────────────────────────────────

def compute_voronoi(seeds, width, height, dist_fn, metric="euclidean"):
    """
    Compute Voronoi cell indices for each pixel position.
    Returns a 2D list where each element is the index of the closest seed.
    Returns an empty list if there are no seeds or dimensions are zero.
    """
    if not seeds or width <= 0 or height <= 0:
        return []
    grid = []
    for y in range(height):
        row = []
        for x in range(width):
            best_idx = 0
            best_dist = float('inf')
            for i, (sx, sy) in enumerate(seeds):
                d = dist_fn(x, y, sx, sy)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            row.append(best_idx)
        grid.append(row)
    return grid

def compute_voronoi_with_distance(seeds, width, height, dist_fn):
    """
    Compute Voronoi cell indices AND distance to nearest seed for each pixel.
    Returns (grid, dist_grid) — both are 2D lists.
    Returns ([], []) if there are no seeds or dimensions are zero.
    """
    if not seeds or width <= 0 or height <= 0:
        return [], []
    grid = []
    dist_grid = []
    for y in range(height):
        row = []
        drow = []
        for x in range(width):
            best_idx = 0
            best_dist = float('inf')
            for i, (sx, sy) in enumerate(seeds):
                d = dist_fn(x, y, sx, sy)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            row.append(best_idx)
            drow.append(best_dist)
        grid.append(row)
        dist_grid.append(drow)
    return grid, dist_grid

# ── Rendering ────────────────────────────────────────────────────────────────

def render_block(colors, grid, dist_grid, width, height, mode="filled",
                 show_borders=True, show_seeds=False, seeds=None):
    """
    Render the Voronoi diagram using Unicode half-block characters.
    Each terminal character cell represents 2 vertical pixels (upper + lower),
    giving us double vertical resolution.

    Returns an empty list if there are no colors or no grid data.
    """
    if not colors or not grid or width <= 0 or height <= 0:
        return []
    lines = []
    # Determine number of terminal rows (half the pixel rows)
    term_rows = (height + 1) // 2

    for ty in range(term_rows):
        py_upper = ty * 2
        py_lower = ty * 2 + 1
        line = ""
        for tx in range(width):
            # Upper pixel
            if py_upper < height:
                idx_up = grid[py_upper][tx]
                color_up = colors[idx_up % len(colors)]
                d_up = dist_grid[py_upper][tx] if dist_grid else 0
            else:
                idx_up = grid[height-1][tx] if height > 0 else 0
                color_up = colors[idx_up % len(colors)]
                d_up = 0

            # Lower pixel
            if py_lower < height:
                idx_lo = grid[py_lower][tx]
                color_lo = colors[idx_lo % len(colors)]
                d_lo = dist_grid[py_lower][tx] if dist_grid else 0
            else:
                idx_lo = idx_up
                color_lo = color_up
                d_lo = d_up

            # Border detection: is this pixel on a cell boundary?
            is_border_up = False
            is_border_lo = False

            if show_borders and py_upper < height and dist_grid:
                idx = grid[py_upper][tx]
                for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                    ny, nx = py_upper+dy, tx+dx
                    if 0 <= ny < height and 0 <= nx < width:
                        if grid[ny][nx] != idx:
                            is_border_up = True
                            break

            if show_borders and py_lower < height and dist_grid:
                idx = grid[py_lower][tx]
                for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                    ny, nx = py_lower+dy, tx+dx
                    if 0 <= ny < height and 0 <= nx < width:
                        if grid[ny][nx] != idx:
                            is_border_lo = True
                            break

            # Apply rendering mode
            fg_up = 231 if is_border_up else (color_up if mode != "outline" else 16)
            bg_lo = 231 if is_border_lo else (color_lo if mode != "outline" else 16)

            if mode == "outline":
                # In outline mode, only borders are colored
                if is_border_up:
                    fg_up = color_up
                else:
                    fg_up = 16  # black
                if is_border_lo:
                    bg_lo = color_lo
                else:
                    bg_lo = 16

            # Use upper-half block: foreground = upper pixel, background = lower pixel
            line += f"{ansi_fg(fg_up)}{ansi_bg(bg_lo)}{UPPER_HALF}"

        line += RESET
        lines.append(line)

    # Draw seed markers on top if requested
    if show_seeds and seeds:
        # We overlay seed markers after rendering
        pass  # handled separately

    return lines

def render_seed_markers(seeds, width, height, colors, term_width=None):
    """
    Create ANSI escape sequences to place seed markers at their positions.
    Returns a list of (row, col, marker_string) for overlaying.
    """
    markers = []
    for i, (sx, sy) in enumerate(seeds):
        tx = int(sx)
        ty = int(sy) // 2  # half-block compression
        if 0 <= tx < width and 0 <= ty < (height + 1) // 2:
            c = colors[i % len(colors)]
            # Use a bright contrasting marker
            markers.append((ty, tx, f"{BOLD}{ansi_fg(231)}{ansi_bg(c)}+{RESET}"))
    return markers

# ── Animation ────────────────────────────────────────────────────────────────

def animate_voronoi(seeds, width, height, dist_fn, colors, args):
    """
    Animate seeds moving and Voronoi cells updating in real time.
    """
    # Make copies that we'll move
    seed_x = [s[0] for s in seeds]
    seed_y = [s[1] for s in seeds]
    vx = [random.uniform(-0.5, 0.5) for _ in seeds]
    vy = [random.uniform(-0.3, 0.3) for _ in seeds]

    # Hide cursor
    sys.stdout.write(f"{ESC}?25l")
    sys.stdout.flush()

    try:
        frame = 0
        while True:
            # Move seeds
            for i in range(len(seeds)):
                seed_x[i] += vx[i]
                seed_y[i] += vy[i]

                # Bounce off walls
                if seed_x[i] < 0 or seed_x[i] >= width:
                    vx[i] *= -1
                    seed_x[i] = max(0, min(width - 1, seed_x[i]))
                if seed_y[i] < 0 or seed_y[i] >= height:
                    vy[i] *= -1
                    seed_y[i] = max(0, min(height - 1, seed_y[i]))

                # Add slight random drift
                vx[i] += random.uniform(-0.05, 0.05)
                vy[i] += random.uniform(-0.05, 0.05)
                # Dampen to prevent runaway
                vx[i] *= 0.99
                vy[i] *= 0.99

            cur_seeds = list(zip(seed_x, seed_y))
            grid, dist_grid = compute_voronoi_with_distance(
                cur_seeds, width, height, dist_fn)

            lines = render_block(colors, grid, dist_grid, width, height,
                                  mode=args.mode, show_borders=args.borders,
                                  show_seeds=False, seeds=cur_seeds)

            # Add seed markers
            markers = render_seed_markers(cur_seeds, width, height, colors)

            # Move cursor to top-left and redraw
            output = f"{ESC}H"  # cursor home
            for line in lines:
                output += line + "\n"

            # Overlay seed markers (simplified: just add info line)
            info = f"{DIM}Seeds: {len(cur_seeds)} | Frame: {frame} | "
            info += f"Metric: {args.distance} | Press Ctrl+C to stop{RESET}"
            output += info

            sys.stdout.write(output)
            sys.stdout.flush()

            frame += 1
            time.sleep(args.delay)

    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(f"{ESC}?25h")  # show cursor
        sys.stdout.write(f"\n{RESET}")
        sys.stdout.flush()

# ── Static Render ────────────────────────────────────────────────────────────

def render_static(seeds, width, height, dist_fn, colors, args):
    """Render a single static Voronoi diagram."""
    grid, dist_grid = compute_voronoi_with_distance(seeds, width, height, dist_fn)

    lines = render_block(colors, grid, dist_grid, width, height,
                         mode=args.mode, show_borders=args.borders,
                         show_seeds=args.seeds, seeds=seeds)

    # Overlay seed markers
    if args.seeds:
        markers = render_seed_markers(seeds, width, height, colors)
        # Re-render with markers overlay (simplified: print markers info)
        seed_info = f"{DIM}Seed positions:{RESET}\n"
        for i, (sx, sy) in enumerate(seeds):
            c = colors[i % len(colors)]
            seed_info += f"  {ansi_fg(c)}●{RESET} Seed {i}: ({sx:.1f}, {sy:.1f})\n"
        lines.append("")
        lines.append(seed_info)

    return lines

# ── Main ─────────────────────────────────────────────────────────────────────

def get_terminal_size():
    """Get terminal width and height."""
    try:
        cols, rows = os.get_terminal_size()
        return cols, rows
    except OSError:
        return 80, 24

def main():
    parser = argparse.ArgumentParser(
        description="Generate beautiful Voronoi diagrams in the terminal!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Random Voronoi, default settings
  %(prog)s --seeds 20 --palette neon --distance manhattan
  %(prog)s --seeds 50 --seed-type spiral --animate
  %(prog)s --seeds 15 --mode outline --borders --palette fire
  %(prog)s --seeds 30 --distance chebyshev --palette ocean --animate --delay 0.1
        """)
    parser.add_argument("-n", "--seeds", type=int, default=15,
                        help="Number of seed points (default: 15)")
    parser.add_argument("-w", "--width", type=int, default=None,
                        help="Terminal width in columns (default: auto-detect)")
    parser.add_argument("-H", "--height", type=int, default=None,
                        help="Pixel height (default: 2x terminal rows)")
    parser.add_argument("-d", "--distance", choices=list(DISTANCES.keys()),
                        default="euclidean",
                        help="Distance metric (default: euclidean)")
    parser.add_argument("-s", "--seed-type", choices=list(SEED_TYPES.keys()),
                        default="random",
                        help="Seed placement pattern (default: random)")
    parser.add_argument("-p", "--palette", choices=list(PALETTES.keys()),
                        default="rainbow",
                        help="Color palette (default: rainbow)")
    parser.add_argument("-m", "--mode", choices=["filled", "outline"],
                        default="filled",
                        help="Rendering mode (default: filled)")
    parser.add_argument("-b", "--borders", action="store_true",
                        help="Highlight cell borders with white edges")
    parser.add_argument("--seeds-visible", dest="seeds", action="store_true",
                        help="Show seed point markers")
    parser.add_argument("-a", "--animate", action="store_true",
                        help="Animate seeds moving in real time")
    parser.add_argument("--delay", type=float, default=0.08,
                        help="Animation frame delay in seconds (default: 0.08)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--version", action="version", version=f"voronoi {__version__}")

    args = parser.parse_args()

    # Validate inputs
    if args.seeds < 1:
        parser.error(f"Number of seeds must be at least 1, got {args.seeds}")
    if args.delay <= 0:
        parser.error(f"Frame delay must be positive, got {args.delay}")

    if args.seed is not None:
        random.seed(args.seed)

    # Terminal dimensions
    term_w, term_h = get_terminal_size()
    width = args.width or (term_w - 1)
    height = args.height or ((term_h - 2) * 2)  # double resolution via half-blocks

    # Validate dimensions
    if width < 1:
        parser.error(f"Width must be at least 1, got {width}")
    if height < 1:
        parser.error(f"Height must be at least 1, got {height}")

    # Generate seeds
    seed_gen = SEED_TYPES[args.seed_type]
    seeds = seed_gen(args.seeds, width, height)

    # Generate colors
    color_gen = PALETTES[args.palette]
    colors = color_gen(args.seeds)

    # Distance function
    dist_fn = DISTANCES[args.distance]

    # Clear screen
    sys.stdout.write(f"{ESC}2J{ESC}H")
    sys.stdout.flush()

    if args.animate:
        animate_voronoi(seeds, width, height, dist_fn, colors, args)
    else:
        lines = render_static(seeds, width, height, dist_fn, colors, args)
        for line in lines:
            print(line)

        # Print legend
        print(f"\n{DIM}Voronoi Diagram │ Seeds: {args.seeds} │ "
              f"Metric: {args.distance} │ Pattern: {args.seed_type} │ "
              f"Palette: {args.palette}{RESET}")

        # Show color legend
        print(f"{DIM}Cell colors:{RESET} ", end="")
        for i, c in enumerate(colors):
            print(f"{ansi_fg(c)}●{RESET}", end=" ")
        print()

if __name__ == "__main__":
    main()