#!/usr/bin/env python3
"""
Procedural Fingerprint Generator
==================================
Generates unique, realistic ASCII fingerprint patterns with various ridge types
(loops, whorls, arches, tented arches, double loops) and minutiae points.

Uses an orientation field model combined with cosine wave rendering to produce
dense, realistic ridge patterns.

Version: 1.1.0
"""

import argparse
import hashlib
import json
import math
import random
import sys
from enum import Enum
from typing import List, Optional, Tuple

__version__ = "1.1.0"

# ASCII intensity ramp from lightest to darkest
RAMP = " .:-=+*#%@"


class PatternType(Enum):
    """Henry classification system pattern types for fingerprints."""
    LOOP = "loop"
    WHORL = "whorl"
    ARCH = "arch"
    TENTED_ARCH = "tented_arch"
    DOUBLE_LOOP = "double_loop"


class MinutiaType(Enum):
    """Types of minutiae points found in real fingerprints."""
    ENDING = "ending"
    BIFURCATION = "bifurcation"
    ISLAND = "island"


# ANSI color codes for colored output
ANSI_COLORS = {
    "ridge": "\033[38;5;180m",    # warm tan for ridges
    "valley": "\033[38;5;236m",   # dark grey for valleys
    "minutia_ending": "\033[38;5;196m",     # red for endings
    "minutia_bifurcation": "\033[38;5;46m",  # green for bifurcations
    "minutia_island": "\033[38;5;51m",       # cyan for islands
    "border": "\033[38;5;244m",              # grey for border
    "title": "\033[38;5;220m\033[1m",        # bold yellow for title
    "info": "\033[38;5;147m",                # light purple for info
    "reset": "\033[0m",
}

PATTERN_NAMES = {
    PatternType.LOOP: "Ulnar Loop",
    PatternType.WHORL: "Plain Whorl",
    PatternType.ARCH: "Plain Arch",
    PatternType.TENTED_ARCH: "Tented Arch",
    PatternType.DOUBLE_LOOP: "Double Loop Whorl",
}

PATTERN_DESCRIPTIONS = {
    "loop": "Ulnar Loop — ridges enter from one side and curve back",
    "whorl": "Plain Whorl — concentric circular/spiral ridges",
    "arch": "Plain Arch — ridges flow across with a gentle rise",
    "tented_arch": "Tented Arch — like arch but with a sharp peak",
    "double_loop": "Double Loop Whorl — two loop cores spiraling together",
}


def orientation_at(x: float, y: float, w: int, h: int,
                   pattern: PatternType, core_x: float, core_y: float) -> float:
    """Calculate ridge orientation angle (in radians) at position (x, y).

    This models the directional field of a real fingerprint pattern using
    simplified mathematical models of ridge flows from the Henry classification.

    Args:
        x, y: Pixel coordinates in the fingerprint grid.
        w, h: Width and height of the grid.
        pattern: The fingerprint pattern type.
        core_x, core_y: Coordinates of the pattern's core point.

    Returns:
        Orientation angle in radians.
    """
    dx = x - core_x
    dy = y - core_y
    dist = math.sqrt(dx * dx + dy * dy) + 0.001
    theta = math.atan2(dy, dx)

    if pattern == PatternType.LOOP:
        # Ridges curve around the core; orientation varies with position
        # Near the core, ridges loop sharply; far away they're more horizontal
        loop_strength = max(0.0, 1.0 - dist / (w * 0.5))
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
        # Tented arch: sharper upward spike than regular arch
        x_norm = (x - core_x) / (w * 0.3)
        y_norm = y / h
        spike = math.exp(-x_norm * x_norm * 3) * (1.0 - y_norm)
        return -math.pi / 2 + spike * math.pi * 0.7

    elif pattern == PatternType.DOUBLE_LOOP:
        # Two cores; orientation blends between them with inverse-distance weighting
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
    """Return the local ridge spatial frequency (cycles per pixel).

    Frequency varies slightly near the core for whorl patterns to create
    more realistic density variation.

    Args:
        x, y: Pixel coordinates.
        w, h: Grid dimensions.
        pattern: Fingerprint pattern type.
        core_x, core_y: Core point coordinates.

    Returns:
        Frequency value in cycles per pixel.
    """
    base_freq = 0.35
    dx = x - core_x
    dy = y - core_y
    dist = math.sqrt(dx * dx + dy * dy)

    # Slightly lower frequency near core for realism
    if pattern == PatternType.WHORL:
        return base_freq * (1.0 - 0.15 * math.exp(-dist * dist / (w * 4)))
    elif pattern == PatternType.LOOP:
        return base_freq * (1.0 - 0.08 * math.exp(-dist * dist / (w * 3)))
    return base_freq


