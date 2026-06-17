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
    python inkblot.py --invert          # Invert the inkblot
    python inkblot.py --color          # Add ANSI color to the blot
    python inkblot.py --gallery        # Show a 2x2 gallery of styles
    python inkblot.py --save blot.txt  # Save output to a file
    python inkblot.py --density 0.4    # Control blot density (0.1–0.9)
"""

import argparse
import math
import random
import sys
import time
import os

# ─── Version ──────────────────────────────────────────────────────────
VERSION = "2.0.0"

# ─── Braille constants ───────────────────────────────────────────────
# Braille characters encode a 2×4 grid of dots into a single Unicode char.
# Columns: col0 = bits 0,3; col1 = bits 1,4; row offsets in each column.
BRAILLE_MAP = {
    (r, c): (1 << (r + c * 4))  # dot (row r, col c) → bit index
    for c in range(2) for r in range(4)
}
BRAILLE_BASE = 0x2800

# ─── ANSI color codes ─────────────────────────────────────────────────
ANSI_COLORS = {
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "blue": "\033[34m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "white": "\033[37m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_blue": "\033[94m",
}
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"


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


def pixels_to_braille_colored(grid, height, width, color_code):
    """Convert a 2D boolean grid into colored Braille art strings.

    Args:
        grid: 2D boolean grid (row-major)
        height: grid height in pixels
        width: grid width in pixels
        color_code: ANSI escape sequence for the ink color

    Returns:
        List of colored Braille strings.
    """
    raw_lines = pixels_to_braille(grid, height, width)
    return [f"{color_code}{line}{ANSI_RESET}" for line in raw_lines]


# ─── Value noise ──────────────────────────────────────────────────────
def _lerp(a, b, t):
    """Linear interpolation between a and b by factor t."""
    return a + (b - a) * t


def _smooth(t):
    """Smoothstep interpolation for noise."""
    return t * t * (3 - 2 * t)


def _hash2d(x, y, seed):
    """Cheap 2D hash returning a float in [0, 1).

    Uses integer arithmetic to create a deterministic pseudo-random
    value from coordinates and a seed.
    """
    n = (x * 374761393 + y * 668265263 + seed * 1013904223) & 0xFFFFFFFF
    n = ((n >> 13) ^ n) & 0xFFFFFFFF
    n = (n * (n * n * 15731 + 789221) + 1376312589) & 0xFFFFFFFF
    return (n & 0xFFFF) / 0xFFFF


def value_noise(x, y, seed):
    """2D value noise with smooth interpolation.

    Args:
        x, y: Floating-point coordinates
        seed: Integer seed for deterministic output

    Returns:
        Float in [0, 1] range.
    """
    ix, iy = int(math.floor(x)), int(math.floor(y))
    fx, fy = _smooth(x - ix), _smooth(y - iy)
    n00 = _hash2d(ix, iy, seed)
    n10 = _hash2d(ix + 1, iy, seed)
    n01 = _hash2d(ix, iy + 1, seed)
    n11 = _hash2d(ix + 1, iy + 1, seed)
    return _lerp(_lerp(n00, n10, fx), _lerp(n01, n11, fx), fy)


def fbm(x, y, seed, octaves=4, lacunarity=2.0, gain=0.5):
    """Fractal Brownian Motion – layered value noise.

    Combines multiple octaves of value noise at increasing frequencies
    and decreasing amplitudes to create rich, detailed noise patterns.

    Args:
        x, y: Coordinates
        seed: Random seed
        octaves: Number of noise layers (default: 4)
        lacunarity: Frequency multiplier per octave (default: 2.0)
        gain: Amplitude multiplier per octave (default: 0.5)

    Returns:
        Float value combining all noise octaves.
    """
    value, amplitude, frequency = 0.0, 1.0, 1.0
    for i in range(octaves):
        value += amplitude * value_noise(x * frequency, y * frequency, seed + i * 31)
        amplitude *= gain
        frequency *= lacunarity
    return value


# ─── Inkblot generators ──────────────────────────────────────────────

def _mirror_horizontal(grid, height, width):
    """Mirror left half to right half for bilateral symmetry."""
    for y in range(height):
        for x in range(width // 2, width):
            grid[y][x] = grid[y][width - 1 - x]


def _mirror_vertical(grid, height, width):
    """Mirror top half to bottom half."""
    for y in range(height // 2, height):
        for x in range(width):
            grid[y][x] = grid[height - 1 - y][x]


def generate_splash(height, width, seed, rng, density=0.35):
    """Classic Rorschach: symmetric blobs using noise with threshold.

    Creates organic, blob-like patterns with radial falloff from center,
    giving the classic inkblot appearance.

    Args:
        density: Threshold offset (0.0 = sparse, 1.0 = dense). Default 0.35.
    """
    grid = [[False] * width for _ in range(height)]
    cx, cy = width / 2, height / 2

    for y in range(height):
        for x in range(width // 2 + 1):  # only generate left half
            # Distance from center influences probability
            dx = (x - cx) / (width / 2)
            dy = (y - cy) / (height / 2)
            dist = math.sqrt(dx * dx + dy * dy)

            # Multi-scale noise for organic texture
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

            # density parameter shifts the threshold
            threshold = rng.uniform(0.25, 0.45) - (density - 0.35) * 0.5
            grid[y][x] = combined > threshold

    _mirror_horizontal(grid, height, width)
    return grid


def generate_radial(height, width, seed, rng, density=0.4):
    """Radial spokes pattern – like a butterfly or dendrite.

    Creates patterns with spoke-like arms radiating from the center,
    distorted by noise for an organic feel.

    Args:
        density: Threshold offset (0.0 = sparse, 1.0 = dense). Default 0.4.
    """
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

            threshold = rng.uniform(0.3, 0.5) - (density - 0.4) * 0.5
            grid[y][x] = combined > threshold

    _mirror_horizontal(grid, height, width)
    return grid


def generate_cellular(height, width, seed, rng, density=0.4):
    """Cell / voronoi-like pattern – organic cellular structures.

    Creates voronoi-cell patterns with visible boundaries between cells,
    filled sparsely with noise-driven interior detail.

    Args:
        density: Threshold offset (0.0 = sparse, 1.0 = dense). Default 0.4.
    """
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

            threshold = rng.uniform(0.35, 0.5) - (density - 0.4) * 0.5
            grid[y][x] = combined > threshold

    _mirror_horizontal(grid, height, width)
    return grid


def generate_organic(height, width, seed, rng, density=0.33):
    """Worm-like tendrils emanating from center.

    Creates tendril-like forms that radiate outward from the center,
    warped by noise for a living, organic feel.

    Args:
        density: Threshold offset (0.0 = sparse, 1.0 = dense). Default 0.33.
    """
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

            threshold = rng.uniform(0.25, 0.4) - (density - 0.33) * 0.5
            grid[y][x] = combined > threshold

    _mirror_horizontal(grid, height, width)
    return grid


def generate_both_mirror(height, width, seed, rng, density=0.33):
    """Mirror on both axes – creates a 4-fold symmetric pattern.

    Generates only the top-left quadrant and tiles it across all
    four quadrants with mirroring for kaleidoscope-like symmetry.

    Args:
        density: Threshold offset (0.0 = sparse, 1.0 = dense). Default 0.33.
    """
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
            threshold = rng.uniform(0.25, 0.42) - (density - 0.33) * 0.5
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


def generate_fractal(height, width, seed, rng, density=0.35):
    """Fractal dendrite pattern – branching structures like neurons or rivers.

    Uses recursive subdivision and perturbation to create branching
    dendritic patterns with organic, tree-like structures.

    Args:
        density: Threshold offset (0.0 = sparse, 1.0 = dense). Default 0.35.
    """
    grid = [[False] * width for _ in range(height)]
    cx, cy = width / 2, height / 2

    # Create multiple branching structures
    num_branches = rng.randint(3, 7)

    for y in range(height):
        for x in range(width // 2 + 1):
            dx = (x - cx)
            dy = (y - cy)
            dist = math.sqrt(dx * dx + dy * dy)
            angle = math.atan2(dy, dx)
            norm_dist = dist / (min(width, height) * 0.45)

            # Base: thin branches along spoke angles
            branch_val = 0.0
            for b in range(num_branches):
                base_angle = b * math.pi * 2 / num_branches
                # Perturb angle with noise for organic feel
                angle_offset = fbm(b * 1.7, 0, seed) * 1.5
                branch_angle = base_angle + angle_offset

                # How close is this pixel to the branch direction?
                angle_diff = abs(((angle - branch_angle + math.pi) % (2 * math.pi)) - math.pi)

                # Branch width increases with distance, modified by noise
                branch_width = 0.15 + fbm(b * 0.3, norm_dist * 2, seed + 500) * 0.15
                # Branches thin out at the very tips
                branch_width *= max(0.2, 1.0 - norm_dist * 0.3)

                if angle_diff < branch_width:
                    branch_val = max(branch_val, 1.0 - angle_diff / max(branch_width, 0.01))

            # Add sub-branching with higher-frequency noise
            sub_noise = fbm(x * 0.12, y * 0.12, seed + 777) * 0.3

            # Combine
            combined = branch_val * 0.6 + sub_noise * 0.4

            # Radial envelope – branches fade at the edges
            envelope = max(0, 1.0 - norm_dist ** 1.2)
            combined *= envelope

            # Small detail noise to break up hard edges
            detail = fbm(x * 0.2, y * 0.2, seed + 999)
            if combined > 0.1:
                combined += detail * 0.15

            threshold = rng.uniform(0.25, 0.45) - (density - 0.35) * 0.5
            grid[y][x] = combined > threshold

    _mirror_horizontal(grid, height, width)
    return grid


STYLES = {
    "splash": generate_splash,
    "radial": generate_radial,
    "cellular": generate_cellular,
    "organic": generate_organic,
    "mirror4": generate_both_mirror,
    "fractal": generate_fractal,
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
        "a yearning for adventure beyond familiar boundaries",
        "the quiet struggle between vulnerability and strength",
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
        "a storm forming between two mountains",
        "a dragon unfurling its wings at dawn",
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
        "Branches grow toward light. Follow what nourishes you.",
        "The pattern repeats at every scale. Zoom out before you zoom in.",
    ],
}


def generate_interpretation(seed, rng):
    """Generate a whimsical Rorschach-style interpretation.

    Randomly selects an object, emotion, and piece of advice from
    curated lists to create a personalized psychological reading.

    Args:
        seed: Random seed (unused directly, but influences rng).
        rng: Random.Random instance for deterministic selection.

    Returns:
        Multi-line string with the interpretation.
    """
    emotion = rng.choice(INTERPRETATIONS["emotions"])
    obj = rng.choice(INTERPRETATIONS["objects"])
    advice = rng.choice(INTERPRETATIONS["advice"])

    return (
        f"  You see {obj}.\n"
        f"  This suggests {emotion}.\n"
        f"  {advice}"
    )


# ─── Statistics ───────────────────────────────────────────────────────

def compute_stats(grid, height, width):
    """Compute statistics about the inkblot.

    Returns a dict with fill_ratio, pixel_count, total_pixels, and symmetry_score.
    """
    total = height * width
    filled = sum(sum(row) for row in grid)
    fill_ratio = filled / total if total > 0 else 0

    # Check how symmetric the blot actually is (left vs right)
    left_count = sum(
        grid[y][x]
        for y in range(height)
        for x in range(width // 2)
    )
    right_count = sum(
        grid[y][x]
        for x in range(width // 2, width)
        for y in range(height)
    )
    # Symmetry score: 1.0 = perfectly symmetric, 0.0 = completely asymmetric
    if left_count + right_count == 0:
        symmetry = 1.0
    else:
        symmetry = 1.0 - abs(left_count - right_count) / (left_count + right_count)

    return {
        "fill_ratio": fill_ratio,
        "pixel_count": filled,
        "total_pixels": total,
        "symmetry_score": symmetry,
    }


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


# ─── Gallery mode ────────────────────────────────────────────────────

def render_gallery(styles_to_show, seed, width, density):
    """Render a 2×2 gallery of different inkblot styles.

    Args:
        styles_to_show: List of 4 style names to display.
        seed: Base seed (each style gets seed + offset).
        width: Width in Braille chars for each sub-blot.
        density: Density parameter for blot generation.

    Returns:
        Multi-line string containing the gallery.
    """
    # Each sub-blot is smaller
    sub_width = width * 2  # pixel width
    sub_height = (sub_width // 4) * 4  # pixel height, divisible by 4

    panels = []
    for i, style_name in enumerate(styles_to_show):
        style_seed = seed + i * 10000
        rng = random.Random(style_seed)
        generator = STYLES[style_name]
        grid = generator(sub_height, sub_width, style_seed, rng, density=density)
        lines = pixels_to_braille(grid, sub_height, sub_width)
        panels.append({
            "lines": lines,
            "style": style_name,
            "seed": style_seed,
            "stats": compute_stats(grid, sub_height, sub_width),
        })

    # Compose gallery
    sub_braille_width = len(panels[0]["lines"][0]) if panels[0]["lines"] else sub_width // 2
    max_lines = max(len(p["lines"]) for p in panels)

    output_lines = []
    sep = "─" * (sub_braille_width + 2)
    header_width = sub_braille_width * 2 + 7

    output_lines.append(f"╔{'═' * header_width}╗")
    output_lines.append(f"║{'INKBLOT GALLERY':^{header_width}}║")
    output_lines.append(f"╠{'═' * header_width}╣")

    # Top row: panels 0 and 1
    for row in range(max_lines):
        left = panels[0]["lines"][row].center(sub_braille_width) if row < len(panels[0]["lines"]) else " " * sub_braille_width
        right = panels[1]["lines"][row].center(sub_braille_width) if row < len(panels[1]["lines"]) else " " * sub_braille_width
        output_lines.append(f"  {left} │ {right}  ")

    # Divider
    output_lines.append(f"  {'─' * sub_braille_width} ┼ {'─' * sub_braille_width}  ")

    # Bottom row: panels 2 and 3
    for row in range(max_lines):
        left = panels[2]["lines"][row].center(sub_braille_width) if row < len(panels[2]["lines"]) else " " * sub_braille_width
        right = panels[3]["lines"][row].center(sub_braille_width) if row < len(panels[3]["lines"]) else " " * sub_braille_width
        output_lines.append(f"  {left} │ {right}  ")

    # Labels
    labels = []
    for i, p in enumerate(panels):
        labels.append(f"  [{i+1}] {p['style']:>10s} (seed={p['seed']}, fill={p['stats']['fill_ratio']:.0%})  ")
    mid = sub_braille_width + 1
    output_lines.append(labels[0].ljust(mid) + "│" + labels[1])
    output_lines.append(labels[2].ljust(mid) + "│" + labels[3])
    output_lines.append(f"╚{'═' * header_width}╝")

    return "\n".join(output_lines)


# ─── Inversion ────────────────────────────────────────────────────────

def invert_grid(grid, height, width):
    """Invert all pixels in the grid (True→False, False→True)."""
    return [[not grid[y][x] for x in range(width)] for y in range(height)]


# ─── Output capture helper ────────────────────────────────────────────

def render_inkblot(grid, pixel_height, pixel_width, args_width, color_code=None, invert=False):
    """Render a grid to Braille art lines, optionally with color and inversion.

    Args:
        grid: 2D boolean grid.
        pixel_height: Height in pixels.
        pixel_width: Width in pixels.
        args_width: Terminal width in Braille chars for centering.
        color_code: Optional ANSI color escape sequence.
        invert: Whether to invert the grid.

    Returns:
        List of rendered line strings.
    """
    if invert:
        grid = invert_grid(grid, pixel_height, pixel_width)

    if color_code:
        lines = pixels_to_braille_colored(grid, pixel_height, pixel_width, color_code)
    else:
        lines = pixels_to_braille(grid, pixel_height, pixel_width)

    # Center each line within the box width
    centered = [f"{line:^{args_width}}" for line in lines]
    return centered


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Rorschach Inkblot Generator – Braille Art Edition",
        epilog="Example: python inkblot.py --seed 42 --style organic --color --density 0.5"
    )
    parser.add_argument("--version", action="version", version=f"inkblot {VERSION}")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--width", type=int, default=80, help="Output width in Braille chars (default: 80)")
    parser.add_argument("--height", type=int, default=None, help="Output height in pixel rows (default: auto)")
    parser.add_argument("--style", choices=list(STYLES.keys()), default=None,
                        help="Inkblot style: splash, radial, cellular, organic, mirror4, fractal")
    parser.add_argument("--no-interpret", action="store_true", help="Skip psychological interpretation")
    parser.add_argument("--animate", action="store_true", help="Animate the blot forming")
    parser.add_argument("--list-styles", action="store_true", help="List available styles and exit")
    parser.add_argument("--invert", action="store_true", help="Invert the inkblot (swap ink and paper)")
    parser.add_argument("--color", type=str, default=None,
                        choices=list(ANSI_COLORS.keys()),
                        help="Color the inkblot with an ANSI color")
    parser.add_argument("--density", type=float, default=None,
                        help="Blot density from 0.1 (sparse) to 0.9 (dense). Default varies by style.")
    parser.add_argument("--gallery", action="store_true",
                        help="Show a 2×2 gallery of 4 different styles")
    parser.add_argument("--stats", action="store_true",
                        help="Show blot statistics (fill ratio, pixel count, symmetry)")
    parser.add_argument("--save", type=str, default=None, metavar="FILE",
                        help="Save output to a text file")
    args = parser.parse_args()

    # Validate width
    if args.width < 10 or args.width > 300:
        print("Error: --width must be between 10 and 300.", file=sys.stderr)
        sys.exit(1)

    if args.density is not None and (args.density < 0.1 or args.density > 0.9):
        print("Error: --density must be between 0.1 and 0.9.", file=sys.stderr)
        sys.exit(1)

    if args.list_styles:
        print("Available inkblot styles:")
        for name, func in STYLES.items():
            doc = (func.__doc__ or '').strip().split('\n')[0]
            print(f"  {name:12s} – {doc}")
        return

    # Set up RNG
    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    rng = random.Random(seed)
    style = args.style or rng.choice(list(STYLES.keys()))

    # Resolve density
    density = args.density if args.density is not None else None
    if density is None:
        # Use each generator's default density
        density_map = {
            "splash": 0.35, "radial": 0.4, "cellular": 0.4,
            "organic": 0.33, "mirror4": 0.33, "fractal": 0.35,
        }
        density = density_map.get(style, 0.35)

    # Calculate dimensions
    # Braille chars are 2px wide × 4px tall; width is in Braille chars
    pixel_width = args.width * 2
    pixel_height = args.height or (pixel_width // 2)  # ~2:1 aspect
    # Make pixel_height divisible by 4
    pixel_height = (pixel_height // 4) * 4
    if pixel_height < 4:
        pixel_height = 4

    # Color support
    color_code = ANSI_COLORS.get(args.color, None) if args.color else None

    # ─── Gallery mode ──────────────────────────────────────────────
    if args.gallery:
        # Pick 4 different styles (or as many as we have)
        available = list(STYLES.keys())
        rng.shuffle(available)
        chosen = available[:4]
        # Pad if fewer than 4 styles
        while len(chosen) < 4:
            chosen.append(rng.choice(available))

        gallery_width = max(20, args.width // 2 - 2)  # each panel half width
        result = render_gallery(chosen, seed, gallery_width, density)
        print(result)

        if not args.no_interpret:
            print()
            interpretation = generate_interpretation(seed, rng)
            wrap_width = min(args.width, 70)
            print("┌─ Rorschach Interpretation " + "─" * max(0, wrap_width - 28) + "┐")
            for line in interpretation.split("\n"):
                print(f"│{line:^{wrap_width}}│")
            print("└" + "─" * wrap_width + "┘")

        print(f"\n  💡 Gallery seed: {seed}  |  Rerun: python inkblot.py --seed {seed} --gallery")

        # Save gallery if requested
        if args.save:
            with open(args.save, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"  💾 Gallery saved to: {args.save}")
        return

    # ─── Single blot mode ──────────────────────────────────────────
    generator = STYLES[style]
    grid = generator(pixel_height, pixel_width, seed, rng, density=density)

    # Render blot
    rendered_lines = render_inkblot(grid, pixel_height, pixel_width, args.width, color_code, args.invert)

    # Build output
    output_lines = []
    border = "─" * args.width
    output_lines.append(f"╔{border}╗")
    output_lines.append(f"║{'RORSCHACH INKBLOT':^{args.width}}║")
    output_lines.append(f"╠{border}╣")

    if args.animate:
        # Animated reveal
        ESC = "\033["
        total_braille_rows = len(rendered_lines)

        # Print empty space for animation
        for _ in range(total_braille_rows):
            print(f"║{'':^{args.width}}║")

        # Move cursor up and animate
        print(f"{ESC}{total_braille_rows}A", end="", flush=True)

        for reveal in range(1, total_braille_rows + 1):
            # Move to top of blot area
            print(f"{ESC}[{total_braille_rows + 3}H", end="")
            for i, line in enumerate(rendered_lines):
                if i < reveal:
                    print(f"║{line}║")
                else:
                    print(f"║{'':^{args.width}}║")
            sys.stdout.flush()
            time.sleep(0.06)

        time.sleep(0.3)
    else:
        for line in rendered_lines:
            output_lines.append(f"║{line}║")

    output_lines.append(f"╠{border}╣")

    # Footer with metadata
    info_parts = [f"seed={seed}", f"style={style}", f"size={pixel_width}×{pixel_height}px"]
    if args.invert:
        info_parts.append("inverted")
    if args.color:
        info_parts.append(f"color={args.color}")
    if args.density is not None or density != {"splash": 0.35, "radial": 0.4, "cellular": 0.4, "organic": 0.33, "mirror4": 0.33, "fractal": 0.35}.get(style, 0.35):
        info_parts.append(f"density={density:.2f}")

    info_line = "  ".join(info_parts)
    output_lines.append(f"║{info_line:^{args.width}}║")

    # Stats line
    if args.stats:
        stats = compute_stats(grid, pixel_height, pixel_width)
        stats_line = f"fill={stats['fill_ratio']:.1%}  pixels={stats['pixel_count']}  symmetry={stats['symmetry_score']:.2f}"
        output_lines.append(f"║{stats_line:^{args.width}}║")

    output_lines.append(f"╚{border}╝")

    # Print output
    full_output = "\n".join(output_lines)
    print(full_output)

    if not args.no_interpret:
        print()
        interpretation = generate_interpretation(seed, rng)
        wrap_width = min(args.width, 70)
        print("┌─ Rorschach Interpretation " + "─" * max(0, wrap_width - 28) + "┐")
        for line in interpretation.split("\n"):
            print(f"│{line:^{wrap_width}}│")
        print("└" + "─" * wrap_width + "┘")
        print()

    # Print rerun hint
    rerun_parts = [f"--seed {seed}", f"--style {style}"]
    if args.invert:
        rerun_parts.append("--invert")
    if args.color:
        rerun_parts.append(f"--color {args.color}")
    if args.density is not None:
        rerun_parts.append(f"--density {density}")
    if args.stats:
        rerun_parts.append("--stats")
    print(f"  💡 Rerun with: python inkblot.py {' '.join(rerun_parts)}")

    # Save to file if requested
    if args.save:
        try:
            with open(args.save, "w", encoding="utf-8") as f:
                # Strip ANSI codes for the file
                import re
                clean_output = re.sub(r'\033\[[0-9;]*m', '', full_output)
                f.write(clean_output)
                f.write("\n")
            print(f"  💾 Saved to: {args.save}")
        except OSError as e:
            print(f"  ⚠️  Could not save to {args.save}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()