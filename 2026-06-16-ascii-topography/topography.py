#!/usr/bin/env python3
"""
ASCII Topography Map Generator

Generates realistic-looking ASCII topographic/elevation maps using
Perlin-like noise, with contour lines, elevation markers, terrain
type shading, rivers, and peak labels.

Usage:
    python3 topography.py                  # random map
    python3 topography.py --seed 42        # fixed seed
    python3 topography.py --width 80 --height 40
    python3 topography.py --interactive    # zoom/pan mode
"""

import argparse
import hashlib
import math
import os
import random
import sys
import time


# ─── Perlin-like Noise ───────────────────────────────────────────────────────

class PerlinNoise:
    """2D Perlin-like noise using a permutation table."""

    def __init__(self, seed=0):
        rng = random.Random(seed)
        self.p = list(range(256))
        rng.shuffle(self.p)
        self.p += self.p  # double for overflow

    def _fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, t, a, b):
        return a + t * (b - a)

    def _grad(self, h, x, y):
        h = h & 3
        if h == 0:
            return x + y
        elif h == 1:
            return -x + y
        elif h == 2:
            return x - y
        else:
            return -x - y

    def noise2d(self, x, y):
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255
        x -= math.floor(x)
        y -= math.floor(y)
        u = self._fade(x)
        v = self._fade(y)

        A = self.p[X] + Y
        B = self.p[X + 1] + Y

        return self._lerp(v,
            self._lerp(u, self._grad(self.p[A], x, y),
                          self._grad(self.p[B], x - 1, y)),
            self._lerp(u, self._grad(self.p[A + 1], x, y - 1),
                          self._grad(self.p[B + 1], x - 1, y - 1)))

    def octave_noise(self, x, y, octaves=6, persistence=0.5, lacunarity=2.0):
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_val = 0.0
        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_val += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        return total / max_val if max_val > 0 else 0


# ─── Elevation & Terrain ────────────────────────────────────────────────────

# Terrain types with their display characters and the elevation range (0-1)
TERRAIN = [
    (0.00, "≈", "deep water",    (0, 0, 180)),
    (0.12, "~", "shallow water", (30, 100, 200)),
    (0.18, ".", "beach",         (194, 178, 128)),
    (0.22, ",", "plains",        (120, 180, 60)),
    (0.35, ";", "forest",        (40, 120, 40)),
    (0.50, "+", "highland",      (100, 140, 60)),
    (0.60, "/", "mountain",     (130, 110, 90)),
    (0.72, "^", "peak",          (160, 150, 140)),
    (0.85, "#", "snow",          (220, 220, 230)),
]

CONTOUR_INTERVAL = 0.05  # contour line every 5% elevation

# Contour line character (drawn over terrain)
CONTOUR_CHAR = "░"

