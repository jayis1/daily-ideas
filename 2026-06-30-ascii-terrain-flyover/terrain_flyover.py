#!/usr/bin/env python3
"""
ASCII Terrain Flyover — Procedural terrain rendered as a first-person
flyover animation in the terminal.

Uses Perlin-like noise for terrain generation, a height-based color map,
and a simple ray-marching approach to render perspective terrain columns.

Supports interactive keyboard controls, day/night cycles, water animation,
minimap overlays, and screenshot export.
"""

__version__ = "1.1.1"

import os
import sys
import time
import math
import random
import argparse
import select
import tty
import termios
from typing import Optional, Tuple, List

# ── ANSI helpers ──────────────────────────────────────────────────────

ESC = "\033["
RESET = f"{ESC}0m"
CLEAR = f"{ESC}2J{ESC}H"
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"

# 256-color palette indices for terrain
DEEP_WATER = 17
SHALLOW_WATER = 25
SAND = 180
GRASS = 34
DARK_GRASS = 28
FOREST = 22
MOUNTAIN = 95
SNOW = 255
SKY_TOP = 18
SKY_BOTTOM = 111
FOG = 244
SUN_COLOR = 220
CLOUD_COLOR = 252

# Day/night sky palettes (top, mid, bottom, sun, fog)
SKY_DAY = (18, 39, 111, 220, 244)
SKY_SUNSET = (52, 131, 173, 208, 244)
SKY_NIGHT = (16, 17, 19, 184, 236)

# Water animation characters
WAVE_CHARS = "~≈∽∿"


# ── Noise generation (simple Perlin-like) ────────────────────────────

class PerlinNoise:
    """Simple 2D Perlin noise implementation."""

    def __init__(self, seed: Optional[int] = None):
        rng = random.Random(seed)
        self.perm: List[int] = list(range(256))
        rng.shuffle(self.perm)
        self.perm = self.perm + self.perm  # double for wrapping
        self.gradients: List[Tuple[float, float]] = [
            (math.cos(2 * math.pi * i / 256), math.sin(2 * math.pi * i / 256))
            for i in range(256)
        ]

    @staticmethod
    def _fade(t: float) -> float:
        """Quintic fade curve for smooth interpolation."""
        return t * t * t * (t * (t * 6 - 15) + 10)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        """Linear interpolation between a and b by factor t."""
        return a + t * (b - a)

    def _grad(self, h: int, x: float, y: float) -> float:
        """Gradient dot product for Perlin noise."""
        g = self.gradients[h & 255]
        return g[0] * x + g[1] * y

    def noise(self, x: float, y: float) -> float:
        """Evaluate 2D Perlin noise at (x, y). Returns ~[-0.5, 0.5]."""
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = self._fade(xf)
        v = self._fade(yf)

        aa = self.perm[self.perm[xi] + yi]
        ab = self.perm[self.perm[xi] + yi + 1]
        ba = self.perm[self.perm[xi + 1] + yi]
        bb = self.perm[self.perm[xi + 1] + yi + 1]

        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1, yf), u)
        x2 = self._lerp(self._grad(ab, xf, yf - 1), self._grad(bb, xf - 1, yf - 1), u)

        return self._lerp(x1, x2, v)

    def octave_noise(self, x: float, y: float, octaves: int = 6,
                     persistence: float = 0.5, lacunarity: float = 2.0) -> float:
        """Multi-octave fractal noise for richer terrain detail."""
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_val = 0.0
        for _ in range(octaves):
            total += self.noise(x * frequency, y * frequency) * amplitude
            max_val += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        return total / max_val


# ── Color utilities ───────────────────────────────────────────────────

# Extended RGB lookup for 256-color palette blending
_RGB_MAP = {
    17: (0, 0, 95), 25: (0, 95, 175), 180: (175, 135, 95),
    34: (0, 175, 0), 28: (0, 135, 0), 22: (0, 95, 0),
    95: (135, 95, 95), 255: (255, 255, 255), 18: (0, 0, 95),
    111: (135, 175, 215), 244: (180, 180, 180), 220: (255, 215, 0),
    252: (230, 230, 230), 236: (70, 70, 70), 240: (140, 140, 140),
    59: (95, 95, 135), 60: (95, 95, 175), 67: (95, 135, 175),
    74: (95, 175, 215), 117: (135, 175, 255),
    # Sunset/night palette entries
    16: (0, 0, 0), 19: (0, 0, 135), 52: (95, 0, 0),
    131: (215, 95, 0), 173: (215, 135, 95), 184: (215, 215, 0),
    208: (255, 135, 0), 189: (215, 215, 215),
    # Additional terrain colors
    39: (0, 95, 215), 232: (18, 18, 18),
}


