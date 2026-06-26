#!/usr/bin/env python3
"""
Terminal Spirograph — Generate beautiful hypotrochoid & epitrochoid
curve patterns in the terminal using ASCII/Unicode characters.

Supports four curve families: hypotrochoids, epitrochoids, rose curves,
and Lissajous figures. Features animated drawing, rainbow colors, SVG
export, preset galleries, continuous loop mode, and seeded random generation.
"""

import math
import os
import random
import sys
import time
import argparse
from collections import defaultdict

__version__ = "1.1.0"

# Unicode characters for density-based rendering, ordered by "brightness"
DENSITY_CHARS = " .·:;+*#░▒▓█"
DENSITY_CHARS_FINE = " .',:;!|\\/~^+*7#░▒▓█"

# Preset configurations known to produce aesthetically pleasing curves.
# Each preset is (name, curve_type, params_dict).
PRESETS = [
    ("classic",       "hypo",     {"R": 11, "r": 4, "d": 6}),
    ("starflower",    "hypo",     {"R": 21, "r": 8, "d": 5}),
    ("daisy",         "hypo",     {"R": 15, "r": 7, "d": 9}),
    ("vortex",        "hypo",     {"R": 19, "r": 6, "d": 8}),
    ("sunburst",      "epi",      {"R": 9, "r": 4, "d": 7}),
    ("pinwheel",      "epi",      {"R": 7, "r": 3, "d": 5}),
    ("lotus",         "epi",      {"R": 11, "r": 5, "d": 8}),
    ("pentarose",     "rose",     {"k": 5, "n": 3, "d": 10}),
    ("heptarose",     "rose",     {"k": 7, "n": 4, "d": 10}),
    ("trefoil",       "rose",     {"k": 3, "n": 1, "d": 10}),
    ("bowtie",        "lissajous",{"a": 3, "b": 2, "delta": math.pi / 4, "d": 10}),
    ("infinity",      "lissajous",{"a": 3, "b": 4, "delta": math.pi / 2, "d": 10}),
    ("butterfly",     "lissajous",{"a": 5, "b": 6, "delta": math.pi / 2, "d": 10}),
]


def clamp(v, lo, hi):
    """Clamp value v to the range [lo, hi]."""
    return max(lo, min(hi, v))


def hypotrochoid_point(R, r, d, t):
    """Point on a hypotrochoid: circle of radius r rolling inside circle of radius R."""
    x = (R - r) * math.cos(t) + d * math.cos((R - r) / r * t)
    y = (R - r) * math.sin(t) - d * math.sin((R - r) / r * t)
    return x, y


def epitrochoid_point(R, r, d, t):
    """Point on an epitrochoid: circle of radius r rolling outside circle of radius R."""
    x = (R + r) * math.cos(t) - d * math.cos((R + r) / r * t)
    y = (R + r) * math.sin(t) - d * math.sin((R + r) / r * t)
    return x, y


def rose_point(k, n, d, t):
    """Point on a rose curve r = d * cos(k/n * t)."""
    r = d * math.cos(k / n * t)
    x = r * math.cos(t)
    y = r * math.sin(t)
    return x, y


def lissajous_point(a, b, delta, d, t):
    """Point on a Lissajous curve."""
    x = d * math.sin(a * t + delta)
    y = d * math.sin(b * t)
    return x, y


