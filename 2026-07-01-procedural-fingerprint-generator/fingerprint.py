#!/usr/bin/env python3
"""
Procedural Fingerprint Generator
==================================
Generates unique, realistic ASCII fingerprint patterns with various ridge types
(loops, whorls, arches, tented arches, double loops) and minutiae points.

Uses an orientation field model combined with cosine wave rendering to produce
dense, realistic ridge patterns.
"""

import argparse
import hashlib
import math
import random
import sys
from enum import Enum
from typing import List, Tuple


class PatternType(Enum):
    LOOP = "loop"
    WHORL = "whorl"
    ARCH = "arch"
    TENTED_ARCH = "tented_arch"
    DOUBLE_LOOP = "double_loop"


class MinutiaType(Enum):
    ENDING = "ending"
    BIFURCATION = "bifurcation"
    ISLAND = "island"


def orientation_at(x: float, y: float, w: int, h: int,
                   pattern: PatternType, core_x: float, core_y: float) -> float:
    """Calculate ridge orientation angle (in radians) at position (x, y).
    This models the directional field of a real fingerprint pattern."""
    dx = x - core_x
    dy = y - core_y
    dist = math.sqrt(dx * dx + dy * dy) + 0.001
    theta = math.atan2(dy, dx)

    if pattern == PatternType.LOOP:
        # Ridges curve around the core; orientation varies with position
        # Near the core, ridges loop sharply; far away they're more horizontal
        loop_strength = max(0, 1.0 - dist / (w * 0.5))
        return math.pi / 2 + loop_strength * math.sin(2 * theta) * math.pi / 2

    elif pattern == PatternType.WHORL:
        # Whorl: orientation rotates around core like a pinwheel
        return theta + math.pi / 2

    elif pattern == PatternType.ARCH:
        # Arch: ridges flow left to right with upward bump in the middle
        x_norm = (x - core_x) / (w * 0.5)
        y_norm = y / h
        bump = math.exp(-x_norm * x_norm * 2) * (1.0 - y_norm)
        return -math.pi / 2 + bump * math.pi * 0.5

    elif pattern == PatternType.TENTED_ARCH:
        # Tented arch: sharper upward spike
        x_norm = (x - core_x) / (w * 0.3)
        y_norm = y / h
        spike = math.exp(-x_norm * x_norm * 3) * (1.0 - y_norm)
        return -math.pi / 2 + spike * math.pi * 0.7

    elif pattern == PatternType.DOUBLE_LOOP:
        # Two cores; orientation blends between them
        cx2 = w - core_x
        cy2 = core_y + 3
        dist1 = math.sqrt((x - core_x) ** 2 + (y - core_y) ** 2) + 0.001
        dist2 = math.sqrt((x - cx2) ** 2 + (y - cy2) ** 2) + 0.001
        theta1 = math.atan2(y - core_y, x - core_x) + math.pi / 2
        theta2 = math.atan2(y - cy2, x - cx2) + math.pi / 2
        w1 = 1.0 / (dist1 * dist1)
        w2 = 1.0 / (dist2 * dist2)
        return math.atan2(
            w1 * math.sin(theta1) + w2 * math.sin(theta2),
            w1 * math.cos(theta1) + w2 * math.cos(theta2)
        )

    return 0.0


def ridge_frequency(x: float, y: float, w: int, h: int,
                    pattern: PatternType, core_x: float, core_y: float) -> float:
    """Return the local ridge spatial frequency (cycles per pixel)."""
    base_freq = 0.35
    dx = x - core_x
    dy = y - core_y
    dist = math.sqrt(dx * dx + dy * dy)

    # Slightly lower frequency near core for realism
    if pattern == PatternType.WHORL:
        return base_freq * (1.0 - 0.15 * math.exp(-dist * dist / (w * 4)))
    return base_freq


