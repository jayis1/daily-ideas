#!/usr/bin/env python3
"""
ASCII Single-Image Random Dot Stereogram (SIRDS) Generator

Renders depth maps into terminal stereograms using characters as "dots".
Each row is built so that matching character pairs are separated by a
horizontal offset proportional to the depth at that pixel. When the viewer
either crosses their eyes (cross-eyed) or relaxes them (wall-eyed), the
left and right copies fuse and the depth pattern pops out in 3D.

Usage:
    python3 stereogram.py [pattern] [options]

Examples:
    python3 stereogram.py                       # default sphere
    python3 stereogram.py heart                 # a 3D heart
    python3 stereogram.py text:HI               # the word "HI" in 3D
    python3 stereogram.py torus 100 30          # bigger donut
    python3 stereogram.py spiral --seed 42      # reproducible run
    python3 stereogram.py cone --invert         # cone sinks away
    python3 stereogram.py --list-patterns       # list all patterns
    python3 stereogram.py sphere --show-depth    # print depth map instead
    python3 stereogram.py heart --save out.txt  # write to file
"""

import argparse
import math
import random
import sys

__version__ = "1.1.1"

# Characters ordered from sparse -> dense to give subtle texture variety.
# Using mostly similar-density characters so that the stereogram texture
# itself doesn't give away the shape (it should be hidden in the noise).
RAMP = " .:-=+*#%@"
NOISE_CHARS = ".,:;~=+*o#%@#"


# --------------------------------------------------------------------------- #
# Depth-map generators                                                        #
# --------------------------------------------------------------------------- #
# Each returns a 2D list of floats in [0.0, 1.0] where 1.0 = closest to viewer.
# --------------------------------------------------------------------------- #

def _empty(w, h):
    """Return a w×h grid filled with 0.0 (no depth)."""
    return [[0.0 for _ in range(w)] for _ in range(h)]


def depth_sphere(w, h):
    """A sphere centered in the image (front hemisphere)."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2
    r = min(w, h * 2) / 2 * 0.75  # account for char aspect ratio
    for y in range(h):
        for x in range(w):
            dx = (x - cx) / r
            dy = (y - cy) / r * 2  # chars are taller than wide
            d2 = dx * dx + dy * dy
            if d2 <= 1.0:
                z = math.sqrt(1.0 - d2)
                grid[y][x] = z  # front hemisphere
    return grid


def depth_torus(w, h):
    """A torus (donut) shape."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2
    R = min(w, h * 2) / 3.5       # major radius
    r = R * 0.35                   # minor radius
    for y in range(h):
        for x in range(w):
            dx = (x - cx)
            dy = (y - cy) * 2
            dist = math.sqrt(dx * dx + dy * dy)
            # distance from the ring circle
            dring = dist - R
            if abs(dring) <= r:
                z = math.sqrt(r * r - dring * dring)
                grid[y][x] = z / r
    return grid


def depth_cone(w, h):
    """A cone pointing toward the viewer."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2
    rmax = min(w, h * 2) / 2 * 0.8
    for y in range(h):
        for x in range(w):
            dx = (x - cx)
            dy = (y - cy) * 2
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= rmax:
                grid[y][x] = 1.0 - dist / rmax
    return grid


def depth_pyramid(w, h):
    """A square pyramid pointing toward the viewer."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2
    half = min(w, h * 2) / 2 * 0.8
    for y in range(h):
        for x in range(w):
            dx = abs(x - cx)
            dy = abs(y - cy) * 2
            cheby = max(dx, dy)
            if cheby <= half:
                grid[y][x] = 1.0 - cheby / half
    return grid


