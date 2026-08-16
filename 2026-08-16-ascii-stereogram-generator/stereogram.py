#!/usr/bin/env python3
"""
ASCII Single-Image Random Dot Stereogram (SIRDS) Generator

Renders depth maps into terminal stereograms using characters as "dots".
Each row is built so that matching character pairs are separated by a
horizontal offset proportional to the depth at that pixel. When the viewer
either crosses their eyes (cross-eyed) or relaxes them (wall-eyed), the
left and right copies fuse and the depth pattern pops out in 3D.

Usage:
    python3 stereogram.py [pattern] [width] [height]

    pattern : sphere | torus | cone | pyramid | wave | steps | heart | text:ABC | random
    width   : character width of the stereogram  (default 72)
    height  : character height of the stereogram  (default 24)
"""

import math
import random
import sys

# Characters ordered from sparse -> dense to give subtle texture variety.
# Using mostly similar-density characters so that the stereogram texture
# itself doesn't give away the shape (it should be hidden in the noise).
RAMP = " .:-=+*#%@"
NOISE_CHARS = ".,:;~=+*o#%@#"  # pool for random texture


# --------------------------------------------------------------------------- #
# Depth-map generators                                                        #
# --------------------------------------------------------------------------- #
# Each returns a 2D list of floats in [0.0, 1.0] where 1.0 = closest to viewer.
# --------------------------------------------------------------------------- #

def _empty(w, h):
    return [[0.0 for _ in range(w)] for _ in range(h)]


def depth_sphere(w, h):
    """A sphere centered in the image."""
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
            d2 = dring * dring + 0  # we treat as flat in z-plane
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
    """A heart shape."""
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


def depth_text(text, w, h):
    """Render text as a depth map using a built-in 5x5 bitmap font."""
    glyphs = _build_font()
    grid = _empty(w, h)
    # Layout the text horizontally, centered.
    total_w = sum(len(glyphs.get(ch.upper(), glyphs.get("?", []))[0]) + 1
                  for ch in text)
    if total_w >= w:
        text = text[: max(1, w // 6)]
        total_w = sum(len(glyphs.get(ch.upper(), glyphs.get("?", []))[0]) + 1
                      for ch in text)
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


def depth_random(w, h):
    """Random blurry blobs — pure fun to practice seeing stereograms."""
    grid = _empty(w, h)
    num_blobs = random.randint(3, 7)
    for _ in range(num_blobs):
        bx = random.uniform(0, w)
        by = random.uniform(0, h)
        br = random.uniform(w * 0.1, w * 0.3)
        peak = random.uniform(0.5, 1.0)
        for y in range(h):
            for x in range(w):
                d = math.sqrt((x - bx) ** 2 + ((y - by) * 2) ** 2)
                if d < br:
                    val = peak * (1 - d / br)
                    if val > grid[y][x]:
                        grid[y][x] = val
    return grid


# --------------------------------------------------------------------------- #
# Minimal 5x5 bitmap font for text stereograms                                #
# --------------------------------------------------------------------------- #
def _build_font():
    """Return a dict mapping uppercase letters & digits to 5-row glyph arrays.
    Each glyph is a list of 5 lists (rows) of 0/1."""
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
    }
    font = {}
    for ch, spec in raw.items():
        rows = [[int(c) for c in row] for row in spec.split("/")]
        font[ch] = rows
    return font


# --------------------------------------------------------------------------- #
# Stereogram renderer                                                         #
# --------------------------------------------------------------------------- #

def render_stereogram(depth, width, height, eye_separation=14, depth_mul=0.33):
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
    """
    lines = []
    for y in range(height):
        row = list(random.choice(NOISE_CHARS) for _ in range(width))

        for x in range(width):
            d = depth[y][x]
            if d <= 0.001:
                continue
            # Desired pixel-separation between the two matching samples.
            sep = int(round(eye_separation - d * eye_separation * depth_mul))
            if sep < 2:
                sep = 2
            left = x - sep
            if left >= 0 and left < width:
                # Copy the character from the left matching position so that
                # when the eyes fuse, both see the same symbol here.
                row[x] = row[left]

        lines.append("".join(row))
    return "\n".join(lines)


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
    "random": depth_random,
}


def make_depth(pattern, w, h):
    if pattern.startswith("text:"):
        return depth_text(pattern[5:], w, h)
    fn = PATTERNS.get(pattern)
    if fn is None:
        raise ValueError(f"Unknown pattern '{pattern}'. "
                         f"Choose from: {', '.join(list(PATTERNS) + ['text:...'])}")
    return fn(w, h)


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


def main(argv):
    pattern = argv[1] if len(argv) > 1 else "sphere"
    width = int(argv[2]) if len(argv) > 2 else 72
    height = int(argv[3]) if len(argv) > 3 else 24

    # Scale eye separation with width for best viewing.
    eye_sep = max(8, min(20, width // 6))

    try:
        depth = make_depth(pattern, width, height)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(f"Available patterns: {', '.join(PATTERNS)}, text:STRING",
              file=sys.stderr)
        return 1

    print(BANNER)
    print(f"  Pattern : {pattern}")
    print(f"  Size    : {width} x {height}")
    print(f"  Eye sep : {eye_sep} chars")
    print()
    print("─" * width)
    print()
    stereogram = render_stereogram(depth, width, height, eye_separation=eye_sep)
    print(stereogram)
    print()
    print("─" * width)
    print()
    print("  ↑ Stare at the block above and let your eyes relax/cross.")
    print("  The hidden 3D shape will emerge from the noise.")
    print()
    print("  Patterns: " + ", ".join(PATTERNS) + ", text:STRING")
    print("  Try:  python3 stereogram.py heart")
    print("        python3 stereogram.py text:HI")
    print("        python3 stereogram.py random 80 28")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))