def compute_curve(curve_type, params, num_points):
    """Compute all points for a given curve type.

    Calculates the appropriate parametric range so the curve completes
    one full period, then samples `num_points` evenly-spaced t values.
    """
    points = []
    if curve_type == "hypo":
        R, r, d = params["R"], params["r"], params["d"]
        if r == 0:
            return points
        # Use integer GCD to compute the full period for closure
        R_int, r_int = int(round(R)), int(round(r))
        g = math.gcd(R_int, r_int)
        period = 2 * math.pi * r_int / g  # full period for curve to close
        # Ensure we draw enough loops; minimum 2*pi worth
        t_max = max(period, 2 * math.pi) * max(R_int // g, 1)
        for i in range(num_points):
            t = i / num_points * t_max
            x, y = hypotrochoid_point(R, r, d, t)
            points.append((x, y))

    elif curve_type == "epi":
        R, r, d = params["R"], params["r"], params["d"]
        if r == 0:
            return points
        R_int, r_int = int(round(R)), int(round(r))
        g = math.gcd(R_int, r_int)
        period = 2 * math.pi * r_int / g
        t_max = max(period, 2 * math.pi) * max(R_int // g, 1)
        for i in range(num_points):
            t = i / num_points * t_max
            x, y = epitrochoid_point(R, r, d, t)
            points.append((x, y))

    elif curve_type == "rose":
        k, n, d = params["k"], params["n"], params["d"]
        if n == 0:
            return points
        # Rose curve needs pi * n (if k*n odd) or 2*pi*n to close
        loops_needed = max(n, 2)
        t_max = 2 * math.pi * loops_needed
        for i in range(num_points):
            t = i / num_points * t_max
            x, y = rose_point(k, n, d, t)
            points.append((x, y))

    elif curve_type == "lissajous":
        a, b, delta, d = params["a"], params["b"], params["delta"], params["d"]
        loops_needed = max(a, b, 2)
        t_max = 2 * math.pi * loops_needed
        for i in range(num_points):
            t = i / num_points * t_max
            x, y = lissajous_point(a, b, delta, d, t)
            points.append((x, y))

    return points


def render_frame(points, width, height, chars=DENSITY_CHARS, color_mode=False, frame_idx=0, total_frames=1):
    """Render curve points into a character grid.

    Maps each (x, y) point to a grid cell, counts density per cell,
    then maps density to a character from `chars`. Higher density
    (more overlapping points) maps to "heavier" characters.
    """
    if not points:
        return []

    # Find bounds
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Add small padding to avoid division by zero for degenerate curves
    x_range = max(x_max - x_min, 0.001)
    y_range = max(y_max - y_min, 0.001)

    # Build density map
    grid = defaultdict(int)
    for x, y in points:
        # Map to character coordinates; maintain aspect ratio adjustment
        # Terminal chars are ~2x taller than wide, so stretch x by ~2
        cx = int((x - x_min) / x_range * (width - 1))
        cy = int((y - y_min) / y_range * (height - 1))
        cx = clamp(cx, 0, width - 1)
        cy = clamp(cy, 0, height - 1)
        grid[(cy, cx)] += 1

    if not grid:
        return [" " * width] * height

    max_density = max(grid.values())

    lines = []
    for row in range(height):
        line = []
        for col in range(width):
            density = grid.get((row, col), 0)
            if density == 0:
                line.append(chars[0])
            else:
                idx = int((density / max_density) * (len(chars) - 1))
                idx = clamp(idx, 0, len(chars) - 1)
                line.append(chars[idx])
        lines.append("".join(line))

    return lines


def colorize(lines, palette="auto", frame_idx=0, total_frames=1):
    """Apply ANSI colors to rendered lines.

    Palettes:
        - 'none': no color
        - 'auto': single accent color that shifts per frame
        - 'rainbow': different color per line
        - 'gradient': shifted rainbow per frame (animated rainbow)
    """
    ANSI_COLORS = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "bright_red": "\033[91m",
        "bright_green": "\033[92m",
        "bright_yellow": "\033[93m",
        "bright_blue": "\033[94m",
        "bright_magenta": "\033[95m",
        "bright_cyan": "\033[96m",
    }
    RESET = "\033[0m"

    if palette == "none":
        return lines

    color_list = [
        ANSI_COLORS["bright_cyan"],
        ANSI_COLORS["bright_magenta"],
        ANSI_COLORS["bright_yellow"],
        ANSI_COLORS["bright_green"],
        ANSI_COLORS["cyan"],
        ANSI_COLORS["magenta"],
        ANSI_COLORS["blue"],
    ]

    if palette == "rainbow":
        # Different color per line
        result = []
        for i, line in enumerate(lines):
            color = color_list[i % len(color_list)]
            result.append(f"{color}{line}{RESET}")
        return result
    elif palette == "gradient":
        # Shift colors based on frame — animated rainbow effect
        shift = frame_idx % len(color_list)
        result = []
        for i, line in enumerate(lines):
            color = color_list[(i + shift) % len(color_list)]
            result.append(f"{color}{line}{RESET}")
        return result
    else:
        # Auto — single accent color that shifts with frame
        shift = frame_idx % len(color_list)
        color = color_list[shift]
        return [f"{color}{line}{RESET}" for line in lines]


def generate_params(curve_type, seed=None):
    """Generate random aesthetically pleasing parameters.

    If seed is given, the random generator is seeded for reproducibility.
    """
    rng = random.Random(seed)
    if curve_type == "hypo":
        R = rng.choice([7, 9, 11, 13, 15, 17, 19, 21])
        r = rng.choice([2, 3, 4, 5, 6, 7, 8])
        if r >= R:
            r = R - 2
        d = rng.choice([r - 1, r, r + 1, r + 2, r * 0.5, r * 1.5])
        d = max(1, abs(d))
        return {"R": R, "r": r, "d": d}
    elif curve_type == "epi":
        R = rng.choice([5, 7, 9, 11])
        r = rng.choice([2, 3, 4, 5])
        d = rng.choice([r - 1, r, r + 1, r * 0.7, r * 1.3])
        d = max(1, abs(d))
        return {"R": R, "r": r, "d": d}
    elif curve_type == "rose":
        k = rng.randint(2, 9)
        n = rng.randint(1, 7)
        d = rng.randint(5, 15)
        return {"k": k, "n": n, "d": d}
    elif curve_type == "lissajous":
        a = rng.randint(1, 9)
        b = rng.randint(1, 9)
        delta = rng.choice([0, math.pi / 6, math.pi / 4, math.pi / 3, math.pi / 2])
        d = rng.randint(8, 15)
        return {"a": a, "b": b, "delta": delta, "d": d}
    return {}


def get_curve_label(curve_type, params):
    """Get a human-readable label for the curve."""
    if curve_type == "hypo":
        return f"Hypotrochoid(R={params['R']}, r={params['r']}, d={params['d']})"
    elif curve_type == "epi":
        return f"Epitrochoid(R={params['R']}, r={params['r']}, d={params['d']})"
    elif curve_type == "rose":
        return f"Rose(k={params['k']}, n={params['n']}, d={params['d']})"
    elif curve_type == "lissajous":
        return f"Lissajous(a={params['a']}, b={params['b']}, δ={params['delta']:.2f}, d={params['d']})"
    return "Unknown curve"


def get_terminal_size():
    """Get terminal dimensions, with fallback."""
    try:
        import shutil
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    except Exception:
        return 80, 24


def clear_screen():
    """Clear the terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def hide_cursor():
    """Hide the terminal cursor for cleaner animation."""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    """Restore the terminal cursor."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def export_svg(points, curve_type, params, filepath, width=800, height=800):
    """Export curve as an SVG file for high-quality rendering.

    Generates an SVG document with a polyline of the computed points,
    suitable for printing or embedding in documents.
    """
    if not points:
        print(f"Warning: no points to export for {filepath}", file=sys.stderr)
        return

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Add 5% padding
    pad = max(x_max - x_min, y_max - y_min, 0.001) * 0.05
    x_min -= pad
    x_max += pad
    y_min -= pad
    y_max += pad

    margin = 20
    svg_w = width + 2 * margin
    svg_h = height + 2 * margin

    # Build polyline points string
    svg_points = []
    for x, y in points:
        sx = margin + (x - x_min) / (x_max - x_min) * width
        sy = margin + (y_max - y) / (y_max - y_min) * height  # flip y for SVG
        svg_points.append(f"{sx:.2f},{sy:.2f}")

    points_str = " ".join(svg_points)
    label = get_curve_label(curve_type, params)

    svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">
  <title>{label}</title>
  <desc>Generated by Terminal Spirograph v{__version__}</desc>
  <rect width="{svg_w}" height="{svg_h}" fill="#0a0a0a"/>
  <polyline points="{points_str}"
    fill="none" stroke="#00ddff" stroke-width="0.5" stroke-linejoin="round"/>
  <text x="{margin}" y="{svg_h - 5}" fill="#555" font-size="12" font-family="monospace">{label}</text>
</svg>
"""

    try:
        with open(filepath, "w") as f:
            f.write(svg_content)
        print(f"  SVG exported to {filepath} ({len(points)} points)")
    except OSError as e:
        print(f"  Error writing SVG: {e}", file=sys.stderr)


def animate_curve(curve_type, params, width, height, num_points, frames, fps, palette, chars):
    """Animate a spirograph being drawn progressively."""
    all_points = compute_curve(curve_type, params, num_points)
    if not all_points:
        print("Error: Could not compute curve points.")
        return

    frame_delay = 1.0 / fps
    points_per_frame = max(1, len(all_points) // frames)

    hide_cursor()

    try:
        for frame in range(frames + 1):
            visible_points = all_points[:min((frame + 1) * points_per_frame, len(all_points))]
            lines = render_frame(visible_points, width, height, chars)

            if sys.stdout.isatty():
                lines = colorize(lines, palette, frame, frames)

            clear_screen()
            label = get_curve_label(curve_type, params)
            progress = min(100, int((frame + 1) / frames * 100))
            header = f"  Terminal Spirograph — {label}  [{progress}%]"
            print(header)
            print("  " + "─" * (width - 4))

            for line in lines:
                print(line)

            print("  " + "─" * (width - 4))
            print(f"  Points: {len(visible_points)}/{len(all_points)}  |  Press Ctrl+C to stop")
            sys.stdout.flush()

            time.sleep(frame_delay)

        # Hold final frame briefly
        if sys.stdout.isatty():
            try:
                time.sleep(2)
            except KeyboardInterrupt:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        clear_screen()


def static_render(curve_type, params, width, height, num_points, palette, chars):
    """Render a static spirograph."""
    all_points = compute_curve(curve_type, params, num_points)
    if not all_points:
        print("Error: Could not compute curve points.")
        return

    lines = render_frame(all_points, width, height, chars)

    if sys.stdout.isatty():
        lines = colorize(lines, palette, 0, 1)

    label = get_curve_label(curve_type, params)
    print()
    print(f"  Terminal Spirograph — {label}")
    print("  " + "─" * (width - 4))

    for line in lines:
        print(line)

    print("  " + "─" * (width - 4))
    print(f"  {len(all_points)} points rendered  |  Curve: {curve_type}")
    print()


def gallery_mode(width, height, num_points, palette, chars, continuous=False):
    """Show a gallery of different curve types.

    If continuous is True, loop forever until Ctrl+C is pressed.
    """
    curves = [
        ("hypo", {"R": 11, "r": 4, "d": 6}),
        ("epi", {"R": 7, "r": 3, "d": 5}),
        ("rose", {"k": 5, "n": 3, "d": 10}),
        ("lissajous", {"a": 3, "b": 4, "delta": math.pi / 2, "d": 10}),
    ]

    try:
        while True:
            for curve_type, params in curves:
                clear_screen()
                static_render(curve_type, params, width, height, num_points, palette, chars)
                time.sleep(1.5)
            if not continuous:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if continuous:
            clear_screen()


def loop_mode(width, height, num_points, palette, chars, fps, seed=None):
    """Continuously generate and display random spirographs until Ctrl+C.

    Each iteration picks a random curve type and random parameters,
    renders statically, then waits briefly before the next.
    """
    curve_types = ["hypo", "epi", "rose", "lissajous"]
    iteration = 0
    rng = random.Random(seed)

    try:
        while True:
            curve_type = rng.choice(curve_types)
            params = generate_params(curve_type, seed=(seed + iteration) if seed is not None else None)
            clear_screen()
            static_render(curve_type, params, width, height, num_points, palette, chars)
            iteration += 1
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        clear_screen()


def list_presets():
    """Print all available preset configurations."""
    print("Available presets:")
    print("=" * 60)
    for name, curve_type, params in PRESETS:
        label = get_curve_label(curve_type, params)
        print(f"  {name:15s}  {label}")
    print()


CURVE_TYPES = ["hypo", "epi", "rose", "lissajous"]


def main():
    parser = argparse.ArgumentParser(
        description="Terminal Spirograph — Generate beautiful curve patterns in the terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                            Random spirograph, animated
  %(prog)s --hypo --R 11 --r 4 --d 6 Hypotrochoid with specific params
  %(prog)s --epi --random             Random epitrochoid
  %(prog)s --rose --random            Random rose curve
  %(prog)s --lissajous --random       Random Lissajous curve
  %(prog)s --random --palette rainbow Rainbow-colored random curve
  %(prog)s --gallery                  Show a gallery of different curves
  %(prog)s --loop                     Continuous random spirographs
  %(prog)s --preset classic           Named preset configuration
  %(prog)s --list-presets             Show all available presets
  %(prog)s --seed 42 --random         Reproducible random generation
  %(prog)s --export-svg out.svg       Export as SVG
  %(prog)s --hypo --R 21 --r 8 --d 5 --static
        """
    )

    # Version
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # Curve type
    parser.add_argument("--hypo", action="store_true", help="Use hypotrochoid curve")
    parser.add_argument("--epi", action="store_true", help="Use epitrochoid curve")
    parser.add_argument("--rose", action="store_true", help="Use rose curve")
    parser.add_argument("--lissajous", action="store_true", help="Use Lissajous curve")
    parser.add_argument("--random", action="store_true", help="Generate random parameters")

    # Presets
    parser.add_argument("--preset", type=str, default=None,
                        help="Use a named preset (e.g. 'classic', 'starflower')")
    parser.add_argument("--list-presets", action="store_true",
                        help="List all available presets and exit")

    # Hypotrochoid / Epitrochoid params
    parser.add_argument("--R", type=float, help="Outer radius (hypo/epi)")
    parser.add_argument("--r", type=float, help="Inner radius (hypo/epi)")
    parser.add_argument("--d", type=float, help="Pen distance (hypo/epi)")

    # Rose params
    parser.add_argument("--k", type=int, help="Numerator parameter (rose)")
    parser.add_argument("--n", type=int, help="Denominator parameter (rose)")

    # Lissajous params
    parser.add_argument("--a", type=int, help="Frequency a (lissajous)")
    parser.add_argument("--b", type=int, help="Frequency b (lissajous)")
    parser.add_argument("--delta", type=float, help="Phase shift δ (lissajous)")

    # Display options
    parser.add_argument("--width", type=int, default=None, help="Output width (default: terminal width)")
    parser.add_argument("--height", type=int, default=None, help="Output height (default: terminal height - 4)")
    parser.add_argument("--points", type=int, default=20000, help="Number of curve points (default: 20000)")
    parser.add_argument("--static", action="store_true", help="Static render (no animation)")
    parser.add_argument("--animate", action="store_true", help="Animate drawing (default)")
    parser.add_argument("--frames", type=int, default=40, help="Number of animation frames (default: 40)")
    parser.add_argument("--fps", type=int, default=15, help="Animation FPS (default: 15)")
    parser.add_argument("--palette", choices=["auto", "rainbow", "gradient", "none"], default="auto",
                        help="Color palette (default: auto)")
    parser.add_argument("--chars", choices=["block", "fine"], default="block",
                        help="Character set: block (default) or fine")

    # Gallery / loop modes
    parser.add_argument("--gallery", action="store_true", help="Show gallery of different curve types")
    parser.add_argument("--loop", action="store_true",
                        help="Continuously generate random spirographs until Ctrl+C")

    # Reproducibility
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible generation")

    # Export
    parser.add_argument("--export-svg", type=str, default=None, metavar="FILE",
                        help="Export curve as SVG file")

    args = parser.parse_args()

    # List presets and exit
    if args.list_presets:
        list_presets()
        return

    # Seed the random module if requested (for any random.choices in the code)
    if args.seed is not None:
        random.seed(args.seed)

    # Determine curve type
    curve_type = None
    if args.hypo:
        curve_type = "hypo"
    elif args.epi:
        curve_type = "epi"
    elif args.rose:
        curve_type = "rose"
    elif args.lissajous:
        curve_type = "lissajous"

    # Handle preset
    if args.preset:
        preset_match = None
        for name, ct, p in PRESETS:
            if name == args.preset:
                preset_match = (ct, p)
                break
        if preset_match is None:
            print(f"Error: Unknown preset '{args.preset}'. Use --list-presets to see available presets.",
                  file=sys.stderr)
            sys.exit(1)
        curve_type = preset_match[0]
        params = dict(preset_match[1])  # copy to avoid mutating the preset
    else:
        if curve_type is None:
            curve_type = random.choice(CURVE_TYPES)

        # Build parameters
        params = {}
        if args.random or (curve_type in ("hypo", "epi") and args.R is None):
            params = generate_params(curve_type, seed=args.seed)
        else:
            if curve_type in ("hypo", "epi"):
                params["R"] = args.R if args.R is not None else 11
                params["r"] = args.r if args.r is not None else 4
                params["d"] = args.d if args.d is not None else params["r"]
            elif curve_type == "rose":
                params["k"] = args.k if args.k is not None else 5
                params["n"] = args.n if args.n is not None else 3
                params["d"] = 10
            elif curve_type == "lissajous":
                params["a"] = args.a if args.a is not None else 3
                params["b"] = args.b if args.b is not None else 4
                params["delta"] = args.delta if args.delta is not None else math.pi / 2
                params["d"] = 10

    # Validate params for hypo/epi: r must not be 0
    if curve_type in ("hypo", "epi") and params.get("r", 0) == 0:
        print("Error: Inner radius r cannot be 0 (division by zero in parametric equations).",
              file=sys.stderr)
        sys.exit(1)

    # Validate params for rose: n must not be 0
    if curve_type == "rose" and params.get("n", 0) == 0:
        print("Error: Denominator parameter n cannot be 0 (division by zero in rose curve).",
              file=sys.stderr)
        sys.exit(1)

    # Validate lissajous: a and b must not both be 0
    if curve_type == "lissajous" and params.get("a", 0) == 0 and params.get("b", 0) == 0:
        print("Error: Both frequencies a and b cannot be 0.",
              file=sys.stderr)
        sys.exit(1)

    tw, th = get_terminal_size()
    w = args.width or (tw - 2)
    h = args.height or (th - 6)
    chars = DENSITY_CHARS if args.chars == "block" else DENSITY_CHARS_FINE

    # Gallery mode
    if args.gallery:
        gallery_mode(w, h, args.points, args.palette, chars, continuous=False)
        return

    # Loop mode — continuous random spirographs
    if args.loop:
        loop_mode(w, h, args.points, args.palette, chars, args.fps, seed=args.seed)
        return

    # Export SVG if requested
    if args.export_svg:
        all_points = compute_curve(curve_type, params, args.points)
        if not all_points:
            print("Error: Could not compute curve points for SVG export.", file=sys.stderr)
            sys.exit(1)
        export_svg(all_points, curve_type, params, args.export_svg)
        return

    # Normal render
    if args.static or not sys.stdout.isatty():
        static_render(curve_type, params, w, h, args.points,
                      args.palette if sys.stdout.isatty() else "none", chars)
    else:
        animate_curve(curve_type, params, w, h, args.points, args.frames, args.fps, args.palette, chars)


if __name__ == "__main__":
    main()