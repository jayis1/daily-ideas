#!/usr/bin/env python3
"""
Procedural Inkblot Generator
=============================
Generates Rorschach-style symmetric inkblots using procedural noise,
rendered as Braille art in the terminal. Each run produces a unique
inkblot with a whimsical psychological interpretation.

Usage:
    python inkblot.py                  # Random inkblot
    python inkblot.py --seed 42        # Reproducible inkblot
    python inkblot.py --width 100      # Wider output
    python inkblot.py --style splash   # Different inkblot style
    python inkblot.py --no-interpret   # Skip the interpretation
    python inkblot.py --animate        # Animate the blot forming
"""

import argparse
import math
import random
import sys
import time
import os

# ─── Braille constants ───────────────────────────────────────────────
# Braille characters encode a 2×4 grid of dots into a single Unicode char.
# Columns: col0 = bits 0,3; col1 = bits 1,4; row offsets in each column.
BRAILLE_MAP = {
    (r, c): (1 << (r + c * 4))  # dot (row r, col c) → bit index
    for c in range(2) for r in range(4)
}
BRAILLE_BASE = 0x2800


def pixels_to_braille(grid, height, width):
    """Convert a 2D boolean grid (row-major) into Braille art strings."""
    # Grid is height×width pixels; Braille chars are 2 wide × 4 tall
    lines = []
    for by in range(0, height, 4):
        row_str = ""
        for bx in range(0, width, 2):
            code = 0
            for r in range(4):
                for c in range(2):
                    px, py = bx + c, by + r
                    if 0 <= py < height and 0 <= px < width and grid[py][px]:
                        code |= BRAILLE_MAP[(r, c)]
            row_str += chr(BRAILLE_BASE + code)
        lines.append(row_str)
    return lines


# ─── Value noise ──────────────────────────────────────────────────────
def _lerp(a, b, t):
    return a + (b - a) * t


def _smooth(t):
    return t * t * (3 - 2 * t)


def _hash2d(x, y, seed):
    """Cheap 2D hash returning a float in [0, 1)."""
    n = (x * 374761393 + y * 668265263 + seed * 1013904223) & 0xFFFFFFFF
    n = ((n >> 13) ^ n) & 0xFFFFFFFF
    n = (n * (n * n * 15731 + 789221) + 1376312589) & 0xFFFFFFFF
    return (n & 0xFFFF) / 0xFFFF


def value_noise(x, y, seed):
    """2D value noise with smooth interpolation."""
    ix, iy = int(math.floor(x)), int(math.floor(y))
    fx, fy = _smooth(x - ix), _smooth(y - iy)
    n00 = _hash2d(ix, iy, seed)
    n10 = _hash2d(ix + 1, iy, seed)
    n01 = _hash2d(ix, iy + 1, seed)
    n11 = _hash2d(ix + 1, iy + 1, seed)
    return _lerp(_lerp(n00, n10, fx), _lerp(n01, n11, fx), fy)


def fbm(x, y, seed, octaves=4, lacunarity=2.0, gain=0.5):
    """Fractal Brownian Motion – layered value noise."""
    value, amplitude, frequency = 0.0, 1.0, 1.0
    for i in range(octaves):
        value += amplitude * value_noise(x * frequency, y * frequency, seed + i * 31)
        amplitude *= gain
        frequency *= lacunarity
    return value


# ─── Inkblot generators ──────────────────────────────────────────────