def _rgb_to_256(r: int, g: int, b: int) -> int:
    """Find nearest 256-color index for an RGB value using the 6x6x6 color cube."""
    r_idx = min(5, max(0, round(r / 51)))
    g_idx = min(5, max(0, round(g / 51)))
    b_idx = min(5, max(0, round(b / 51)))
    return 16 + 36 * r_idx + 6 * g_idx + b_idx


def _blend_256(c1: int, c2: int, t: float) -> int:
    """Blend two 256-color palette indices by factor t (0=c1, 1=c2)."""
    t = max(0.0, min(1.0, t))
    if t == 0.0:
        return c1
    if t == 1.0:
        return c2
    r1, g1, b1 = _RGB_MAP.get(c1, (128, 128, 128))
    r2, g2, b2 = _RGB_MAP.get(c2, (128, 128, 128))
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return _rgb_to_256(r, g, b)


# ── Time-of-day sky interpolation ────────────────────────────────────

def _lerp_palette(day: Tuple, sunset: Tuple, night: Tuple, hour: float) -> Tuple:
    """Interpolate between three sky palettes based on hour of day (0-24).

    Returns (sky_top, sky_mid, sky_bottom, sun, fog) color indices.
    """
    if 6 <= hour < 8:
        # Dawn: night → sunset
        t = (hour - 6) / 2.0
        return tuple(_blend_256(n, s, t) for n, s in zip(night, sunset))
    elif 8 <= hour < 10:
        # Morning: sunset → day
        t = (hour - 8) / 2.0
        return tuple(_blend_256(s, d, t) for s, d in zip(sunset, day))
    elif 10 <= hour < 17:
        # Full day
        return day
    elif 17 <= hour < 19:
        # Evening: day → sunset
        t = (hour - 17) / 2.0
        return tuple(_blend_256(d, s, t) for d, s in zip(day, sunset))
    elif 19 <= hour < 21:
        # Dusk: sunset → night
        t = (hour - 19) / 2.0
        return tuple(_blend_256(s, n, t) for s, n in zip(sunset, night))
    else:
        # Night
        return night


# ── Terrain ───────────────────────────────────────────────────────────

def height_to_color(h: float, fog_factor: float = 0.0, hour: float = 12.0) -> int:
    """Map a height value (0-1) to an ANSI 256-color index with fog and time-of-day tint."""
    if h < 0.28:
        c = DEEP_WATER
    elif h < 0.35:
        c = SHALLOW_WATER
    elif h < 0.38:
        c = SAND
    elif h < 0.50:
        c = GRASS
    elif h < 0.60:
        c = DARK_GRASS
    elif h < 0.72:
        c = FOREST
    elif h < 0.82:
        c = MOUNTAIN
    else:
        c = SNOW

    # Night darkening: blend terrain toward dark blue/gray at night
    if hour < 6 or hour > 21:
        c = _blend_256(c, 16, 0.5)   # dark overlay at night
    elif 6 <= hour < 8:
        c = _blend_256(c, 16, 0.5 * (1 - (hour - 6) / 2.0))
    elif 19 <= hour < 21:
        c = _blend_256(c, 16, 0.5 * ((hour - 19) / 2.0))

    # Blend with fog color for distance
    if fog_factor > 0:
        fog_color = 236 if (hour < 6 or hour > 20) else FOG
        c = _blend_256(c, fog_color, fog_factor)
    return c