def depth_wave(w, h):
    """Ripple / sine wave field."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2
    for y in range(h):
        for x in range(w):
            dx = (x - cx) / w * 6
            dy = (y - cy) / h * 6
            val = (math.sin(dx) + math.sin(dy * 2)) / 2
            grid[y][x] = (val + 1) / 2  # normalize to 0..1
    return grid


def depth_steps(w, h):
    """Concentric square steps like a ziggurat."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2
    half = min(w, h * 2) / 2 * 0.9
    steps = 5
    for y in range(h):
        for x in range(w):
            dx = abs(x - cx)
            dy = abs(y - cy) * 2
            cheby = max(dx, dy)
            if cheby <= half:
                level = int((1.0 - cheby / half) * steps)
                grid[y][x] = level / steps
    return grid


def depth_heart(w, h):
    """A heart shape using the implicit heart curve."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2 - h * 0.05
    scale = min(w, h * 2) / 3.5
    for y in range(h):
        for x in range(w):
            nx = (x - cx) / scale
            ny = -(y - cy) * 2 / scale   # flip y
            # Implicit heart curve: (x² + y² - 1)³ - x²y³ ≤ 0
            lhs = (nx * nx + ny * ny - 1) ** 3 - nx * nx * ny * ny * ny
            if lhs <= 0:
                # depth based on distance from edge (fake 3D)
                dist_edge = abs(lhs) ** 0.2
                grid[y][x] = max(0.0, min(1.0, dist_edge))
    return grid


def depth_diamond(w, h):
    """A diamond (rotated square) pointing toward the viewer."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2
    half = min(w, h * 2) / 2 * 0.85
    for y in range(h):
        for x in range(w):
            dx = abs(x - cx)
            dy = abs(y - cy) * 2
            manh = dx + dy  # Manhattan distance gives a diamond
            if manh <= half:
                grid[y][x] = 1.0 - manh / half
    return grid


