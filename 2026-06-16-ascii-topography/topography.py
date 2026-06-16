#!/usr/bin/env python3
"""
ASCII Topography Map Generator

Generates realistic-looking ASCII topographic/elevation maps using
Perlin-like noise, with contour lines, elevation markers, terrain
type shading, rivers, lakes, peak labels, elevation profiles,
terrain statistics, coordinate grid overlay, and compass rose.

Usage:
    python3 topography.py                  # random map
    python3 topography.py --seed 42        # fixed seed
    python3 topography.py --width 80 --height 40
    python3 topography.py --interactive    # zoom/pan mode
    python3 topography.py --profile row 15 # elevation profile at row 15
    python3 topography.py --output map.txt # save to file
"""

import argparse
import collections
import hashlib
import math
import os
import random
import sys
import time

__version__ = "1.1.1"


# ─── Perlin-like Noise ───────────────────────────────────────────────────────

class PerlinNoise:
    """2D Perlin-like noise using a permutation table."""

    def __init__(self, seed=0):
        rng = random.Random(seed)
        self.p = list(range(256))
        rng.shuffle(self.p)
        self.p += self.p  # double for overflow

    def _fade(self, t):
        """Quintic fade curve for smooth interpolation."""
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, t, a, b):
        """Linear interpolation between a and b by factor t."""
        return a + t * (b - a)

    def _grad(self, h, x, y):
        """Gradient function mapping hash to 2D gradient vector."""
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
        """Compute 2D Perlin noise value at (x, y)."""
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
        """Multi-octave fractal noise for natural-looking terrain."""
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