def height_to_char(h: float, dist: float, max_dist: float, frame: int = 0) -> str:
    """Map height and distance to an ASCII character with water animation."""
    if h < 0.28:
        # Animated water characters
        idx = (frame // 4 + int(dist)) % len(WAVE_CHARS)
        return WAVE_CHARS[idx]
    elif h < 0.35:
        chars = "≈∽∿"
    elif h < 0.40:
        chars = ".,·"
    elif h < 0.55:
        chars = "v\"|"
    elif h < 0.72:
        chars = "♠♣¶"
    elif h < 0.82:
        chars = "^▲⛰"
    else:
        chars = "*✦❄"

    # Guard against division by zero when max_dist is 0
    if max_dist <= 0:
        return chars[0]
    idx = min(len(chars) - 1, int(dist / max_dist * (len(chars) - 1)))
    return chars[idx]


# ── Sky rendering ────────────────────────────────────────────────────

def sky_color(row: int, total_rows: int, sun_x_norm: float, sun_y_norm: float,
              hour: float = 12.0) -> int:
    """Return ANSI 256-color for sky at a given row, with day/night cycle."""
    palette = _lerp_palette(SKY_DAY, SKY_SUNSET, SKY_NIGHT, hour)
    sky_top, sky_mid, sky_bottom, sun_col, _ = palette

    t = row / max(1, total_rows)

    # Sky gradient
    if t < 0.3:
        c = _blend_256(sky_top, sky_mid, t / 0.3)
    elif t < 0.7:
        c = _blend_256(sky_mid, sky_bottom, (t - 0.3) / 0.4)
    else:
        c = _blend_256(sky_bottom, 189, (t - 0.7) / 0.3)

    # Sun/moon glow
    sun_dist = math.sqrt(((t - sun_y_norm) * 2) ** 2 + 0.01)
    if sun_dist < 0.15:
        glow_strength = max(0, 1 - sun_dist / 0.15) * 0.8
        c = _blend_256(c, sun_col, glow_strength)

    # Stars at night
    if hour < 5 or hour > 22:
        c = _blend_256(c, 16, 0.3)  # deepen the night sky

    return c


# ── Renderer ─────────────────────────────────────────────────────────

class TerrainFlyover:
    """Main flyover renderer with optional interactive controls."""

    def __init__(self, seed: Optional[int] = None, speed: float = 1.0,
                 altitude: float = 0.6, fog_dist: int = 40,
                 width: Optional[int] = None, height: Optional[int] = None,
                 show_stats: bool = True, hour: float = 12.0,
                 interactive: bool = False, show_minimap: bool = False):
        self.seed = seed if seed is not None else random.randint(0, 999999)
        self.noise = PerlinNoise(self.seed)
        self.noise2 = PerlinNoise(self.seed + 1000)  # for detail/clouds
        self.speed = speed
        self.altitude = altitude  # 0.0 = ground level, 1.0 = very high
        self.fog_dist = fog_dist
        self.show_stats = show_stats
        self.hour = hour
        self.interactive = interactive
        self.show_minimap = show_minimap

        # Terminal dimensions
        try:
            ts = os.get_terminal_size()
            self.width = width or min(120, ts.columns - 1)
            self.height = height or min(40, ts.lines - 1)
        except OSError:
            self.width = width or 100
            self.height = height or 35

        # Camera position
        self.pos_x: float = 0.0
        self.pos_z: float = 0.0
        self.heading: float = 0.0  # radians

        # Cloud offset for animation
        self.cloud_offset: float = 0.0

        # Trail breadcrumb positions
        self.trail: List[Tuple[float, float]] = []

        # Interactive state
        self._keys_held = set()

    def get_height(self, x: float, z: float) -> float:
        """Get terrain height at world coordinates (x, z). Returns [0, 1]."""
        h = self.noise.octave_noise(x * 0.015, z * 0.015, octaves=6, persistence=0.55)
        # Add detail
        h += self.noise2.octave_noise(x * 0.06, z * 0.06, octaves=3, persistence=0.35) * 0.25
        # Normalize: octave_noise range is roughly [-0.35, 0.35]
        h = (h + 0.4) / 0.8  # map [-0.4, 0.4] -> [0, 1]
        h = max(0, min(1, h))
        # Apply power curve for more pronounced peaks and valleys
        if h < 0.5:
            h = 0.5 * (2 * h) ** 1.3
        else:
            h = 1 - 0.5 * (2 * (1 - h)) ** 1.3
        return max(0, min(1, h))

    def get_cloud_density(self, x: float, z: float) -> float:
        """Get cloud density at world coordinates (0 = clear, >0.5 = cloudy)."""
        c = self.noise2.octave_noise(x * 0.005 + 500, z * 0.005 + 500,
                                     octaves=3, persistence=0.4)
        return max(0, (c + 0.3) * 1.5)

    def _get_biome(self, x: float, z: float) -> str:
        """Determine the biome name at world coordinates."""
        h = self.get_height(x, z)
        if h < 0.28:
            return "Ocean"
        elif h < 0.35:
            return "Shallows"
        elif h < 0.40:
            return "Beach"
        elif h < 0.55:
            return "Plains"
        elif h < 0.68:
            return "Forest"
        elif h < 0.82:
            return "Mountains"
        else:
            return "Alpine"

    def render_frame(self, frame: int) -> str:
        """Render a single frame and return the ANSI string to display."""
        lines = []
        w = self.width
        h = self.height

        # Minimap overlay reserves bottom-right corner
        minimap_size = 0
        minimap_lines = []
        if self.show_minimap:
            minimap_size = min(20, w // 4, h // 4)
            minimap_lines = self._render_minimap_inline(minimap_size, frame)

        # Flyover viewport dimensions (leave room for minimap + stats)
        view_h = h - 1 if self.show_stats else h

        horizon = int(view_h * 0.35)  # horizon row

        # Camera movement
        speed_mult = self.speed
        heading_delta = 0.0

        if self.interactive:
            # Process held keys for interactive mode
            if 'w' in self._keys_held or 'W' in self._keys_held:
                speed_mult = self.speed * 2.0
            if 's' in self._keys_held or 'S' in self._keys_held:
                speed_mult = self.speed * 0.3
            if 'a' in self._keys_held or 'A' in self._keys_held:
                heading_delta = -0.05
            if 'd' in self._keys_held or 'D' in self._keys_held:
                heading_delta = 0.05
            if 'q' in self._keys_held or 'Q' in self._keys_held:
                self.altitude = max(0.1, self.altitude - 0.02)
            if 'e' in self._keys_held or 'E' in self._keys_held:
                self.altitude = min(1.0, self.altitude + 0.02)
            self.heading += heading_delta
        else:
            # Automatic gentle heading oscillation
            self.heading = (math.sin(frame * 0.003) * 0.3
                            + math.sin(frame * 0.0007) * 0.8)

        self.pos_x += math.cos(self.heading) * 0.8 * speed_mult
        self.pos_z += math.sin(self.heading) * 0.8 * speed_mult

        # Animate clouds
        self.cloud_offset += 0.3 * self.speed

        # Advance time-of-day if not fixed
        if self.hour >= 0:
            # Time advances slowly: ~1 hour per 30 seconds of real time
            pass  # hour is fixed unless auto-cycling

        # Sun position (moves slowly across the sky)
        sun_x_norm = 0.5 + 0.3 * math.sin(frame * 0.001)
        sun_y_norm = 0.3 + 0.05 * math.sin(frame * 0.002)

        # Build the frame line by line
        for row in range(view_h):
            col_buf = []

            for col in range(w):
                # Normalized screen coordinates
                sx = (col / w - 0.5) * 2.0  # -1 to 1
                sy = (row / view_h)  # 0 to 1 (top to bottom)

                if row < horizon:
                    # ── Sky ──
                    c = sky_color(row, horizon, sun_x_norm, sun_y_norm, self.hour)

                    # Clouds
                    cloud_screen_x = sx
                    cloud_world_x = self.pos_x + cloud_screen_x * 50 + self.cloud_offset
                    cloud_world_z = self.pos_z - 100 + row * 2
                    cloud_d = self.get_cloud_density(cloud_world_x, cloud_world_z)
                    if cloud_d > 0.5 and row > horizon * 0.3:
                        blend = min(1, (cloud_d - 0.5) * 2)
                        c = _blend_256(c, CLOUD_COLOR, blend * 0.6)

                    ch = " "
                    if cloud_d > 0.6 and row > horizon * 0.4:
                        if self.hour < 6 or self.hour > 21:
                            ch = "·"  # dim stars through thin clouds at night
                        else:
                            ch = "░" if cloud_d < 0.75 else ("▒" if cloud_d < 0.85 else "▓")

                    col_buf.append(f"{ESC}38;5;{c}m{ch}")

                else:
                    # ── Terrain ──
                    below_horizon = row - horizon
                    dist_ratio = below_horizon / max(1, view_h - horizon)

                    # Perspective: further rows = further distance
                    dist = self.fog_dist / max(0.01, dist_ratio) * 0.3
                    dist = max(1, min(self.fog_dist, dist))

                    # World position of this terrain column
                    world_x = (self.pos_x + sx * dist * math.cos(self.heading)
                                - dist * math.sin(self.heading) * 0.1)
                    world_z = (self.pos_z + sx * dist * math.sin(self.heading)
                                + dist * math.cos(self.heading) * 0.1)

                    # Get height at this world position
                    th = self.get_height(world_x, world_z)

                    # Apply altitude offset — camera is above ground
                    camera_h = self.altitude
                    apparent_h = th - (1 - camera_h) * dist_ratio
                    apparent_h = max(0, min(1, apparent_h))

                    # Fog (guard against zero fog_dist)
                    fog_factor = (dist / max(1, self.fog_dist)) ** 1.5

                    # Get color and character (with time-of-day and animation)
                    c = height_to_color(apparent_h, fog_factor, self.hour)
                    ch = height_to_char(th, dist, max(1, self.fog_dist), frame)

                    # Hill shading
                    if apparent_h > 0.4 and dist < self.fog_dist * 0.6:
                        neighbor_h = self.get_height(world_x + 2, world_z)
                        shade = max(0, min(1, 0.5 + (th - neighbor_h) * 5))
                        if shade > 0.6:
                            c = _blend_256(c, 232, (shade - 0.6) * 0.5)

                    col_buf.append(f"{ESC}38;5;{c}m{ch}")

            lines.append("".join(col_buf))

        # Overlay minimap if enabled
        if self.show_minimap and minimap_lines:
            self._overlay_minimap(lines, minimap_lines, minimap_size, w)

        # Build status line
        if self.show_stats:
            biome = self._get_biome(self.pos_x, self.pos_z)
            hour_display = f"{int(self.hour):02d}:{int((self.hour % 1) * 60):02d}"
            compass = self._heading_to_compass(self.heading)
            stats = (
                f"  POS ({self.pos_x:.0f},{self.pos_z:.0f})  "
                f"HDG {math.degrees(self.heading):.0f}° {compass}  "
                f"BIOME {biome}  "
                f"SEED {self.seed}  "
                f"ALT {self.altitude:.1f}  "
                f"SPD {speed_mult:.1f}×  "
                f"TIME {hour_display}"
            )
            if self.interactive:
                stats += "  [WASDQE]"
            stats_padded = stats.ljust(w)
            stats_line = f"{ESC}48;5;236;38;5;252m{stats_padded}{RESET}"
            lines.append(stats_line)

        # Trail breadcrumb
        if frame % 20 == 0:
            self.trail.append((self.pos_x, self.pos_z))
            if len(self.trail) > 50:
                self.trail.pop(0)

        return f"{ESC}H" + "\n".join(lines) + RESET

    @staticmethod
    def _heading_to_compass(heading: float) -> str:
        """Convert a heading in radians to a compass direction string."""
        deg = math.degrees(heading) % 360
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((deg + 22.5) / 45) % 8
        return directions[idx]

    def _render_minimap_inline(self, size: int, frame: int) -> List[str]:
        """Render a small top-down minimap for overlay."""
        lines = []
        for row in range(size):
            line_parts = []
            for col in range(size):
                wx = self.pos_x + (col - size // 2) * 0.5
                wz = self.pos_z + (row - size // 2) * 0.5
                h = self.get_height(wx, wz)
                c = height_to_color(h, 0.0, self.hour)
                if h < 0.35:
                    ch = "~"
                elif h < 0.40:
                    ch = "."
                elif h < 0.55:
                    ch = "\""
                elif h < 0.72:
                    ch = "♣"
                elif h < 0.82:
                    ch = "^"
                else:
                    ch = "*"
                line_parts.append(f"{ESC}38;5;{c}m{ch}")
            lines.append("".join(line_parts))
        return lines

    @staticmethod
    def _parse_ansi_cells(line: str) -> List[Tuple[str, str]]:
        """Parse an ANSI-coded string into a list of (ansi_prefix, char) tuples.

        Each visual cell on the terminal corresponds to one tuple.
        ANSI escape sequences are grouped with their following visible character.
        """
        cells = []
        pos = 0
        current_ansi = ""
        while pos < len(line):
            if line[pos] == '\x1b':
                # Start of ANSI escape sequence
                seq_start = pos
                pos += 1  # skip ESC
                if pos < len(line) and line[pos] == '[':
                    pos += 1  # skip '['
                    while pos < len(line) and line[pos] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz':
                        pos += 1
                    if pos < len(line):
                        pos += 1  # skip the final letter
                elif pos < len(line) and line[pos] == ']':
                    # OSC sequence: ESC] ... BEL or ST
                    pos += 1
                    while pos < len(line) and line[pos] != '\x07' and line[pos:pos+2] != '\x1b\\':
                        pos += 1
                    if pos < len(line):
                        if line[pos] == '\x07':
                            pos += 1
                        elif line[pos:pos+2] == '\x1b\\':
                            pos += 2
                else:
                    pos += 1  # skip unknown after ESC
                current_ansi = line[seq_start:pos]
                # The ANSI prefix belongs to the next visible char
                continue
            elif line[pos] == '\n':
                pos += 1
                continue
            else:
                # Visible character — attach any pending ANSI prefix
                cells.append((current_ansi, line[pos]))
                current_ansi = ""
                pos += 1
        return cells

    @staticmethod
    def _cells_to_string(cells: List[Tuple[str, str]]) -> str:
        """Convert a list of (ansi_prefix, char) tuples back to a string."""
        return "".join(a + c for a, c in cells)

    def _overlay_minimap(self, frame_lines: List[str], minimap_lines: List[str],
                          size: int, width: int) -> None:
        """Overlay the minimap onto the bottom-right corner of the frame.

        Properly handles ANSI escape sequences by parsing visual cells
        instead of slicing raw byte strings.
        """
        start_row = len(frame_lines) - size - 1  # -1 for stats bar

        for i, mini_line in enumerate(minimap_lines):
            row_idx = start_row + i
            if row_idx < 0 or row_idx >= len(frame_lines):
                continue

            # Parse the frame line into visual cells
            cells = self._parse_ansi_cells(frame_lines[row_idx])
            # Parse the minimap line into visual cells
            mini_cells = self._parse_ansi_cells(mini_line)

            # Border cell
            border = f"{ESC}48;5;236;38;5;252m "
            border_cell = (border, " ")

            # Calculate where the minimap starts (in visual columns from the right)
            start_col = max(0, len(cells) - size - 2)

            # Build new cell list: original up to start_col, border, minimap cells, border, RESET
            new_cells = cells[:start_col]
            new_cells.append(border_cell)
            new_cells.extend(mini_cells)
            new_cells.append(border_cell)
            new_cells.append((RESET, ""))

            frame_lines[row_idx] = self._cells_to_string(new_cells)

    def render_screenshot(self, frame: int = 0) -> str:
        """Render a single frame for screenshot export (strip ANSI codes for plain text)."""
        ansi_output = self.render_frame(frame)
        # Strip all ANSI escape sequences (CSI sequences, OSC sequences, etc.)
        import re
        plain = re.sub(r'\033\[[0-9;]*[A-Za-z]', '', ansi_output)
        plain = re.sub(r'\033\].*?\007', '', plain)  # OSC sequences
        plain = re.sub(r'\033\[', '', plain)  # any remaining bare CSI
        return plain


# ── Top-down map mode ────────────────────────────────────────────────

def render_minimap(flyover: TerrainFlyover, map_w: int = 80, map_h: int = 30,
                   center_x: float = 0, center_z: float = 0,
                   scale: float = 0.15, hour: float = 12.0) -> str:
    """Render a top-down ASCII minimap of the terrain."""
    lines = []
    for row in range(map_h):
        line = []
        for col in range(map_w):
            wx = center_x + (col - map_w // 2) * scale
            wz = center_z + (row - map_h // 2) * scale
            h = flyover.get_height(wx, wz)
            c = height_to_color(h, 0.0, hour)
            if h < 0.35:
                ch = "~"
            elif h < 0.40:
                ch = "."
            elif h < 0.55:
                ch = "\""
            elif h < 0.72:
                ch = "♣"
            elif h < 0.82:
                ch = "^"
            else:
                ch = "*"
            line.append(f"{ESC}38;5;{c}m{ch}")
        lines.append("".join(line))

    # Position marker — replace center character with a plane marker
    center_row = map_h // 2
    center_col = map_w // 2
    # Parse ANSI-colored string into visual cells and replace center with marker
    center_cells = TerrainFlyover._parse_ansi_cells(lines[center_row])
    if center_col < len(center_cells):
        marker_ansi = f"{ESC}38;5;196m"
        center_cells[center_col] = (marker_ansi, "▶")

    lines[center_row] = TerrainFlyover._cells_to_string(center_cells)

    return "\n".join(lines) + RESET


def show_map(seed: Optional[int] = None, scale: float = 0.2,
             map_size: Optional[Tuple[int, int]] = None, hour: float = 12.0) -> None:
    """Show a static top-down map of the terrain."""
    try:
        term_w = os.get_terminal_size().columns
        term_h = os.get_terminal_size().lines
    except OSError:
        term_w, term_h = 100, 35

    w = min(term_w - 2, 140) if map_size is None else map_size[0]
    h = min(term_h - 4, 50) if map_size is None else map_size[1]

    flyover = TerrainFlyover(seed=seed, width=w, height=h, hour=hour)

    sys.stdout.write(CLEAR)
    hour_str = f"{int(hour):02d}:00" if hour >= 0 else "auto"
    print(f"  🗺️  Terrain Map — Seed {flyover.seed} — Time {hour_str} (Press Ctrl+C to exit)\n")

    output = render_minimap(flyover, map_w=w, map_h=h, scale=scale, hour=hour)
    print(output)

    # Legend
    legend_items = [
        ("~ Ocean", DEEP_WATER), (". Beach", SAND), ("\" Plains", GRASS),
        ("♣ Forest", FOREST), ("^ Mountain", MOUNTAIN), ("* Alpine", SNOW),
    ]
    print()
    legend = "  "
    for name, color in legend_items:
        legend += f"{ESC}38;5;{color}m■{RESET} {name}  "
    print(legend + RESET)


# ── Interactive keyboard input ───────────────────────────────────────

def _read_key_nonblock(fd: int, timeout: float = 0.01) -> Optional[str]:
    """Read a single keypress non-blockingly. Returns None if no key available."""
    try:
        rlist, _, _ = select.select([fd], [], [], timeout)
        if rlist:
            return os.read(fd, 1).decode('utf-8', errors='replace')
    except (OSError, ValueError):
        pass
    return None


# ── Main run functions ───────────────────────────────────────────────

def run_demo(seed: Optional[int] = None, speed: float = 1.0, altitude: float = 0.6,
             fps: int = 20, duration: Optional[int] = None, hour: float = 12.0,
             interactive: bool = False, show_minimap: bool = False) -> None:
    """Run the terrain flyover demo."""
    try:
        ts = os.get_terminal_size()
        term_w, term_h = ts.columns, ts.lines
    except OSError:
        term_w, term_h = 100, 35

    w = min(term_w - 1, 140)
    h = min(term_h - 2, 50)

    flyover = TerrainFlyover(
        seed=seed,
        speed=speed,
        altitude=altitude,
        width=w,
        height=h,
        hour=hour,
        interactive=interactive,
        show_minimap=show_minimap,
    )

    # Clear screen and hide cursor
    sys.stdout.write(CLEAR + HIDE_CURSOR)
    sys.stdout.flush()

    # Interactive mode: set terminal to raw for key reading
    old_settings = None
    if interactive:
        try:
            old_settings = termios.tcgetattr(sys.stdin.fileno())
            tty.setraw(sys.stdin.fileno())
        except (termios.error, AttributeError):
            interactive = False

    frame = 0
    start_time = time.time()
    try:
        while True:
            if duration and (time.time() - start_time) > duration:
                break

            # Handle keyboard input in interactive mode
            if interactive:
                key = _read_key_nonblock(sys.stdin.fileno())
                while key is not None:
                    if key == '\x1b':  # Escape sequences
                        # Read the rest of the escape sequence
                        k2 = _read_key_nonblock(sys.stdin.fileno(), 0.005)
                        if k2 == '[':
                            _ = _read_key_nonblock(sys.stdin.fileno(), 0.005)
                        # Arrow keys etc — ignore for now
                    elif key == '\x03':  # Ctrl+C
                        raise KeyboardInterrupt
                    elif key == 'x' or key == 'X':
                        raise KeyboardInterrupt  # eXit
                    else:
                        flyover._keys_held.add(key.lower())
                    key = _read_key_nonblock(sys.stdin.fileno())

            frame_start = time.time()
            output = flyover.render_frame(frame)
            # Clear held keys after rendering so they don't stick
            flyover._keys_held = set()
            sys.stdout.write(output)
            sys.stdout.flush()

            # Frame timing
            elapsed = time.time() - frame_start
            target = 1.0 / fps
            if elapsed < target:
                time.sleep(target - elapsed)

            frame += 1

    except KeyboardInterrupt:
        pass
    finally:
        if old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
            except (termios.error, AttributeError):
                pass
        sys.stdout.write(SHOW_CURSOR + CLEAR + RESET)
        sys.stdout.flush()
        print(f"\n🏔️  Terrain Flyover Complete!")
        print(f"   Seed: {flyover.seed}")
        print(f"   Position: ({flyover.pos_x:.0f}, {flyover.pos_z:.0f})")
        print(f"   Heading: {math.degrees(flyover.heading):.0f}° {flyover._heading_to_compass(flyover.heading)}")
        print(f"   Frames rendered: {frame}")
        print(f"   Duration: {time.time() - start_time:.1f}s")


def run_screenshot(seed: Optional[int] = None, altitude: float = 0.6,
                   filepath: str = "terrain_screenshot.txt",
                   hour: float = 12.0, width: int = 120, height: int = 40) -> None:
    """Render a single frame and save it to a file (no ANSI codes)."""
    flyover = TerrainFlyover(
        seed=seed,
        altitude=altitude,
        width=width,
        height=height,
        show_stats=True,
        hour=hour,
    )

    output = flyover.render_screenshot(frame=0)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"📸 Screenshot saved to: {filepath}")
    print(f"   Seed: {flyover.seed}")
    print(f"   Size: {width}×{height}")


# ── Main entry point ─────────────────────────────────────────────────

def main() -> None:
    """Parse arguments and run the terrain flyover."""
    parser = argparse.ArgumentParser(
        description="🏔️  ASCII Terrain Flyover — Procedural terrain rendered in your terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Start flyover with random seed
  %(prog)s --seed 42           # Use specific seed
  %(prog)s --speed 2.0         # Fly faster
  %(prog)s --altitude 0.8      # Higher altitude view
  %(prog)s --hour 19           # Sunset lighting
  %(prog)s --hour 2            # Night mode
  %(prog)s --map               # Show top-down map instead
  %(prog)s --interactive        # Use WASDQE keys to fly
  %(prog)s --minimap           # Show minimap overlay
  %(prog)s --screenshot out.txt # Save a single frame to file

Keyboard Controls (interactive mode):
  W/S   - Speed up / Slow down
  A/D   - Turn left / Turn right
  Q/E   - Decrease / Increase altitude
  X     - Exit
        """
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for terrain")
    parser.add_argument("--speed", type=float, default=1.0, help="Flight speed (default: 1.0)")
    parser.add_argument("--altitude", type=float, default=0.6,
                        help="Camera altitude 0.1-1.0 (default: 0.6)")
    parser.add_argument("--fps", type=int, default=20, help="Target FPS (default: 20)")
    parser.add_argument("--duration", type=int, default=None,
                        help="Duration in seconds (default: infinite)")
    parser.add_argument("--map", action="store_true",
                        help="Show top-down map instead of flyover")
    parser.add_argument("--scale", type=float, default=0.2,
                        help="Map scale for --map mode (default: 0.2)")
    parser.add_argument("--hour", type=float, default=12.0,
                        help="Time of day 0-24 (default: 12=noon). Try 0=midnight, 19=sunset")
    parser.add_argument("--interactive", action="store_true",
                        help="Enable keyboard controls (WASDQE)")
    parser.add_argument("--minimap", action="store_true",
                        help="Show minimap overlay during flyover")
    parser.add_argument("--screenshot", type=str, default=None, metavar="FILE",
                        help="Save a single frame to FILE and exit")

    args = parser.parse_args()

    if args.screenshot:
        run_screenshot(
            seed=args.seed,
            altitude=max(0.1, min(1.0, args.altitude)),
            filepath=args.screenshot,
            hour=args.hour,
        )
    elif args.map:
        show_map(seed=args.seed, scale=args.scale, hour=args.hour)
    else:
        run_demo(
            seed=args.seed,
            speed=args.speed,
            altitude=max(0.1, min(1.0, args.altitude)),
            fps=args.fps,
            duration=args.duration,
            hour=args.hour,
            interactive=args.interactive,
            show_minimap=args.minimap,
        )


if __name__ == "__main__":
    main()