def depth_spiral(w, h):
    """An Archimedean spiral ramp — depth rises as you follow the arm."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2
    rmax = min(w, h * 2) / 2
    turns = 2.5
    for y in range(h):
        for x in range(w):
            dx = (x - cx)
            dy = (y - cy) * 2
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= rmax and dist > 0.5:
                theta = math.atan2(dy, dx)
                # Unwind angle so it increases monotonically with radius.
                # atan2 returns [-pi, pi]; add 2*pi for negative to get [0, 2pi).
                if theta < 0:
                    theta += 2 * math.pi
                # Number of full turns reached at this radius:
                r_turns = (dist / rmax) * turns
                # Fractional position within the current turn (0..1):
                frac = r_turns - math.floor(r_turns)
                # Depth is high on the inner half of each turn arm, low between.
                grid[y][x] = max(0.0, min(1.0, 1.0 - abs(frac - 0.5) * 2)) * (dist / rmax)
    return grid


def depth_tunnel(w, h):
    """A tunnel / vortex — concentric rings getting deeper toward the center."""
    grid = _empty(w, h)
    cx, cy = w / 2, h / 2
    rmax = min(w, h * 2) / 2
    rings = 6
    for y in range(h):
        for x in range(w):
            dx = (x - cx)
            dy = (y - cy) * 2
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= rmax:
                # Distance as a fraction of rmax:
                frac = dist / rmax
                # Sawtooth that repeats `rings` times across the radius:
                ring_frac = (frac * rings) % 1.0
                # Closer to center = closer to viewer (pop out), rings recede:
                base = 1.0 - frac
                grid[y][x] = max(0.0, min(1.0, base * (0.5 + 0.5 * ring_frac)))
    return grid


def depth_text(text, w, h):
    """Render text as a depth map using a built-in 5×5 bitmap font."""
    glyphs = _build_font()
    grid = _empty(w, h)
    if not text:
        return grid
    # Layout the text horizontally, centered.
    def _glyph_width(ch):
        g = glyphs.get(ch.upper(), glyphs.get("?", glyphs["A"]))
        return len(g[0])

    total_w = sum(_glyph_width(ch) + 1 for ch in text)
    if total_w >= w:
        text = text[: max(1, w // 6)]
        total_w = sum(_glyph_width(ch) + 1 for ch in text)
    start_x = (w - total_w) // 2
    start_y = (h - 5) // 2
    cx = start_x
    for ch in text:
        glyph = glyphs.get(ch.upper(), glyphs.get("?", glyphs["A"]))
        gw = len(glyph[0])
        for row in range(5):
            for col in range(gw):
                if glyph[row][col] == 1:
                    px, py = cx + col, start_y + row
                    if 0 <= px < w and 0 <= py < h:
                        grid[py][px] = 1.0
        cx += gw + 1
    return grid


def depth_random(w, h, rng=None):
    """Random blurry blobs — pure fun to practice seeing stereograms.

    Accepts an optional random.Random instance for reproducible output.
    """
    if rng is None:
        rng = random
    grid = _empty(w, h)
    num_blobs = rng.randint(3, 7)
    for _ in range(num_blobs):
        bx = rng.uniform(0, w)
        by = rng.uniform(0, h)
        br = rng.uniform(w * 0.1, w * 0.3)
        peak = rng.uniform(0.5, 1.0)
        for y in range(h):
            for x in range(w):
                d = math.sqrt((x - bx) ** 2 + ((y - by) * 2) ** 2)
                if d < br:
                    val = peak * (1 - d / br)
                    if val > grid[y][x]:
                        grid[y][x] = val
    return grid


# --------------------------------------------------------------------------- #
# Minimal 5×5 bitmap font for text stereograms                                #
# --------------------------------------------------------------------------- #
def _build_font():
    """Return a dict mapping uppercase letters & digits to 5-row glyph arrays.

    Each glyph is a list of 5 lists (rows) of 0/1.
    """
    raw = {
        "A": "01110/10001/10001/11111/10001",
        "B": "11110/10001/11110/10001/11110",
        "C": "01111/10000/10000/10000/01111",
        "D": "11110/10001/10001/10001/11110",
        "E": "11111/10000/11110/10000/11111",
        "F": "11111/10000/11110/10000/10000",
        "G": "01111/10000/10111/10001/01111",
        "H": "10001/10001/11111/10001/10001",
        "I": "11111/00100/00100/00100/11111",
        "J": "00111/00010/00010/10010/01100",
        "K": "10001/10010/11100/10010/10001",
        "L": "10000/10000/10000/10000/11111",
        "M": "10001/11011/10101/10001/10001",
        "N": "10001/11001/10101/10011/10001",
        "O": "01110/10001/10001/10001/01110",
        "P": "11110/10001/11110/10000/10000",
        "Q": "01110/10001/10101/10010/01101",
        "R": "11110/10001/11110/10010/10001",
        "S": "01111/10000/01110/00001/11110",
        "T": "11111/00100/00100/00100/00100",
        "U": "10001/10001/10001/10001/01110",
        "V": "10001/10001/10001/01010/00100",
        "W": "10001/10001/10101/11011/10001",
        "X": "10001/01010/00100/01010/10001",
        "Y": "10001/01010/00100/00100/00100",
        "Z": "11111/00010/00100/01000/11111",
        "0": "01110/10001/10001/10001/01110",
        "1": "00100/01100/00100/00100/01110",
        "2": "01110/10001/00110/01000/11111",
        "3": "11110/00001/00110/00001/11110",
        "4": "00010/00110/01010/11111/00010",
        "5": "11111/10000/11110/00001/11110",
        "6": "01110/10000/11110/10001/01110",
        "7": "11111/00001/00010/00100/00100",
        "8": "01110/10001/01110/10001/01110",
        "9": "01110/10001/01111/00001/01110",
        " ": "00000/00000/00000/00000/00000",
        "!": "00100/00100/00100/00000/00100",
        "?": "01110/10001/00110/00000/00100",
        ".": "00000/00000/00000/00000/00100",
        ",": "00000/00000/00000/00100/01000",
        "-": "00000/00000/11111/00000/00000",
        "/": "00001/00010/00100/01000/10000",
        ":": "00000/00100/00000/00100/00000",
    }
    font = {}
    for ch, spec in raw.items():
        rows = [[int(c) for c in row] for row in spec.split("/")]
        font[ch] = rows
    return font


# --------------------------------------------------------------------------- #
# Stereogram renderer                                                         #
# --------------------------------------------------------------------------- #

def render_stereogram(depth, width, height, eye_separation=14, depth_mul=0.33,
                      rng=None):
    """Render a depth map into an ASCII single-image random dot stereogram.

    Algorithm (per-row):
      1. Create a random character strip of length = eye_separation.
      2. For each pixel x, if depth[y][x] == 0 (background), just use the
         random strip (repeating every eye_separation chars).
      3. If there is depth, shift the matching point by:
             separation = eye_separation - depth * eye_separation * depth_mul
         This means closer objects have the matching character closer together,
         causing the fused image to pop *toward* the viewer.
      4. If the shifted position is already within the row, copy that character
         so the left/right eyes see the same symbol at the two positions.

    Args:
        depth: 2D list [height][width] of floats in [0.0, 1.0].
        width: Character width of the output.
        height: Character height of the output.
        eye_separation: Base pixel separation for the repeating pattern.
        depth_mul: Multiplier controlling how strongly depth shifts the
            pattern (0.0 = flat, ~0.33 = typical, >0.5 = dramatic/hard to fuse).
        rng: Optional random.Random instance for reproducible output.

    Returns:
        A single string with `height` newline-separated rows of `width` chars.
    """
    if rng is None:
        rng = random
    lines = []
    for y in range(height):
        row = [rng.choice(NOISE_CHARS) for _ in range(width)]

        for x in range(width):
            d = depth[y][x]
            if d <= 0.001:
                continue
            # Desired pixel-separation between the two matching samples.
            sep = int(round(eye_separation - d * eye_separation * depth_mul))
            if sep < 2:
                sep = 2
            left = x - sep
            if 0 <= left < width:
                # Copy the character from the left matching position so that
                # when the eyes fuse, both see the same symbol here.
                row[x] = row[left]

        lines.append("".join(row))
    return "\n".join(lines)


def render_depth_map(depth, width, height):
    """Render a depth map as a human-readable ASCII shading for debugging.

    Maps depth values through RAMP so you can see the shape without needing
    to fuse the stereogram.
    """
    lines = []
    n = len(RAMP) - 1
    for y in range(height):
        row = []
        for x in range(width):
            d = depth[y][x]
            # Clamp both bounds: negative depth must map to RAMP[0], not wrap
            # around via Python's negative indexing.
            idx = max(0, min(n, int(d * n)))
            row.append(RAMP[idx])
        lines.append("".join(row))
    return "\n".join(lines)


def invert_depth(depth, width, height):
    """Return a new depth grid with depth inverted (1 - d).

    Makes pop-out shapes sink in, and vice versa. Useful for cross-eyed
    viewers who perceive depth reversed, or just for variety.
    """
    return [[1.0 - depth[y][x] for x in range(width)] for y in range(height)]


# --------------------------------------------------------------------------- #
# Pattern dispatcher                                                          #
# --------------------------------------------------------------------------- #

PATTERNS = {
    "sphere": depth_sphere,
    "torus": depth_torus,
    "cone": depth_cone,
    "pyramid": depth_pyramid,
    "wave": depth_wave,
    "steps": depth_steps,
    "heart": depth_heart,
    "diamond": depth_diamond,
    "spiral": depth_spiral,
    "tunnel": depth_tunnel,
    "random": depth_random,
}


def make_depth(pattern, w, h, rng=None):
    """Build a depth map for the given pattern name or 'text:STRING'.

    Args:
        pattern: One of the keys in PATTERNS, or 'text:STRING'.
        w: Width in characters.
        h: Height in characters.
        rng: Optional random.Random for reproducible 'random' pattern.

    Returns:
        A 2D list [h][w] of floats in [0.0, 1.0].
    """
    if pattern.startswith("text:"):
        return depth_text(pattern[5:], w, h)
    fn = PATTERNS.get(pattern)
    if fn is None:
        raise ValueError(
            f"Unknown pattern '{pattern}'. "
            f"Choose from: {', '.join(list(PATTERNS) + ['text:...'])}"
        )
    if pattern == "random" and rng is not None:
        return fn(w, h, rng=rng)
    return fn(w, h)


# --------------------------------------------------------------------------- #
# Alignment guide                                                             #
# --------------------------------------------------------------------------- #

def alignment_guide(width, eye_sep):
    """Return a guide line with two markers separated by eye_sep characters.

    When the two markers appear as one (fused), your eyes are converged at
    the right distance and the stereogram should pop out.
    """
    if eye_sep >= width:
        return " " * width
    left_pos = (width - eye_sep) // 2
    right_pos = left_pos + eye_sep
    guide = [" "] * width
    guide[left_pos] = "|"
    guide[right_pos] = "|"
    return "".join(guide)


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║          ASCII  STEREOGRAM  GENERATOR  (SIRDS)               ║
║                                                              ║
║  Relax your eyes (wall-eyed) or cross them until the         ║
║  two halves of each row fuse, then a 3D shape pops out.     ║
║                                                              ║
║  Tip: hold the screen close to your face, then slowly       ║
║  pull back while keeping your eyes unfocused.               ║
╚══════════════════════════════════════════════════════════════╝
"""