# Lake character
LAKE_CHAR = "◊"

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
    "◊": "\033[38;5;39m",   # lake cyan
    "│": "\033[38;5;243m",  # grid line dim
    "─": "\033[38;5;243m",  # grid line dim
    "┼": "\033[38;5;243m",  # grid cross dim
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Compass rose parts for rendering
COMPASS_ROSE = [
    "      N      ",
    "      ▲      ",
    "  NW ╱ ╲ NE  ",
    "    ╱   ╲    ",
    "W ◄  ┼  ► E  ",
    "    ╲   ╱    ",
    "  SW ╲ ╱ SE  ",
    "      ▼      ",
    "      S      ",
]


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

    def __init__(self, width=80, height=30, seed=None, scale=0.04,
                 octaves=6, contour_interval=CONTOUR_INTERVAL):
        if seed is None:
            seed = int(time.time() * 1000) % (2**31)
        if width < 10 or height < 5:
            raise ValueError(f"Map dimensions too small: {width}x{height}. Minimum is 10x5.")
        if width > 500 or height > 200:
            raise ValueError(f"Map dimensions too large: {width}x{height}. Maximum is 500x200.")
        if octaves < 1 or octaves > 12:
            raise ValueError(f"Octaves must be between 1 and 12, got {octaves}.")
        if scale <= 0 or scale > 1:
            raise ValueError(f"Scale must be between 0 (exclusive) and 1 (inclusive), got {scale}.")
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
        self.lake_cells = set()

    def generate(self):
        """Generate elevation data, rivers, lakes, and peak labels."""
        self._generate_elevation()
        self._generate_rivers()
        self._detect_lakes()
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
        # Use more sources for larger maps
        num_sources = max(6, min(16, self.width * self.height // 200))
        sources = []
        for _ in range(num_sources):
            rx = rng.randint(self.width // 6, 5 * self.width // 6)
            ry = rng.randint(self.height // 6, 5 * self.height // 6)
            if self.elevation[ry][rx] > 0.30:
                sources.append((rx, ry))

        for sx, sy in sources:
            x, y = sx, sy
            visited = set()
            for _ in range(300):  # max steps
                if (x, y) in visited:
                    break
                visited.add((x, y))
                self.river_cells.add((x, y))

                # Stop if we hit water
                if self.elevation[y][x] < 0.12:
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
                    # Flat area or local min — might form a lake
                    # Add some randomness to try to continue
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

    def _detect_lakes(self):
        """Detect enclosed low-elevation basins that form lakes."""
        self.lake_cells = set()
        # Find basins: low-elevation areas (< 0.18) that aren't connected
        # to the map edge via shallow water paths

        # BFS from all edge cells that are water — these are ocean-connected
        edge_water = set()
        queue = collections.deque()
        for x in range(self.width):
            for y in [0, self.height - 1]:
                if self.elevation[y][x] < 0.18:
                    edge_water.add((x, y))
                    queue.append((x, y))
        for y in range(self.height):
            for x in [0, self.width - 1]:
                if self.elevation[y][x] < 0.18:
                    if (x, y) not in edge_water:
                        edge_water.add((x, y))
                        queue.append((x, y))

        # BFS to find all ocean-connected water
        connected = set(queue)
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < self.width and 0 <= ny < self.height
                        and (nx, ny) not in connected
                        and self.elevation[ny][nx] < 0.18):
                    connected.add((nx, ny))
                    queue.append((nx, ny))

        # Any water cell NOT connected to the ocean is a lake
        for y in range(self.height):
            for x in range(self.width):
                if self.elevation[y][x] < 0.18 and (x, y) not in connected:
                    self.lake_cells.add((x, y))

    def _find_peaks(self):
        """Find local maxima and assign labels."""
        self.peak_labels = []
        used_names = set()

        # Name generation — expanded list for larger maps
        name_parts_1 = ["Mt.", "Peak", "Mount", "Summit", "Pico", "Crag", "Tor", "Horn",
                         "Mesa", "Butte", "Dome", "Spire"]
        name_parts_2 = ["Eagle", "Storm", "Cloud", "Iron", "Stone", "Wind", "Frost",
                        "Thunder", "Silver", "Gold", "Ash", "Ember", "Raven", "Wolf",
                        "Bear", "Hawk", "Pine", "Cedar", "Oak", "Crystal", "Shadow",
                        "Sunset", "Dawn", "Twilight", "Ancient", "Lost", "High",
                        "Granite", "Jade", "Amber", "Opal", "Onyx", "Flame", "Vale"]

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
        # Scale minimum spacing based on map size
        min_x_spacing = max(8, self.width // 10)
        min_y_spacing = max(4, self.height // 8)
        placed = []
        for px, py, pe in peaks:
            too_close = False
            for qx, qy, _ in placed:
                if abs(px - qx) < min_x_spacing and abs(py - qy) < min_y_spacing:
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
        """Check if this cell is on a contour line (elevation crosses contour interval).

        Uses integer comparison of contour level indices to avoid floating-point
        rounding issues.
        """
        e = self.elevation[y][x]
        contour_idx = round(e / self.contour_interval)

        # Check if any neighbor crosses a different contour level
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                ne = self.elevation[ny][nx]
                n_idx = round(ne / self.contour_interval)
                if n_idx != contour_idx:
                    return True
        return False

    def get_terrain_stats(self):
        """Return a dict of terrain name -> percentage coverage."""
        counts = {}
        total = self.width * self.height
        for y in range(self.height):
            for x in range(self.width):
                _, name = get_terrain(self.elevation[y][x])
                counts[name] = counts.get(name, 0) + 1
        return {name: count / total * 100 for name, count in sorted(counts.items())}

    def get_lake_count(self):
        """Return the number of distinct lakes (connected components of lake cells)."""
        if not self.lake_cells:
            return 0
        visited = set()
        count = 0
        for cell in self.lake_cells:
            if cell in visited:
                continue
            count += 1
            # BFS to mark entire lake
            queue = collections.deque([cell])
            visited.add(cell)
            while queue:
                cx, cy = queue.popleft()
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) in self.lake_cells and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        return count

    def render_profile(self, direction, index, use_color=True):
        """Render an elevation profile along a row or column.

        Args:
            direction: 'row' or 'col'
            index: 0-based row or column index
            use_color: whether to use ANSI colors

        Returns:
            String representation of the elevation profile
        """
        if not self.elevation:
            return "  Error: map has not been generated. Call generate() first."
        if direction == 'row':
            if index < 0 or index >= self.height:
                return f"  Error: row index {index} out of range (0-{self.height-1})"
            elevations = [self.elevation[index][x] for x in range(self.width)]
            label = f"Row {index}"
        elif direction == 'col':
            if index < 0 or index >= self.width:
                return f"  Error: col index {index} out of range (0-{self.width-1})"
            elevations = [self.elevation[y][index] for y in range(self.height)]
            label = f"Col {index}"
        else:
            return f"  Error: direction must be 'row' or 'col', got '{direction}'"

        if not elevations:
            return "  No data"

        lines = []
        max_e = max(elevations)
        min_e = min(elevations)
        profile_height = 12

        lines.append(f"  {BOLD}Elevation Profile — {label}{RESET}")
        lines.append(f"  Min: {int(min_e*4500)}m  Max: {int(max_e*4500)}m")
        lines.append("")

        # Build profile from top to bottom
        for row in range(profile_height, -1, -1):
            threshold = min_e + (max_e - min_e) * (row / profile_height)
            threshold_m = int(threshold * 4500)
            line_str = f"  {threshold_m:>5}m │"
            for e in elevations:
                if e >= threshold:
                    ch = "█"
                    if use_color:
                        # Color based on terrain
                        tchar, _ = get_terrain(e)
                        color = ANSI_COLORS.get(tchar, "")
                        line_str += f"{color}{ch}{RESET}"
                    else:
                        line_str += ch
                else:
                    line_str += " "
            lines.append(line_str)

        # Bottom axis
        lines.append(f"  {'':>6} └{'─' * len(elevations)}")
        if direction == 'row':
            max_idx = len(elevations) - 1
            # Build axis label with 0 on left and max index on right
            label_inner = str(max_idx)
            total_len = len(elevations)
            left = '0'
            right = label_inner
            spacing = total_len - len(left) - len(right)
            if spacing < 1:
                spacing = 1
            axis_label = left + ' ' * spacing + right
            lines.append(f"  {'':>6}  {axis_label}")
        else:
            lines.append(f"  {'':>6}  col index 0 → {len(elevations)-1}")

        return "\n".join(lines)

    def render(self, use_color=True, show_contours=True, show_rivers=True,
               show_labels=True, show_legend=True, show_grid=False,
               show_compass=True, show_stats=True):
        """Render the map as a string."""
        if not self.elevation:
            raise RuntimeError("Cannot render: map has not been generated. Call generate() first.")
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

        # Determine grid spacing
        grid_spacing_x = max(10, self.width // 8)
        grid_spacing_y = max(5, self.height // 6)

        for y in range(self.height):
            row_str = "  ║"
            for x in range(self.width):
                e = self.elevation[y][x]

                # Grid overlay
                if show_grid and (x, y) not in label_map:
                    grid_char = None
                    if x > 0 and x < self.width - 1 and x % grid_spacing_x == 0:
                        if y > 0 and y < self.height - 1 and y % grid_spacing_y == 0:
                            grid_char = "┼"
                        elif y > 0 and y < self.height - 1:
                            grid_char = "│"
                    if grid_char is None and y > 0 and y < self.height - 1 and y % grid_spacing_y == 0:
                        if x > 0 and x < self.width - 1:
                            grid_char = "─"
                    if grid_char is not None:
                        if use_color:
                            row_str += f"{ANSI_COLORS.get(grid_char, '')}{grid_char}{RESET}"
                        else:
                            row_str += grid_char
                        continue

                # Check for label
                if (x, y) in label_map:
                    ch = "▲"
                    if use_color:
                        row_str += f"\033[38;5;196m{ch}{RESET}"
                    else:
                        row_str += ch
                    continue

                # Lake
                if (x, y) in self.lake_cells:
                    ch = LAKE_CHAR
                    if use_color:
                        row_str += f"{ANSI_COLORS[ch]}{ch}{RESET}"
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

        # Compass rose (multi-line block)
        if show_compass and self.width >= 40:
            lines.append("")
            for line in COMPASS_ROSE:
                if use_color:
                    lines.append(f"  {DIM}{line}{RESET}")
                else:
                    lines.append(f"  {line}")

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
            lake_str = LAKE_CHAR if not use_color else ANSI_COLORS[LAKE_CHAR] + LAKE_CHAR + RESET
            lines.append(f"  {lake_str} lakes")
            if show_labels:
                peak_str = '▲' if not use_color else '\033[38;5;196m▲\033[0m'
                lines.append(f"  {peak_str} peaks")
            if show_grid:
                grid_str = '┼' if not use_color else ANSI_COLORS['┼'] + '┼│─' + RESET
                lines.append(f"  {grid_str} coordinate grid")

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
        if show_stats:
            elevations = [self.elevation[y][x] for y in range(self.height) for x in range(self.width)]
            min_e = min(elevations)
            max_e = max(elevations)
            avg_e = sum(elevations) / len(elevations)
            water_pct = sum(1 for e in elevations if e < 0.18) / len(elevations) * 100
            land_pct = 100 - water_pct
            lake_count = self.get_lake_count()
            lines.append("")
            lines.append(f"  Area: {self.width}×{self.height}  |  "
                          f"Elev: {int(min_e*4500)}m–{int(max_e*4500)}m  |  "
                          f"Avg: {int(avg_e*4500)}m  |  "
                          f"Water: {water_pct:.0f}%  |  Land: {land_pct:.0f}%")
            if self.lake_cells:
                lines.append(f"  Lakes: {lake_count}  |  "
                              f"River cells: {len(self.river_cells)}  |  "
                              f"Lake cells: {len(self.lake_cells)}")

            # Terrain composition
            stats = self.get_terrain_stats()
            comp_parts = []
            for name, pct in stats.items():
                if pct > 0.5:
                    comp_parts.append(f"{name} {pct:.0f}%")
            if comp_parts:
                lines.append(f"  Terrain: {', '.join(comp_parts)}")

        return "\n".join(lines)

    def render_elevation_numbers(self):
        """Render a compact view showing elevation numbers (for debugging/detail)."""
        if not self.elevation:
            raise RuntimeError("Cannot render: map has not been generated. Call generate() first.")
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

def interactive_mode(seed=None, octaves=6):
    """Interactive mode with zoom/pan controls.

    Args:
        seed: Random seed (None for random)
        octaves: Number of noise octaves (default: 6)
    """
    import tty
    import termios

    print(f"{BOLD}ASCII Topography Map — Interactive Mode{RESET}")
    print("Controls: +/- zoom | WASD/arrows pan | r regenerate | g grid | q quit")
    print()

    if seed is None:
        seed = int(time.time() * 1000) % (2**31)
    offset_x = 0.0
    offset_y = 0.0
    zoom = 1.0
    show_grid = False
    try:
        term_w = os.get_terminal_size().columns - 4
        term_h = os.get_terminal_size().lines - 6
    except OSError:
        term_w = 80
        term_h = 30
    width = min(80, term_w)
    height = min(30, term_h)

    def render_frame():
        tmap = TopographyMap(width, height, seed=seed, scale=0.04 / zoom,
                             octaves=octaves)
        # Apply offset by shifting the noise sampling
        base_noise = PerlinNoise(seed)
        tmap.noise = base_noise
        tmap.elevation = []
        mask_noise = PerlinNoise(seed + 9999)

        for y in range(height):
            row = []
            for x in range(width):
                nx = (x * tmap.scale) + offset_x
                ny = (y * tmap.scale) + offset_y
                e = (base_noise.octave_noise(nx, ny, octaves) + 1) / 2.0

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
        tmap._detect_lakes()
        tmap._find_peaks()
        return tmap

    tmap = render_frame()

    # Initial render
    print(f"\033[2J\033[H")  # clear screen
    output = tmap.render(show_legend=False, show_grid=show_grid)
    print(output)
    print(f"\n{DIM}+/-: zoom | WASD: pan | r: new map | g: grid | q: quit | zoom={zoom:.1f}x{RESET}")

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
            elif ch == 'g':
                show_grid = not show_grid
            else:
                continue

            tmap = render_frame()
            print(f"\033[2J\033[H]")
            output = tmap.render(show_legend=False, show_grid=show_grid)
            print(output)
            print(f"\n{DIM}+/-: zoom | WASD: pan | r: new map | g: grid | q: quit | zoom={zoom:.1f}x{RESET}")

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    print("\nGoodbye!")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ASCII Topography Map Generator — generate beautiful terrain maps in your terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python3 topography.py                          # random map
  python3 topography.py --seed 42                 # reproducible map
  python3 topography.py --width 100 --height 40   # custom size
  python3 topography.py --no-color                # monochrome
  python3 topography.py --profile row 15          # elevation profile at row 15
  python3 topography.py --profile col 40          # elevation profile at col 40
  python3 topography.py --grid                    # show coordinate grid
  python3 topography.py --no-compass              # hide compass rose
  python3 topography.py --output map.txt          # save to file
  python3 topography.py -i                       # interactive zoom/pan mode
""")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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
    parser.add_argument("--no-compass", action="store_true",
                        help="Hide compass rose")
    parser.add_argument("--no-stats", action="store_true",
                        help="Hide terrain statistics")
    parser.add_argument("--elevation-numbers", action="store_true",
                        help="Show raw elevation numbers (0-9) instead of terrain chars")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Interactive mode with zoom/pan (requires terminal)")
    parser.add_argument("--octaves", type=int, default=6,
                        help="Number of noise octaves (default: 6)")
    parser.add_argument("--grid", action="store_true",
                        help="Show coordinate grid overlay")
    parser.add_argument("--profile", nargs=2, metavar=("DIRECTION", "INDEX"),
                        help="Render elevation profile: 'row N' or 'col N'")
    parser.add_argument("--output", type=str, default=None, metavar="FILE",
                        help="Save output to file instead of stdout")

    args = parser.parse_args()

    # Validate profile arguments
    if args.profile:
        direction = args.profile[0].lower()
        if direction not in ('row', 'col'):
            parser.error(f"Profile direction must be 'row' or 'col', got '{direction}'")
        try:
            profile_index = int(args.profile[1])
        except ValueError:
            parser.error(f"Profile index must be an integer, got '{args.profile[1]}'")

    if args.interactive:
        interactive_mode(seed=args.seed, octaves=args.octaves)
        return

    tmap = TopographyMap(
        width=args.width,
        height=args.height,
        seed=args.seed,
        scale=args.scale,
        octaves=args.octaves,
    )
    tmap.generate()

    if args.profile:
        output = tmap.render_profile(
            direction=args.profile[0].lower(),
            index=int(args.profile[1]),
            use_color=not args.no_color,
        )
    elif args.elevation_numbers:
        output = tmap.render_elevation_numbers()
    else:
        output = tmap.render(
            use_color=not args.no_color,
            show_contours=not args.no_contours,
            show_rivers=not args.no_rivers,
            show_labels=not args.no_labels,
            show_legend=not args.no_legend,
            show_grid=args.grid,
            show_compass=not args.no_compass,
            show_stats=not args.no_stats,
        )

    if args.output:
        # Warn if file already exists
        if os.path.exists(args.output):
            print(f"Warning: file '{args.output}' already exists and will be overwritten.", file=sys.stderr)
        # Strip ANSI codes for file output
        import re
        clean_output = re.sub(r'\033\[[0-9;]*m', '', output)
        with open(args.output, 'w') as f:
            f.write(clean_output)
            f.write("\n")
        print(f"Map saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()