def _mirror_horizontal(grid, height, width):
    """Mirror left half to right half."""
    for y in range(height):
        for x in range(width // 2, width):
            grid[y][x] = grid[y][width - 1 - x]


def _mirror_vertical(grid, height, width):
    """Mirror top half to bottom half."""
    for y in range(height // 2, height):
        for x in range(width):
            grid[y][x] = grid[height - 1 - y][x]


def generate_splash(height, width, seed, rng):
    """Classic Rorschach: symmetric blobs using noise with threshold."""
    grid = [[False] * width for _ in range(height)]
    cx, cy = width / 2, height / 2

    for y in range(height):
        for x in range(width // 2 + 1):  # only generate left half
            # Distance from center influences probability
            dx = (x - cx) / (width / 2)
            dy = (y - cy) / (height / 2)
            dist = math.sqrt(dx * dx + dy * dy)

            # Multi-scale noise
            n1 = fbm(x * 0.08, y * 0.08, seed)
            n2 = fbm(x * 0.04, y * 0.04, seed + 100)
            n3 = fbm(x * 0.15, y * 0.15, seed + 200)

            # Combine noise layers
            combined = n1 * 0.4 + n2 * 0.35 + n3 * 0.25

            # Radial falloff – blots are denser in the center
            falloff = max(0, 1.0 - dist * 0.8)
            combined *= falloff

            # Add some blob structures
            blob = math.sin(x * 0.1 + n1 * 3) * math.cos(y * 0.1 + n2 * 3)
            combined += blob * 0.15

            threshold = rng.uniform(0.25, 0.45)
            grid[y][x] = combined > threshold

    _mirror_horizontal(grid, height, width)
    return grid


def generate_radial(height, width, seed, rng):
    """Radial spokes pattern – like a butterfly or dendrite."""
    grid = [[False] * width for _ in range(height)]
    cx, cy = width / 2, height / 2
    num_spokes = rng.randint(3, 8)

    for y in range(height):
        for x in range(width // 2 + 1):
            dx = (x - cx)
            dy = (y - cy)
            angle = math.atan2(dy, dx)
            dist = math.sqrt(dx * dx + dy * dy) / min(width, height)

            # Create spoke pattern
            spoke = (math.cos(angle * num_spokes) + 1) / 2
            noise_val = fbm(x * 0.06, y * 0.06, seed)
            noise_val2 = fbm(x * 0.12, y * 0.12, seed + 50)

            combined = spoke * 0.5 + noise_val * 0.3 + noise_val2 * 0.2
            combined *= max(0, 1.0 - dist * 1.2)

            # Add organic wobble to spokes
            wobble = fbm(math.cos(angle) * 2, math.sin(angle) * 2, seed + 99)
            combined += wobble * 0.2

            threshold = rng.uniform(0.3, 0.5)
            grid[y][x] = combined > threshold

    _mirror_horizontal(grid, height, width)
    return grid


def generate_cellular(height, width, seed, rng):
    """Cell / voronoi-like pattern – organic cellular structures."""
    grid = [[False] * width for _ in range(height)]
    num_cells = rng.randint(8, 20)

    # Generate random cell centers (left half only)
    cells = [(rng.uniform(0, width / 2), rng.uniform(0, height)) for _ in range(num_cells)]

    for y in range(height):
        for x in range(width // 2 + 1):
            # Find distance to nearest two cells
            distances = sorted(math.sqrt((x - cx) ** 2 + (y - cy) ** 2) for cx, cy in cells)
            d1 = distances[0] if distances else 999
            d2 = distances[1] if len(distances) > 1 else 999

            # Edge detection: thin borders between cells
            edge_ratio = d2 / max(d1, 0.01)
            # When d1 ≈ d2, we're on a cell boundary (edge_ratio ≈ 1)
            # When d1 << d2, we're deep inside a cell (edge_ratio >> 1)
            is_boundary = edge_ratio < 1.15  # close to boundary

            noise_val = fbm(x * 0.05, y * 0.05, seed)

            # Draw boundaries thickened by noise
            combined = 0.0
            if is_boundary:
                combined = 0.7 + noise_val * 0.3
            else:
                # Sparse interior fill using noise
                if noise_val > 0.7:
                    combined = (noise_val - 0.7) * 2.0

            threshold = rng.uniform(0.35, 0.5)
            grid[y][x] = combined > threshold

    _mirror_horizontal(grid, height, width)
    return grid


def generate_organic(height, width, seed, rng):
    """Worm-like tendrils emanating from center."""
    grid = [[False] * width for _ in range(height)]
    cx, cy = width / 2, height / 2
    num_tendrils = rng.randint(4, 10)

    for y in range(height):
        for x in range(width // 2 + 1):
            dx = (x - cx)
            dy = (y - cy)
            dist = math.sqrt(dx * dx + dy * dy)
            angle = math.atan2(dy, dx)

            # Each tendril is a warped sine function of angle
            tendril_val = 0.0
            for t in range(num_tendrils):
                phase = t * math.pi * 2 / num_tendrils + fbm(t, t, seed) * 2
                width_mod = 0.3 + fbm(t * 0.5, 0, seed + 300) * 0.2
                tendril = math.cos(angle - phase)
                tendril_val = max(tendril_val, tendril * width_mod)

            noise1 = fbm(x * 0.08, y * 0.08, seed)
            noise2 = fbm(x * 0.15, y * 0.15, seed + 77)
            combined = tendril_val * 0.5 + noise1 * 0.3 + noise2 * 0.2

            # Radial envelope
            max_dist = min(width, height) * 0.45
            envelope = max(0, 1.0 - (dist / max_dist) ** 1.5)
            combined *= envelope

            threshold = rng.uniform(0.25, 0.4)
            grid[y][x] = combined > threshold

    _mirror_horizontal(grid, height, width)
    return grid


def generate_both_mirror(height, width, seed, rng):
    """Mirror on both axes – creates a 4-fold symmetric pattern."""
    half_h = height // 2
    half_w = width // 2

    # Generate just the top-left quadrant
    quadrant = [[False] * half_w for _ in range(half_h)]
    for y in range(half_h):
        for x in range(half_w):
            n1 = fbm(x * 0.07, y * 0.07, seed)
            n2 = fbm(x * 0.14, y * 0.14, seed + 200)
            n3 = fbm(x * 0.03, y * 0.03, seed + 400)

            # Distance from quadrant corner
            dx = (half_w - x) / half_w
            dy = (half_h - y) / half_h
            dist = math.sqrt(dx * dx + dy * dy)

            combined = (n1 * 0.4 + n2 * 0.35 + n3 * 0.25) * max(0, 1.0 - dist * 0.6)
            threshold = rng.uniform(0.25, 0.42)
            quadrant[y][x] = combined > threshold

    # Tile into full image
    grid = [[False] * width for _ in range(height)]
    for y in range(half_h):
        for x in range(half_w):
            # Top-left
            grid[y][x] = quadrant[y][x]
            # Top-right (mirror)
            grid[y][width - 1 - x] = quadrant[y][x]
            # Bottom-left (mirror vertical)
            grid[height - 1 - y][x] = quadrant[y][x]
            # Bottom-right (mirror both)
            grid[height - 1 - y][width - 1 - x] = quadrant[y][x]

    return grid


STYLES = {
    "splash": generate_splash,
    "radial": generate_radial,
    "cellular": generate_cellular,
    "organic": generate_organic,
    "mirror4": generate_both_mirror,
}


# ─── Interpretations ─────────────────────────────────────────────────

INTERPRETATIONS = {
    "emotions": [
        "a sense of unresolved conflict with authority",
        "deep-seated longing for transformation",
        "the duality of your creative and analytical selves",
        "a hidden desire for symmetry and balance in life",
        "repressed feelings trying to find an outlet",
        "the tension between freedom and structure",
        "an unconscious need for connection and intimacy",
        "a battle between your inner child and adult self",
        "the fragile bridge between dreams and reality",
        "an echo of something important you've forgotten",
    ],
    "objects": [
        "two dancers frozen mid-waltz",
        "a butterfly emerging from darkness",
        "twin faces in quiet conversation",
        "an ancient tree with mirrored branches",
        "a skull with glowing eyes",
        "two hands reaching toward each other",
        "a crown dissolving into shadow",
        "wings of a vast, sleeping moth",
        "the silhouette of a sleeping cat",
        "a chalice overflowing with ink",
    ],
    "advice": [
        "You should trust your instincts more today.",
        "Now is the time to embrace change – the inkblot never stays the same.",
        "Symmetry suggests balance. Seek equilibrium in your decisions.",
        "The patterns suggest complexity beneath the surface. Look deeper.",
        "Your perception is unique. Don't let others define what you see.",
        "The blots are reaching outward. So should you.",
        "Darkness and light coexist here. Accept both within yourself.",
        "The center holds. Remember what anchors you.",
        "What you see shapes what you get. Choose your perspective wisely.",
        "The edges blur. Not everything needs a sharp definition.",
    ],
}


def generate_interpretation(seed, rng):
    """Generate a whimsical Rorschach-style interpretation."""
    emotion = rng.choice(INTERPRETATIONS["emotions"])
    obj = rng.choice(INTERPRETATIONS["objects"])
    advice = rng.choice(INTERPRETATIONS["advice"])

    return (
        f"  You see {obj}.\n"
        f"  This suggests {emotion}.\n"
        f"  {advice}"
    )


# ─── Animation ────────────────────────────────────────────────────────

def animate_inkblot(grid, height, width, fps=12):
    """Animate the inkblot forming by progressively revealing rows."""
    # Create a gradually-filling sequence
    total_rows = (height + 3) // 4  # Braille rows
    all_lines = pixels_to_braille(grid, height, width)

    # Clear screen
    ESC = "\033["
    print(f"{ESC}2J{ESC}H", end="")

    for reveal_row in range(1, total_rows + 1):
        # Move cursor to top
        print(f"{ESC}H", end="")
        for i, line in enumerate(all_lines):
            if i < reveal_row:
                print(line)
            else:
                print()
        time.sleep(1.0 / fps)

    # Final pause
    time.sleep(0.5)


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Rorschach Inkblot Generator – Braille Art Edition"
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--width", type=int, default=80, help="Output width in Braille chars (default: 80)")
    parser.add_argument("--height", type=int, default=None, help="Output height in pixel rows (default: auto)")
    parser.add_argument("--style", choices=list(STYLES.keys()), default=None,
                        help="Inkblot style: splash, radial, cellular, organic, mirror4")
    parser.add_argument("--no-interpret", action="store_true", help="Skip psychological interpretation")
    parser.add_argument("--animate", action="store_true", help="Animate the blot forming")
    parser.add_argument("--list-styles", action="store_true", help="List available styles and exit")
    args = parser.parse_args()

    if args.list_styles:
        print("Available inkblot styles:")
        for name, func in STYLES.items():
            print(f"  {name:12s} – {(func.__doc__ or '').strip()}")
        return

    # Set up RNG
    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    rng = random.Random(seed)
    style = args.style or rng.choice(list(STYLES.keys()))

    # Calculate dimensions
    # Braille chars are 2px wide × 4px tall; width is in Braille chars
    pixel_width = args.width * 2
    pixel_height = args.height or (pixel_width // 2)  # ~2:1 aspect
    # Make pixel_height divisible by 4
    pixel_height = (pixel_height // 4) * 4

    # Generate the inkblot
    generator = STYLES[style]
    grid = generator(pixel_height, pixel_width, seed, rng)

    # Render
    lines = pixels_to_braille(grid, pixel_height, pixel_width)

    # Header
    border = "─" * args.width
    print(f"╔{border}╗")
    print(f"║{'RORSCHACH INKBLOT':^{args.width}}║")
    print(f"╠{border}╣")

    if args.animate:
        # Animated reveal
        ESC = "\033["
        total_braille_rows = len(lines)

        # Print empty space for animation
        for _ in range(total_braille_rows):
            print(f"║{'':^{args.width}}║")

        # Move cursor up and animate
        print(f"{ESC}{total_braille_rows}A", end="", flush=True)

        for reveal in range(1, total_braille_rows + 1):
            # Move to top of blot area
            print(f"{ESC}[{total_braille_rows + 3}H", end="")  # after header
            for i, line in enumerate(lines):
                if i < reveal:
                    print(f"║{line:^{args.width}}║")
                else:
                    print(f"║{'':^{args.width}}║")
            sys.stdout.flush()
            time.sleep(0.06)

        time.sleep(0.3)
    else:
        for line in lines:
            print(f"║{line:^{args.width}}║")

    print(f"╠{border}╣")

    # Footer with metadata and interpretation
    info_line = f"seed={seed}  style={style}  size={pixel_width}×{pixel_height}px"
    print(f"║{info_line:^{args.width}}║")
    print(f"╚{border}╝")

    if not args.no_interpret:
        print()
        interpretation = generate_interpretation(seed, rng)
        wrap_width = min(args.width, 70)
        print("┌─ Rorschach Interpretation " + "─" * (wrap_width - 28) + "┐")
        for line in interpretation.split("\n"):
            print(f"│{line:^{wrap_width}}│")
        print("└" + "─" * wrap_width + "┘")
        print()

    # Print rerun hint
    print(f"  💡 Rerun with: python inkblot.py --seed {seed} --style {style}")


if __name__ == "__main__":
    main()