def build_parser():
    """Construct and return the argparse.ArgumentParser for the CLI."""
    p = argparse.ArgumentParser(
        prog="stereogram.py",
        description="Generate single-image random dot stereograms (SIRDS) "
                    "in the terminal using ASCII characters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "patterns:\n"
            "  sphere   A floating sphere (easiest to see)\n"
            "  torus    A 3D donut\n"
            "  cone     A cone pointing toward you\n"
            "  pyramid  A square pyramid\n"
            "  diamond  A rotated square (diamond)\n"
            "  wave     A rippling sine wave field\n"
            "  steps    Concentric ziggurat steps\n"
            "  heart    A 3D heart\n"
            "  spiral   An Archimedean spiral ramp\n"
            "  tunnel   A receding ringed vortex\n"
            "  random   Random blurry blobs\n"
            "  text:STR Render the word STR in 3D (e.g. text:HI)\n"
            "\n"
            "examples:\n"
            "  python3 stereogram.py heart\n"
            "  python3 stereogram.py text:HELLO 100 24\n"
            "  python3 stereogram.py spiral --seed 42 --depth-strength 0.4\n"
            "  python3 stereogram.py cone --invert --guide\n"
            "  python3 stereogram.py --list-patterns\n"
        ),
    )
    p.add_argument("pattern", nargs="?", default="sphere",
                   help="depth pattern to render (default: sphere). "
                        "Use 'text:STRING' to render text, or "
                        "'random' for blobs.")
    p.add_argument("width", nargs="?", type=int, default=72,
                   help="character width of the stereogram (default: 72)")
    p.add_argument("height", nargs="?", type=int, default=24,
                   help="character height of the stereogram (default: 24)")
    p.add_argument("--version", action="version",
                   version=f"ASCII Stereogram Generator {__version__}")
    p.add_argument("--seed", type=int, default=None,
                   help="random seed for reproducible 'random' pattern "
                        "and texture (default: none)")
    p.add_argument("--depth-strength", type=float, default=0.33,
                   help="multiplier for depth effect, 0.0-0.5 "
                        "(default: 0.33). Higher = more dramatic 3D but "
                        "harder to fuse.")
    p.add_argument("--invert", action="store_true",
                   help="invert depth so pop-out shapes sink in and vice "
                        "versa (good for cross-eyed viewing)")
    p.add_argument("--no-banner", action="store_true",
                   help="suppress the banner and info header (useful for "
                        "piping output to a file or another command)")
    p.add_argument("--guide", action="store_true",
                   help="print alignment guide markers above the stereogram; "
                        "fuse the two markers into one to lock in the view")
    p.add_argument("--show-depth", action="store_true",
                   help="print the depth map as ASCII shading instead of "
                        "the stereogram (for debugging / previewing the shape)")
    p.add_argument("--save", metavar="FILE", default=None,
                   help="also write the output to FILE")
    p.add_argument("--list-patterns", action="store_true",
                   help="list all available patterns and exit")
    return p