def render_fingerprint(w: int, h: int, pattern: PatternType, seed: int,
                       density: float, contrast: float,
                       show_minutiae: bool) -> Tuple[List[str], List[dict]]:
    """Render a fingerprint using orientation-field-driven cosine rendering."""
    rng = random.Random(seed)

    # Slight random perturbation of core position for variety
    core_x = w * 0.5 + rng.uniform(-w * 0.03, w * 0.03)
    core_y = h * 0.42 + rng.uniform(-h * 0.03, h * 0.03)

    # We use a phase-integration approach:
    # At each point, the local phase = integral of (frequency * orientation) from a reference
    # Simplified: accumulate phase along x and y based on orientation

    # First compute the phase field using gradient integration
    phase = [[0.0] * w for _ in range(h)]

    # Build phase by integrating the orientation field
    # Phase gradient at (x,y) has magnitude = ridge_frequency
    # and direction = orientation_at(x,y)
    for row in range(h):
        for col in range(w):
            x = col + 0.5
            y = row + 0.5
            angle = orientation_at(x, y, w, h, pattern, core_x, core_y)
            freq = ridge_frequency(x, y, w, h, pattern, core_x, core_y) * density

            # Phase gradient components
            dphase_dx = freq * math.cos(angle)
            dphase_dy = freq * math.sin(angle)

            if col == 0 and row == 0:
                phase[row][col] = 0.0
            elif col == 0:
                phase[row][col] = phase[row - 1][col] + dphase_dy
            elif row == 0:
                phase[row][col] = phase[row][col - 1] + dphase_dx
            else:
                # Average integration from left and above
                from_left = phase[row][col - 1] + dphase_dx
                from_above = phase[row - 1][col] + dphase_dy
                phase[row][col] = (from_left + from_above) / 2.0

    # Now render: ridge = cos(phase) where dark = ridge, light = valley
    ramp = " .:-=+*#%@"
    grid = [[0.0] * w for _ in range(h)]

    for row in range(h):
        for col in range(w):
            val = math.cos(phase[row][col])
            # Map: -1 = valley (space), +1 = ridge (dark)
            intensity = (val + 1.0) / 2.0  # 0 to 1
            intensity = intensity * contrast
            intensity = max(0.0, min(1.0, intensity))
            grid[row][col] = intensity

    # Add some noise for realism
    noise_level = 0.08
    for row in range(h):
        for col in range(w):
            noise = rng.gauss(0, noise_level)
            grid[row][col] = max(0.0, min(1.0, grid[row][col] + noise))

    # Convert to ASCII
    lines = []
    for row in range(h):
        line = ""
        for col in range(w):
            idx = int(grid[row][col] * (len(ramp) - 1))
            idx = max(0, min(len(ramp) - 1, idx))
            line += ramp[idx]
        lines.append(line)

    # Apply elliptical mask
    lines = apply_oval_mask(lines, w, h)

    # Generate and optionally mark minutiae
    minutiae = generate_minutiae(w, h, rng)
    if show_minutiae:
        lines = mark_minutiae(lines, minutiae, w, h)

    return lines, minutiae


def apply_oval_mask(lines: List[str], w: int, h: int) -> List[str]:
    """Apply an elliptical mask for a realistic finger-pad shape."""
    cx, cy = w / 2.0, h / 2.0
    rx, ry = w / 2.0 - 1.5, h / 2.0 - 1.5

    result = []
    for row_idx, line in enumerate(lines):
        new_chars = []
        for col_idx, ch in enumerate(line):
            dx = (col_idx - cx) / rx
            dy = (row_idx - cy) / ry
            dist_sq = dx * dx + dy * dy

            if dist_sq > 1.0:
                new_chars.append(" ")
            elif dist_sq > 0.82:
                # Smooth fade at edges
                fade = (1.0 - dist_sq) / 0.18
                ramp = " .:-=+*#%@"
                if ch == " ":
                    new_chars.append(" ")
                else:
                    ci = ramp.index(ch)
                    new_ci = max(0, ci - int((1 - fade) * 4))
                    new_chars.append(ramp[new_ci])
            else:
                new_chars.append(ch)
        result.append("".join(new_chars))

    return result