def render_fingerprint(w: int, h: int, pattern: PatternType, seed: int,
                       density: float, contrast: float,
                       show_minutiae: bool) -> Tuple[List[str], List[dict]]:
    """Render a fingerprint using orientation-field-driven cosine rendering.

    The algorithm:
    1. Compute orientation and frequency fields across the grid
    2. Integrate phase by accumulating gradients (from left and above)
    3. Render ridges via cos(phase), mapping to ASCII intensity
    4. Add Gaussian noise for realism
    5. Apply elliptical mask for finger-pad shape
    6. Optionally mark minutiae points

    Args:
        w, h: Width and height of the output grid.
        pattern: Fingerprint pattern type.
        seed: Random seed for reproducibility.
        density: Ridge density multiplier (0.5–2.0 recommended).
        contrast: Contrast multiplier for the rendering.
        show_minutiae: Whether to overlay minutiae markers.

    Returns:
        Tuple of (list of rendered lines, list of minutiae dicts).
    """
    rng = random.Random(seed)

    # Slight random perturbation of core position for variety
    core_x = w * 0.5 + rng.uniform(-w * 0.03, w * 0.03)
    core_y = h * 0.42 + rng.uniform(-h * 0.03, h * 0.03)

    # Build phase field via gradient integration
    # At each point, the local phase = integral of (frequency * orientation)
    phase = [[0.0] * w for _ in range(h)]

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
                # Average integration from left and above for stability
                from_left = phase[row][col - 1] + dphase_dx
                from_above = phase[row - 1][col] + dphase_dy
                phase[row][col] = (from_left + from_above) / 2.0

    # Render: ridge = cos(phase) where dark = ridge, light = valley
    grid = [[0.0] * w for _ in range(h)]

    for row in range(h):
        for col in range(w):
            val = math.cos(phase[row][col])
            # Map: -1 = valley (space), +1 = ridge (dark)
            intensity = (val + 1.0) / 2.0  # normalize to [0, 1]
            intensity = intensity * contrast
            intensity = max(0.0, min(1.0, intensity))
            grid[row][col] = intensity

    # Add Gaussian noise for realism
    noise_level = 0.08
    for row in range(h):
        for col in range(w):
            noise = rng.gauss(0, noise_level)
            grid[row][col] = max(0.0, min(1.0, grid[row][col] + noise))

    # Convert to ASCII characters
    lines = []
    for row in range(h):
        line = ""
        for col in range(w):
            idx = int(grid[row][col] * (len(RAMP) - 1))
            idx = max(0, min(len(RAMP) - 1, idx))
            line += RAMP[idx]
        lines.append(line)

    # Apply elliptical mask for realistic finger-pad shape
    lines = apply_oval_mask(lines, w, h)

    # Generate and optionally mark minutiae
    minutiae = generate_minutiae(w, h, rng)
    if show_minutiae:
        lines = mark_minutiae(lines, minutiae, w, h)

    return lines, minutiae


def apply_oval_mask(lines: List[str], w: int, h: int) -> List[str]:
    """Apply an elliptical mask for a realistic finger-pad shape.

    Characters outside the ellipse become spaces. Characters near the
    edge get faded for a smooth transition.

    Args:
        lines: Rendered fingerprint lines.
        w, h: Grid dimensions.

    Returns:
        Masked fingerprint lines.
    """
    cx, cy = w / 2.0, h / 2.0
    rx, ry = w / 2.0 - 1.5, h / 2.0 - 1.5

    # Guard against degenerate sizes
    if rx <= 0 or ry <= 0:
        return lines

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
                if ch == " ":
                    new_chars.append(" ")
                else:
                    ci = RAMP.index(ch) if ch in RAMP else 0
                    new_ci = max(0, ci - int((1 - fade) * 4))
                    new_chars.append(RAMP[new_ci])
            else:
                new_chars.append(ch)
        result.append("".join(new_chars))

    return result