def _validate_args(args):
    """Validate parsed args; return (ok, error_message)."""
    if args.width < 10 or args.width > 1000:
        return False, f"width must be between 10 and 1000, got {args.width}"
    if args.height < 3 or args.height > 500:
        return False, f"height must be between 3 and 500, got {args.height}"
    if not (0.0 <= args.depth_strength <= 1.0):
        return False, (
            f"--depth-strength must be in [0.0, 1.0], got {args.depth_strength}"
        )
    return True, None


def main(argv=None):
    """CLI entry point. Returns a process exit code."""
    if argv is None:
        argv = sys.argv
    parser = build_parser()

    args = parser.parse_args(argv[1:])

    # Handle --list-patterns via the parsed flag so that argparse prefix
    # abbreviations (e.g. --list) are honoured consistently.
    if args.list_patterns:
        print("Available patterns:")
        for name, fn in PATTERNS.items():
            doc = (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else ""
            print(f"  {name:10s} {doc}")
        print(f"  {'text:STR':10s} Render the word STR in 3D")
        return 0

    ok, err = _validate_args(args)
    if not ok:
        print(f"Error: {err}", file=sys.stderr)
        return 2

    rng = random.Random(args.seed) if args.seed is not None else random

    pattern = args.pattern
    width = args.width
    height = args.height

    # Scale eye separation with width for best viewing.
    eye_sep = max(8, min(20, width // 6))

    try:
        depth = make_depth(pattern, width, height, rng=rng)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(f"Available patterns: {', '.join(PATTERNS)}, text:STRING",
              file=sys.stderr)
        return 1

    if args.invert:
        depth = invert_depth(depth, width, height)

    # Build the output body.
    if args.show_depth:
        body = render_depth_map(depth, width, height)
        header_extra = "  Mode    : depth-map preview"
    else:
        body = render_stereogram(
            depth, width, height,
            eye_separation=eye_sep, depth_mul=args.depth_strength, rng=rng,
        )
        header_extra = "  Mode    : stereogram"

    # Assemble output.
    parts = []
    if not args.no_banner:
        parts.append(BANNER)
        parts.append(f"  Pattern : {pattern}")
        parts.append(f"  Size    : {width} x {height}")
        parts.append(f"  Eye sep : {eye_sep} chars")
        if args.seed is not None:
            parts.append(f"  Seed    : {args.seed}")
        if args.invert:
            parts.append("  Invert  : on")
        parts.append(f"  Strength: {args.depth_strength}")
        parts.append(header_extra)
        parts.append("")
        parts.append("─" * width)
        parts.append("")

    if args.guide and not args.show_depth:
        guide = alignment_guide(width, eye_sep)
        parts.append(guide)
        parts.append("")

    parts.append(body)

    if not args.no_banner:
        parts.append("")
        parts.append("─" * width)
        parts.append("")
        parts.append("  ↑ Stare at the block above and let your eyes relax/cross.")
        parts.append("  The hidden 3D shape will emerge from the noise.")
        parts.append("")
        parts.append("  Patterns: " + ", ".join(PATTERNS) + ", text:STRING")
        parts.append("  Try:  python3 stereogram.py heart")
        parts.append("        python3 stereogram.py text:HI")
        parts.append("        python3 stereogram.py spiral --seed 1")
        parts.append("        python3 stereogram.py cone --invert")

    output = "\n".join(parts)
    print(output)

    if args.save is not None:
        try:
            with open(args.save, "w", encoding="utf-8") as fh:
                fh.write(output + "\n")
            print(f"\n  [saved to {args.save}]", file=sys.stderr)
        except OSError as exc:
            print(f"Error writing to {args.save}: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))