def generate_minutiae(w: int, h: int, rng: random.Random) -> List[dict]:
    """Generate random minutiae points within the fingerprint area."""
    minutiae = []
    num = rng.randint(10, 20)
    for _ in range(num):
        # Place within the elliptical area
        while True:
            mx = rng.uniform(w * 0.15, w * 0.85)
            my = rng.uniform(h * 0.15, h * 0.85)
            # Check inside ellipse
            dx = (mx - w / 2.0) / (w / 2.0 - 2)
            dy = (my - h / 2.0) / (h / 2.0 - 2)
            if dx * dx + dy * dy < 0.7:
                break
        mt = rng.choice(["ending", "bifurcation", "island"])
        ma = rng.uniform(0, 2 * math.pi)
        minutiae.append({"x": mx, "y": my, "angle": ma, "type": mt})
    return minutiae


def mark_minutiae(lines: List[str], minutiae: List[dict], w: int, h: int) -> List[str]:
    """Mark minutiae points with special symbols."""
    result = [list(line) for line in lines]
    symbols = {"ending": "◆", "bifurcation": "◇", "island": "○"}

    for m in minutiae:
        ix, iy = int(round(m["x"])), int(round(m["y"]))
        if 0 <= ix < w and 0 <= iy < h:
            result[iy][ix] = symbols.get(m["type"], "•")

    return ["".join(row) for row in result]