def generate_minutiae(w: int, h: int, rng: random.Random) -> List[dict]:
    """Generate random minutiae points within the fingerprint area.

    Minutiae are placed within the inner region of the elliptical fingerprint
    mask to ensure they appear on visible ridges.

    Args:
        w, h: Grid dimensions.
        rng: Seeded Random instance for reproducibility.

    Returns:
        List of minutiae dicts with keys: x, y, angle, type.
    """
    minutiae = []
    num = rng.randint(10, 20)
    for _ in range(num):
        # Place within the elliptical area (inner region)
        attempts = 0
        while attempts < 50:
            mx = rng.uniform(w * 0.15, w * 0.85)
            my = rng.uniform(h * 0.15, h * 0.85)
            # Check inside ellipse
            dx = (mx - w / 2.0) / (w / 2.0 - 2)
            dy = (my - h / 2.0) / (h / 2.0 - 2)
            if dx * dx + dy * dy < 0.7:
                break
            attempts += 1
        else:
            # Fallback: use center region if ellipse check keeps failing
            mx = w / 2.0 + rng.uniform(-w * 0.1, w * 0.1)
            my = h / 2.0 + rng.uniform(-h * 0.1, h * 0.1)

        mt = rng.choice(["ending", "bifurcation", "island"])
        ma = rng.uniform(0, 2 * math.pi)
        minutiae.append({"x": mx, "y": my, "angle": ma, "type": mt})
    return minutiae


def mark_minutiae(lines: List[str], minutiae: List[dict],
                  w: int, h: int) -> List[str]:
    """Mark minutiae points with special Unicode symbols on the fingerprint.

    Symbols used:
        ◆ = Ridge ending
        ◇ = Bifurcation
        ○ = Island (short ridge segment)

    Args:
        lines: Rendered fingerprint lines.
        minutiae: List of minutiae point dicts.
        w, h: Grid dimensions.

    Returns:
        Fingerprint lines with minutiae markers overlaid.
    """
    result = [list(line) for line in lines]
    symbols = {"ending": "◆", "bifurcation": "◇", "island": "○"}

    for m in minutiae:
        ix, iy = int(round(m["x"])), int(round(m["y"]))
        if 0 <= ix < w and 0 <= iy < h:
            result[iy][ix] = symbols.get(m["type"], "•")

    return ["".join(row) for row in result]