# Color codes (ANSI 256-color approximations)
ANSI_COLORS = {
    "≈": "\033[38;5;17m",    # deep blue
    "~": "\033[38;5;27m",    # medium blue
    ".": "\033[38;5;186m",  # sandy
    ",": "\033[38;5;82m",   # bright green
    ";": "\033[38;5;22m",   # dark green
    "+": "\033[38;5;100m",  # olive
    "/": "\033[38;5;137m",  # brown
    "^": "\033[38;5;145m",  # gray
    "#": "\033[38;5;255m",  # white-ish
    "░": "\033[38;5;240m",  # dark gray contour
    "▼": "\033[38;5;27m",   # river blue
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def get_terrain(elevation):
    """Return terrain char and name for a given elevation (0-1)."""
    for threshold, char, name, _ in reversed(TERRAIN):
        if elevation >= threshold:
            return char, name
    return TERRAIN[0][1], TERRAIN[0][2]


def get_terrain_index(elevation):
    """Return index into TERRAIN for the given elevation."""
    for i, (threshold, _, _, _) in enumerate(TERRAIN):
        if elevation < threshold:
            return max(0, i - 1)
    return len(TERRAIN) - 1


# ─── Map Generation ─────────────────────────────────────────────────────────

class TopographyMap:
    """Generates and renders an ASCII topographic map."""

    def __init__(self, width=80, height=35, seed=None, scale=0.04,
                 octaves=6, contour_interval=CONTOUR_INTERVAL):
        if seed is None:
            seed = int(time.time() * 1000) % (2**31)
        self.seed = seed
        self.width = width
        self.height = height
        self.scale = scale
        self.octaves = octaves
        self.contour_interval = contour_interval
        self.noise = PerlinNoise(seed)
        self.elevation = []
        self.peak_labels = []
        self.river_cells = set()

    def generate(self):
        """Generate elevation data, rivers, and peak labels."""
        self._generate_elevation()
        self._generate_rivers()
        self._find_peaks()
        return self

    def _generate_elevation(self):
        """Generate elevation grid using multi-octave Perlin noise."""
        # Use secondary noise for island mask (prefer higher in center)
        mask_noise = PerlinNoise(self.seed + 9999)
        self.elevation = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                # Base terrain
                nx = x * self.scale
                ny = y * self.scale
                e = (self.noise.octave_noise(nx, ny, self.octaves) + 1) / 2.0

                # Island mask: lower edges to create natural coastline
                cx = (x / self.width - 0.5) * 2
                cy = (y / self.height - 0.5) * 2
                dist = math.sqrt(cx * cx + cy * cy)
                mask = 1.0 - max(0, min(1, (dist - 0.7) * 2.0))
                mask = mask * mask

                # Secondary warp for more interesting coastlines
                warp = (mask_noise.octave_noise(nx * 2, ny * 2, 3) + 1) / 2.0
                mask = mask * (0.7 + 0.3 * warp)

                e = e * mask

                # Power curve to enhance peaks and valleys
                e = e ** 0.8

                # Boost: remap so the highest point approaches 1.0
                e = e * 1.2

                e = max(0.0, min(1.0, e))
                row.append(e)
            self.elevation.append(row)

    def _generate_rivers(self):
        """Trace rivers from high elevations downhill to water."""
        rng = random.Random(self.seed + 7777)
        self.river_cells = set()

        # Find river sources (high elevation random points)
        sources = []
        for _ in range(8):
            rx = rng.randint(self.width // 6, 5 * self.width // 6)
            ry = rng.randint(self.height // 6, 5 * self.height // 6)
            if self.elevation[ry][rx] > 0.30:
                sources.append((rx, ry))

        for sx, sy in sources:
            x, y = sx, sy
            visited = set()
            for _ in range(200):  # max steps
                if (x, y) in visited:
                    break
                visited.add((x, y))
                self.river_cells.add((x, y))

                # Stop if we hit water
                if self.elevation[y][x] < 0.15:
                    break

                # Flow downhill: find lowest neighbor
                best = (x, y)
                best_e = self.elevation[y][x]
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                                (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        ne = self.elevation[ny][nx]
                        if ne < best_e:
                            best_e = ne
                            best = (nx, ny)
                if best == (x, y):
                    # Flat area or local min — add some randomness
                    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    rng.shuffle(dirs)
                    moved = False
                    for dx, dy in dirs:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            x, y = nx, ny
                            moved = True
                            break
                    if not moved:
                        break
                else:
                    x, y = best

    def _find_peaks(self):
        """Find local maxima and assign labels."""
        self.peak_labels = []
        used_names = set()

        # Name generation
        name_parts_1 = ["Mt.", "Peak", "Mount", "Summit", "Pico", "Crag", "Tor", "Horn"]
        name_parts_2 = ["Eagle", "Storm", "Cloud", "Iron", "Stone", "Wind", "Frost",
                        "Thunder", "Silver", "Gold", "Ash", "Ember", "Raven", "Wolf",
                        "Bear", "Hawk", "Pine", "Cedar", "Oak", "Crystal", "Shadow",
                        "Sunset", "Dawn", "Twilight", "Ancient", "Lost", "High"]

        rng = random.Random(self.seed + 3333)
        peaks = []

        for y in range(2, self.height - 2):
            for x in range(2, self.width - 2):
                e = self.elevation[y][x]
                if e < 0.60:
                    continue
                # Check if local maximum in 5x5 neighborhood
                is_max = True
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            if self.elevation[ny][nx] > e:
                                is_max = False
                                break
                    if not is_max:
                        break
                if is_max:
                    peaks.append((x, y, e))

        # Sort by elevation (highest first), take top peaks with spacing
        peaks.sort(key=lambda p: -p[2])
        placed = []
        for px, py, pe in peaks:
            too_close = False
            for qx, qy, _ in placed:
                if abs(px - qx) < 10 and abs(py - qy) < 5:
                    too_close = True
                    break
            if too_close:
                continue
            # Generate name
            while True:
                p1 = rng.choice(name_parts_1)
                p2 = rng.choice(name_parts_2)
                name = f"{p1} {p2}"
                if name not in used_names:
                    used_names.add(name)
                    break
            elev_m = int(pe * 4500)  # scale to ~4500m max
            placed.append((px, py, pe))
            self.peak_labels.append((px, py, name, elev_m))

    def is_contour(self, x, y):
        """Check if this cell is on a contour line (elevation crosses contour interval)."""
        e = self.elevation[y][x]
        contour_level = round(e / self.contour_interval) * self.contour_interval

        # Check if any neighbor crosses a different contour level
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                ne = self.elevation[ny][nx]
                n_contour = round(ne / self.contour_interval) * self.contour_interval
                if n_contour != contour_level:
                    return True
        return False

    def render(self, use_color=True, show_contours=True, show_rivers=True,
               show_labels=True, show_legend=True):
        """Render the map as a string."""
        lines = []

        # Header
        header = f"  Topographic Map — Seed {self.seed}"
        border = "─" * (self.width + 2)
        if use_color:
            lines.append(f"{BOLD}{header}{RESET}")
        else:
            lines.append(header)
        lines.append(f"  ╔{border}╗")

        # Map rows
        label_map = {}  # (x, y) -> label text
        if show_labels:
            for px, py, name, elev_m in self.peak_labels:
                label_map[(px, py)] = name

        for y in range(self.height):
            row_str = "  ║"
            for x in range(self.width):
                e = self.elevation[y][x]

                # Check for label
                if (x, y) in label_map:
                    ch = "▲"
                    if use_color:
                        row_str += f"\033[38;5;196m{ch}{RESET}"
                    else:
                        row_str += ch
                    continue

                # River
                if show_rivers and (x, y) in self.river_cells:
                    ch = "▼"
                    if use_color:
                        row_str += f"{ANSI_COLORS['▼']}{ch}{RESET}"
                    else:
                        row_str += ch
                    continue

                # Contour lines
                if show_contours and self.is_contour(x, y) and e >= 0.22:
                    ch = CONTOUR_CHAR
                    if use_color:
                        row_str += f"{ANSI_COLORS[ch]}{ch}{RESET}"
                    else:
                        row_str += ch
                    continue

                # Terrain
                tchar, tname = get_terrain(e)
                if use_color:
                    row_str += f"{ANSI_COLORS.get(tchar, '')}{tchar}{RESET}"
                else:
                    row_str += tchar

            row_str += "║"
            lines.append(row_str)

        lines.append(f"  ╚{border}╝")

        # Legend
        if show_legend:
            lines.append("")
            if use_color:
                lines.append(f"  {BOLD}Legend:{RESET}")
            else:
                lines.append("  Legend:")
            legend_parts = []
            for threshold, char, name, _ in TERRAIN:
                elev_pct = int(threshold * 100)
                if use_color:
                    legend_parts.append(f"{ANSI_COLORS.get(char, '')}{char}{RESET} {name} ({elev_pct}%+)")
                else:
                    legend_parts.append(f"{char} {name} ({elev_pct}%+)")
            # Print legend in rows of ~3
            for i in range(0, len(legend_parts), 3):
                line = "  " + "  ".join(legend_parts[i:i+3])
                lines.append(line)

            if show_contours:
                contour_ch = CONTOUR_CHAR
                if use_color:
                    lines.append(f"  {ANSI_COLORS[contour_ch]}{contour_ch}{RESET} contour lines (every {int(self.contour_interval*100)}%)")
                else:
                    lines.append(f"  {contour_ch} contour lines (every {int(self.contour_interval*100)}%)")
            if show_rivers:
                river_str = '▼' if not use_color else ANSI_COLORS['▼'] + '▼' + RESET
                lines.append(f"  {river_str} rivers")
            if show_labels:
                peak_str = '▲' if not use_color else '\033[38;5;196m▲\033[0m'
                lines.append(f"  {peak_str} peaks")

        # Peak labels
        if show_labels and self.peak_labels:
            lines.append("")
            if use_color:
                lines.append(f"  {BOLD}Peaks:{RESET}")
            else:
                lines.append("  Peaks:")
            for px, py, name, elev_m in sorted(self.peak_labels, key=lambda p: -p[3]):
                lines.append(f"    ▲ {name} — {elev_m}m  (col {px+1}, row {py+1})")

        # Stats
        elevations = [self.elevation[y][x] for y in range(self.height) for x in range(self.width)]
        min_e = min(elevations)
        max_e = max(elevations)
        avg_e = sum(elevations) / len(elevations)
        water_pct = sum(1 for e in elevations if e < 0.22) / len(elevations) * 100
        lines.append("")
        lines.append(f"  Area: {self.width}×{self.height}  |  "
                      f"Elev: {int(min_e*4500)}m–{int(max_e*4500)}m  |  "
                      f"Avg: {int(avg_e*4500)}m  |  "
                      f"Water: {water_pct:.0f}%")

        return "\n".join(lines)

    def render_elevation_numbers(self):
        """Render a compact view showing elevation numbers (for debugging/detail)."""
        lines = []
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                e = self.elevation[y][x]
                val = int(e * 9)
                row += str(val)
            lines.append(row)
        return "\n".join(lines)


# ─── Interactive Mode ───────────────────────────────────────────────────────

def interactive_mode():
    """Interactive mode with zoom/pan controls."""
    import tty
    import termios

    print(f"{BOLD}ASCII Topography Map — Interactive Mode{RESET}")
    print("Controls: +/- zoom | WASD/arrows pan | r regenerate | q quit")
    print()

    seed = int(time.time() * 1000) % (2**31)
    offset_x = 0.0
    offset_y = 0.0
    zoom = 1.0
    width = min(80, os.get_terminal_size().columns - 4)
    height = min(30, os.get_terminal_size().lines - 6)

    def render_frame():
        tmap = TopographyMap(width, height, seed=seed, scale=0.04 / zoom)
        # Apply offset by shifting the noise sampling
        # We create a new noise with offset baked in via the seed permutation
        base_noise = PerlinNoise(seed)
        tmap.noise = base_noise
        tmap.elevation = []
        mask_noise = PerlinNoise(seed + 9999)

        for y in range(height):
            row = []
            for x in range(width):
                nx = (x * tmap.scale) + offset_x
                ny = (y * tmap.scale) + offset_y
                e = (base_noise.octave_noise(nx, ny, 6) + 1) / 2.0

                cx = ((x + offset_x / tmap.scale) / width - 0.5) * 2
                cy = ((y + offset_y / tmap.scale) / height - 0.5) * 2
                dist = math.sqrt(cx * cx + cy * cy)
                mask = 1.0 - max(0, min(1, (dist - 0.7) * 2.0))
                mask = mask * mask

                warp = (mask_noise.octave_noise(nx * 2, ny * 2, 3) + 1) / 2.0
                mask = mask * (0.7 + 0.3 * warp)

                e = e * mask

                # Power curve to enhance peaks and valleys
                e = e ** 0.8

                # Boost: remap so the highest point approaches 1.0
                e = e * 1.2

                e = max(0.0, min(1.0, e))
                row.append(e)
            tmap.elevation.append(row)

        tmap._generate_rivers()
        tmap._find_peaks()
        return tmap

    tmap = render_frame()

    # Initial render
    print(f"\033[2J\033[H")  # clear screen
    output = tmap.render(show_legend=False)
    print(output)
    print(f"\n{DIM}+/-: zoom | WASD: pan | r: new map | q: quit | zoom={zoom:.1f}x{RESET}")

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == 'q':
                break
            elif ch == '+' or ch == '=':
                zoom = min(8.0, zoom * 1.3)
            elif ch == '-' or ch == '_':
                zoom = max(0.2, zoom / 1.3)
            elif ch == 'w' or ch == '\x1b[A':  # up
                offset_y -= 2.0 / zoom
            elif ch == 's' or ch == '\x1b[B':  # down
                offset_y += 2.0 / zoom
            elif ch == 'a' or ch == '\x1b[D':  # left
                offset_x -= 2.0 / zoom
            elif ch == 'd' or ch == '\x1b[C':  # right
                offset_x += 2.0 / zoom
            elif ch == 'r':
                seed = int(time.time() * 1000) % (2**31)
                offset_x = 0
                offset_y = 0
                zoom = 1.0
            else:
                continue

            tmap = render_frame()
            print(f"\033[2J\033[H")
            output = tmap.render(show_legend=False)
            print(output)
            print(f"\n{DIM}+/-: zoom | WASD: pan | r: new map | q: quit | zoom={zoom:.1f}x{RESET}")

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    print("\nGoodbye!")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ASCII Topography Map Generator — generate beautiful terrain maps in your terminal")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible maps")
    parser.add_argument("--width", type=int, default=80,
                        help="Map width in characters (default: 80)")
    parser.add_argument("--height", type=int, default=30,
                        help="Map height in characters (default: 30)")
    parser.add_argument("--scale", type=float, default=0.04,
                        help="Noise scale factor — lower = more zoomed out (default: 0.04)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    parser.add_argument("--no-contours", action="store_true",
                        help="Hide contour lines")
    parser.add_argument("--no-rivers", action="store_true",
                        help="Hide rivers")
    parser.add_argument("--no-labels", action="store_true",
                        help="Hide peak labels")
    parser.add_argument("--no-legend", action="store_true",
                        help="Hide legend")
    parser.add_argument("--elevation-numbers", action="store_true",
                        help="Show raw elevation numbers (0-9) instead of terrain chars")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Interactive mode with zoom/pan (requires terminal)")
    parser.add_argument("--octaves", type=int, default=6,
                        help="Number of noise octaves (default: 6)")

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
        return

    tmap = TopographyMap(
        width=args.width,
        height=args.height,
        seed=args.seed,
        scale=args.scale,
        octaves=args.octaves,
    )
    tmap.generate()

    if args.elevation_numbers:
        print(tmap.render_elevation_numbers())
    else:
        print(tmap.render(
            use_color=not args.no_color,
            show_contours=not args.no_contours,
            show_rivers=not args.no_rivers,
            show_labels=not args.no_labels,
            show_legend=not args.no_legend,
        ))


if __name__ == "__main__":
    main()