def print_fingerprint(lines: List[str], w: int, h: int, pattern: PatternType,
                       seed: int, minutiae: List[dict], show_minutiae: bool):
    """Pretty-print the fingerprint with a border and info."""
    pattern_names = {
        PatternType.LOOP: "Ulnar Loop",
        PatternType.WHORL: "Plain Whorl",
        PatternType.ARCH: "Plain Arch",
        PatternType.TENTED_ARCH: "Tented Arch",
        PatternType.DOUBLE_LOOP: "Double Loop Whorl",
    }
    name = pattern_names.get(pattern, pattern.value)
    total_w = w + 2

    # Title bar
    title = f" Fingerprint: {name} (seed: {seed}) "
    pad_l = max(0, (total_w - len(title)) // 2)
    pad_r = max(0, total_w - len(title) - pad_l)
    print("┌" + "─" * pad_l + title + "─" * pad_r + "┐")

    for line in lines:
        print(f"│ {line} │")

    # Bottom info
    info = f" Minutiae: {len(minutiae)} points "
    print("│" + info + " " * (total_w - len(info)) + "│")

    if show_minutiae:
        legend = " ◆=Ending ◇=Bifurcation ○=Island "
        print("│" + legend + " " * (total_w - len(legend)) + "│")

    print("└" + "─" * total_w + "┘")


def generate_fingerprint_id(pattern: PatternType, seed: int, minutiae: List[dict]) -> str:
    """Generate a unique hash ID for this fingerprint."""
    data = f"{seed}:{pattern.value}:"
    for m in sorted(minutiae, key=lambda m: (m["x"], m["y"])):
        data += f"({m['x']:.1f},{m['y']:.1f},{m['type']})"
    return hashlib.sha256(data.encode()).hexdigest()[:16].upper()


def list_patterns():
    """Print available pattern types."""
    patterns = [
        ("loop", "Ulnar Loop — ridges enter from one side and curve back"),
        ("whorl", "Plain Whorl — concentric circular/spiral ridges"),
        ("arch", "Plain Arch — ridges flow across with a gentle rise"),
        ("tented_arch", "Tented Arch — like arch but with a sharp peak"),
        ("double_loop", "Double Loop Whorl — two loop cores spiraling together"),
    ]
    print("Available fingerprint patterns:\n")
    for name, desc in patterns:
        print(f"  {name:15s}  {desc}")
    print()


def generate_comparison(w: int, h: int, seed: int, density: float,
                         contrast: float, show_minutiae: bool):
    """Show all pattern types side by side for comparison."""
    patterns = [PatternType.LOOP, PatternType.WHORL, PatternType.ARCH,
                PatternType.TENTED_ARCH, PatternType.DOUBLE_LOOP]
    short_names = ["Loop", "Whorl", "Arch", "Tented", "DblLoop"]

    cw, ch = min(w, 28), min(h, 35)

    all_lines = []
    for pat in patterns:
        lines, _ = render_fingerprint(cw, ch, pat, seed, density, contrast, show_minutiae)
        all_lines.append(lines)

    # Headers
    headers = [f"{name:^{cw}}" for name in short_names]
    print("  ".join(headers))
    print("  ".join(["─" * cw] * 5))

    for row in range(ch):
        row_strs = []
        for fp in all_lines:
            row_strs.append(fp[row] if row < len(fp) else " " * cw)
        print("  ".join(row_strs))

    print("  ".join(["─" * cw] * 5))
    print(f"\nAll patterns generated with seed: {seed}")


def main():
    parser = argparse.ArgumentParser(
        description="Procedural Fingerprint Generator — Generate unique ASCII fingerprint patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Generate a random loop fingerprint
  %(prog)s --pattern whorl          Generate a whorl pattern
  %(prog)s --seed 12345             Generate with specific seed
  %(prog)s --compare                Show all pattern types side by side
  %(prog)s --list                   List available patterns
  %(prog)s --minutiae               Show minutiae points
  %(prog)s --width 60 --height 80   Custom size
        """
    )

    parser.add_argument("--pattern", "-p", type=str, default="loop",
                        choices=["loop", "whorl", "arch", "tented_arch", "double_loop"],
                        help="Fingerprint pattern type (default: loop)")
    parser.add_argument("--seed", "-s", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--width", "-W", type=int, default=50,
                        help="Width of fingerprint (default: 50)")
    parser.add_argument("--height", "-H", type=int, default=55,
                        help="Height of fingerprint (default: 55)")
    parser.add_argument("--density", "-d", type=float, default=1.0,
                        help="Ridge density factor (default: 1.0)")
    parser.add_argument("--contrast", "-c", type=float, default=1.2,
                        help="Contrast multiplier (default: 1.2)")
    parser.add_argument("--minutiae", "-m", action="store_true",
                        help="Show minutiae points on the fingerprint")
    parser.add_argument("--compare", action="store_true",
                        help="Show all pattern types side by side")
    parser.add_argument("--list", action="store_true",
                        help="List available pattern types")
    parser.add_argument("--id-only", action="store_true",
                        help="Only output the fingerprint ID hash")

    args = parser.parse_args()

    if args.list:
        list_patterns()
        return

    pattern_map = {
        "loop": PatternType.LOOP,
        "whorl": PatternType.WHORL,
        "arch": PatternType.ARCH,
        "tented_arch": PatternType.TENTED_ARCH,
        "double_loop": PatternType.DOUBLE_LOOP,
    }

    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    pattern = pattern_map[args.pattern]

    if args.compare:
        generate_comparison(args.width, args.height, seed, args.density,
                           args.contrast, args.minutiae)
        return

    lines, minutiae = render_fingerprint(
        args.width, args.height, pattern, seed, args.density,
        args.contrast, args.minutiae
    )

    fp_id = generate_fingerprint_id(pattern, seed, minutiae)

    if args.id_only:
        print(fp_id)
        return

    print()
    print_fingerprint(lines, args.width, args.height, pattern, seed,
                      minutiae, args.minutiae)
    print(f"  Fingerprint ID: {fp_id}")
    print(f"  Pattern: {pattern.value} | Seed: {seed} | Minutiae: {len(minutiae)}")
    print()


if __name__ == "__main__":
    main()