def format_fingerprint(lines: List[str], w: int, h: int, pattern: PatternType,
                       seed: int, minutiae: List[dict], show_minutiae: bool,
                       use_color: bool = False) -> str:
    """Format the fingerprint output as a string with border and metadata.

    Args:
        lines: Rendered fingerprint lines.
        w, h: Grid dimensions.
        pattern: Fingerprint pattern type.
        seed: Random seed used.
        minutiae: List of minutiae dicts.
        show_minutiae: Whether minutiae legend should be shown.
        use_color: Whether to apply ANSI color codes.

    Returns:
        Formatted string ready for printing.
    """
    name = PATTERN_NAMES.get(pattern, pattern.value)
    total_w = w + 2
    output = []

    if use_color:
        c = ANSI_COLORS
    else:
        # No-op color dict
        c = {k: "" for k in ANSI_COLORS}
        c["reset"] = ""

    # Title bar
    title = f" Fingerprint: {name} (seed: {seed}) "
    pad_l = max(0, (total_w - len(title)) // 2)
    pad_r = max(0, total_w - len(title) - pad_l)
    output.append(f"{c['border']}┌" + "─" * pad_l + f"{c['title']}{title}{c['reset']}" + f"{c['border']}─" * pad_r + "┐" + c["reset"])

    for line in lines:
        if use_color:
            # Color each character based on its ramp position
            colored_line = ""
            for ch in line:
                if ch in RAMP:
                    idx = RAMP.index(ch)
                    if idx <= 2:
                        colored_line += f"{c['valley']}{ch}"
                    elif idx >= 7:
                        colored_line += f"{c['ridge']}{ch}"
                    else:
                        colored_line += ch
                else:
                    colored_line += ch
            output.append(f"{c['border']}│{c['reset']} {colored_line}{c['reset']} {c['border']}│{c['reset']}")
        else:
            output.append(f"│ {line} │")

    # Bottom info
    info = f" Minutiae: {len(minutiae)} points "
    output.append(f"{c['border']}│{c['reset']}{c['info']}{info}{c['reset']}" + " " * (total_w - len(info)) + f"{c['border']}│{c['reset']}")

    if show_minutiae:
        legend = " ◆=Ending ◇=Bifurcation ○=Island "
        output.append(f"{c['border']}│{c['reset']}{c['info']}{legend}{c['reset']}" + " " * (total_w - len(legend)) + f"{c['border']}│{c['reset']}")

    output.append(f"{c['border']}└" + "─" * total_w + "┘" + c["reset"])

    return "\n".join(output)


def generate_fingerprint_id(pattern: PatternType, seed: int,
                             minutiae: List[dict]) -> str:
    """Generate a unique 16-character hex ID for this fingerprint.

    The ID is derived from SHA-256 hashing of the seed, pattern type, and
    sorted minutiae positions, mimicking how real fingerprint identification
    systems create unique identifiers.

    Args:
        pattern: Fingerprint pattern type.
        seed: Random seed used.
        minutiae: List of minutiae dicts.

    Returns:
        16-character uppercase hex string.
    """
    data = f"{seed}:{pattern.value}:"
    for m in sorted(minutiae, key=lambda m: (m["x"], m["y"])):
        data += f"({m['x']:.1f},{m['y']:.1f},{m['type']})"
    return hashlib.sha256(data.encode()).hexdigest()[:16].upper()


def generate_fingerprint_metadata(pattern: PatternType, seed: int,
                                   minutiae: List[dict],
                                   w: int, h: int) -> dict:
    """Generate structured metadata for a fingerprint.

    Args:
        pattern: Pattern type.
        seed: Random seed.
        minutiae: List of minutiae dicts.
        w, h: Grid dimensions.

    Returns:
        Dictionary with all fingerprint metadata.
    """
    return {
        "fingerprint_id": generate_fingerprint_id(pattern, seed, minutiae),
        "pattern_type": pattern.value,
        "pattern_name": PATTERN_NAMES.get(pattern, pattern.value),
        "seed": seed,
        "width": w,
        "height": h,
        "minutiae_count": len(minutiae),
        "minutiae": [
            {
                "x": round(m["x"], 2),
                "y": round(m["y"], 2),
                "angle": round(m["angle"], 4),
                "type": m["type"]
            }
            for m in minutiae
        ],
    }


def list_patterns():
    """Print available pattern types with descriptions."""
    print("Available fingerprint patterns:\n")
    for name, desc in PATTERN_DESCRIPTIONS.items():
        print(f"  {name:15s}  {desc}")
    print()


def generate_comparison(w: int, h: int, seed: int, density: float,
                         contrast: float, show_minutiae: bool,
                         use_color: bool = False):
    """Show all pattern types side by side for comparison.

    Generates all five pattern types using the same seed and renders them
    in a compact side-by-side view.

    Args:
        w, h: Grid dimensions.
        seed: Random seed for reproducibility.
        density: Ridge density multiplier.
        contrast: Contrast multiplier.
        show_minutiae: Whether to show minutiae markers.
        use_color: Whether to use ANSI colors.
    """
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


def generate_batch(count: int, w: int, h: int, pattern: PatternType,
                    seed: int, density: float, contrast: float,
                    show_minutiae: bool, use_color: bool = False):
    """Generate multiple fingerprints with sequential seeds.

    Args:
        count: Number of fingerprints to generate.
        w, h: Grid dimensions.
        pattern: Pattern type to use.
        seed: Starting seed (incremented for each fingerprint).
        density: Ridge density multiplier.
        contrast: Contrast multiplier.
        show_minutiae: Whether to show minutiae markers.
        use_color: Whether to use ANSI colors.
    """
    for i in range(count):
        current_seed = seed + i
        lines, minutiae = render_fingerprint(
            w, h, pattern, current_seed, density, contrast, show_minutiae
        )
        fp_id = generate_fingerprint_id(pattern, current_seed, minutiae)
        print(f"\n--- Fingerprint {i + 1}/{count} ---")
        print(format_fingerprint(lines, w, h, pattern, current_seed,
                                  minutiae, show_minutiae, use_color))
        print(f"  Fingerprint ID: {fp_id}")
        print(f"  Pattern: {pattern.value} | Seed: {current_seed} | Minutiae: {len(minutiae)}")
    print()


def validate_args(args: argparse.Namespace) -> None:
    """Validate command-line arguments and raise SystemExit on errors.

    Args:
        args: Parsed argparse namespace.

    Raises:
        SystemExit: On invalid argument values.
    """
    if args.width < 10 or args.width > 200:
        print(f"Error: width must be between 10 and 200, got {args.width}", file=sys.stderr)
        sys.exit(1)
    if args.height < 10 or args.height > 200:
        print(f"Error: height must be between 10 and 200, got {args.height}", file=sys.stderr)
        sys.exit(1)
    if args.density <= 0 or args.density > 5.0:
        print(f"Error: density must be between 0 and 5.0, got {args.density}", file=sys.stderr)
        sys.exit(1)
    if args.contrast <= 0 or args.contrast > 10.0:
        print(f"Error: contrast must be between 0 and 10.0, got {args.contrast}", file=sys.stderr)
        sys.exit(1)
    if args.batch is not None and args.batch < 1:
        print(f"Error: batch must be >= 1, got {args.batch}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the procedural fingerprint generator CLI."""
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
  %(prog)s --color                  Colorize the output
  %(prog)s --batch 5                Generate 5 fingerprints
  %(prog)s --output print.txt       Save to a file
  %(prog)s --json                   Output metadata as JSON
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
    parser.add_argument("--version", "-v", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Save output to a file instead of stdout")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output fingerprint metadata as JSON")
    parser.add_argument("--color", action="store_true",
                        help="Enable ANSI color output")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Generate N fingerprints with sequential seeds")

    args = parser.parse_args()

    # Validate argument ranges
    validate_args(args)

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

    # JSON output mode
    if args.json:
        if args.compare:
            # Generate metadata for all patterns
            cw, ch = min(args.width, 28), min(args.height, 35)
            all_meta = []
            for pat in [PatternType.LOOP, PatternType.WHORL, PatternType.ARCH,
                        PatternType.TENTED_ARCH, PatternType.DOUBLE_LOOP]:
                _, mins = render_fingerprint(cw, ch, pat, seed, args.density,
                                             args.contrast, args.minutiae)
                all_meta.append(generate_fingerprint_metadata(pat, seed, mins, cw, ch))
            output = json.dumps(all_meta, indent=2)
        else:
            lines, minutiae = render_fingerprint(
                args.width, args.height, pattern, seed, args.density,
                args.contrast, args.minutiae
            )
            meta = generate_fingerprint_metadata(pattern, seed, minutiae,
                                                  args.width, args.height)
            meta["ascii"] = "\n".join(lines)
            output = json.dumps(meta, indent=2)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output + "\n")
            print(f"JSON metadata saved to {args.output}")
        else:
            print(output)
        return

    # Comparison mode
    if args.compare:
        generate_comparison(args.width, args.height, seed, args.density,
                           args.contrast, args.minutiae, args.color)
        return

    # Batch mode
    if args.batch:
        generate_batch(args.batch, args.width, args.height, pattern, seed,
                      args.density, args.contrast, args.minutiae, args.color)
        return

    # Single fingerprint generation
    lines, minutiae = render_fingerprint(
        args.width, args.height, pattern, seed, args.density,
        args.contrast, args.minutiae
    )

    fp_id = generate_fingerprint_id(pattern, seed, minutiae)

    if args.id_only:
        print(fp_id)
        return

    # Build output
    rendered = format_fingerprint(lines, args.width, args.height, pattern, seed,
                                  minutiae, args.minutiae, args.color)
    info_line = f"  Fingerprint ID: {fp_id}"
    meta_line = f"  Pattern: {pattern.value} | Seed: {seed} | Minutiae: {len(minutiae)}"

    full_output = f"\n{rendered}\n{info_line}\n{meta_line}\n"

    # Output to file or stdout
    if args.output:
        with open(args.output, "w") as f:
            f.write(full_output)
        print(f"Fingerprint saved to {args.output}")
    else:
        print(full_output)


if __name__ == "__main__":
    main()