#!/usr/bin/env python3
"""
ASCII Terrain Flyover — Procedural terrain rendered as a first-person
flyover animation in the terminal.

Uses Perlin-like noise for terrain generation, a height-based color map,
and a simple ray-marching approach to render perspective terrain columns.
"""

import os
import sys
import time
import math
import random
import argparse
from collections import namedtuple

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


# ── Noise generation (simple Perlin-like) ────────────────────────────

class PerlinNoise:
    """Simple 2D Perlin noise implementation."""

    def __init__(self, seed=None):
        rng = random.Random(seed)
        self.perm = list(range(256))
        rng.shuffle(self.perm)
        self.perm = self.perm + self.perm  # double for wrapping
        self.gradients = [
            (math.cos(2 * math.pi * i / 256), math.sin(2 * math.pi * i / 256))
            for i in range(256)
        ]

    @staticmethod
    def _fade(t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    @staticmethod
    def _lerp(a, b, t):
        return a + t * (b - a)

    def _grad(self, h, x, y):
        g = self.gradients[h & 255]
        return g[0] * x + g[1] * y

    def noise(self, x, y):
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

    def octave_noise(self, x, y, octaves=6, persistence=0.5, lacunarity=2.0):
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


# ── Terrain ───────────────────────────────────────────────────────────

def height_to_color(h, fog_factor=0.0):
    """Map a height value (0-1) to an ANSI 256-color index with fog."""
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

    # Blend with fog color for distance
    if fog_factor > 0:
        c = _blend_256(c, FOG, fog_factor)
    return c


def _blend_256(c1, c2, t):
    """Blend two 256-color palette indices by t (0=c1, 1=c2)."""
    # Approximate RGB for common palette indices
    rgb_map = {
        17: (0, 0, 95), 25: (0, 95, 175), 180: (175, 135, 95),
        34: (0, 175, 0), 28: (0, 135, 0), 22: (0, 95, 0),
        95: (135, 95, 95), 255: (255, 255, 255), 18: (0, 0, 95),
        111: (135, 175, 215), 244: (180, 180, 180), 220: (255, 215, 0),
        252: (230, 230, 230), 236: (70, 70, 70), 240: (140, 140, 140),
        59: (95, 95, 135), 60: (95, 95, 175), 67: (95, 135, 175),
        74: (95, 175, 215), 111: (135, 175, 215), 117: (135, 175, 255),
    }
    r1, g1, b1 = rgb_map.get(c1, (128, 128, 128))
    r2, g2, b2 = rgb_map.get(c2, (128, 128, 128))
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return _rgb_to_256(r, g, b)


def _rgb_to_256(r, g, b):
    """Find nearest 256-color index for an RGB value."""
    # Use 6x6x6 color cube (indices 16-231)
    r_idx = min(5, max(0, round(r / 51)))
    g_idx = min(5, max(0, round(g / 51)))
    b_idx = min(5, max(0, round(b / 51)))
    return 16 + 36 * r_idx + 6 * g_idx + b_idx


def height_to_char(h, dist, max_dist):
    """Map height and distance to an ASCII character."""
    if h < 0.35:
        chars = "~≈∽"
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
    idx = min(len(chars) - 1, int(dist / max_dist * (len(chars) - 1)))
    return chars[idx]


# ── Sky rendering ────────────────────────────────────────────────────

def sky_color(row, total_rows, sun_x, sun_y):
    """Return ANSI 256-color for sky at a given row."""
    # Gradient from top to bottom
    t = row / max(1, total_rows)

    # Sky colors: dark blue at top, lighter blue at bottom
    if t < 0.3:
        c = _blend_256(SKY_TOP, 39, t / 0.3)
    elif t < 0.7:
        c = _blend_256(39, SKY_BOTTOM, (t - 0.3) / 0.4)
    else:
        c = _blend_256(SKY_BOTTOM, 189, (t - 0.7) / 0.3)

    # Sun glow
    sun_dist = math.sqrt(((t - sun_y) * 2) ** 2 + 0.01)
    if sun_dist < 0.15:
        c = _blend_256(c, SUN_COLOR, max(0, 1 - sun_dist / 0.15) * 0.8)

    return c


# ── Renderer ─────────────────────────────────────────────────────────

class TerrainFlyover:
    """Main flyover renderer."""

    def __init__(self, seed=None, speed=1.0, altitude=0.6, fog_dist=40,
                 width=None, height=None, show_stats=True):
        self.seed = seed or random.randint(0, 999999)
        self.noise = PerlinNoise(self.seed)
        self.noise2 = PerlinNoise(self.seed + 1000)  # for detail
        self.speed = speed
        self.altitude = altitude  # 0.0 = ground level, 1.0 = very high
        self.fog_dist = fog_dist
        self.show_stats = show_stats

        # Terminal dimensions
        self.width = width or min(120, os.get_terminal_size().columns - 1)
        self.height = height or min(40, os.get_terminal_size().lines - 1)

        # Camera position
        self.pos_x = 0.0
        self.pos_z = 0.0
        self.heading = 0.0  # radians

        # Cloud offset
        self.cloud_offset = 0.0

        # Trail breadcrumb positions
        self.trail = []

    def get_height(self, x, z):
        """Get terrain height at world coordinates (x, z)."""
        # Multi-octave noise for interesting terrain — wider frequency for more variation
        h = self.noise.octave_noise(x * 0.015, z * 0.015, octaves=6, persistence=0.55)
        # Add detail
        h += self.noise2.octave_noise(x * 0.06, z * 0.06, octaves=3, persistence=0.35) * 0.25
        # Normalize: octave_noise range is roughly [-0.35, 0.35]
        # Map to [0, 1] and apply power curve for better biome distribution
        h = (h + 0.4) / 0.8  # map [-0.4, 0.4] -> [0, 1]
        # Apply power curve to create more pronounced peaks and valleys
        h = max(0, min(1, h))
        # Stretch: push low values lower and high values higher
        if h < 0.5:
            h = 0.5 * (2 * h) ** 1.3
        else:
            h = 1 - 0.5 * (2 * (1 - h)) ** 1.3
        return max(0, min(1, h))

    def get_cloud_density(self, x, z):
        """Get cloud density at world coordinates."""
        c = self.noise2.octave_noise(x * 0.005 + 500, z * 0.005 + 500, octaves=3, persistence=0.4)
        return max(0, (c + 0.3) * 1.5)

    def render_frame(self, frame):
        """Render a single frame and return the string to display."""
        lines = []
        w = self.width
        h = self.height
        horizon = int(h * 0.35)  # horizon row

        # Camera movement
        self.pos_x += math.cos(self.heading) * 0.8 * self.speed
        self.pos_z += math.sin(self.heading) * 0.8 * self.speed
        # Gentle heading oscillation
        self.heading = math.sin(frame * 0.003) * 0.3 + math.sin(frame * 0.0007) * 0.8

        # Sun position (moves slowly)
        sun_x_norm = 0.5 + 0.3 * math.sin(frame * 0.001)
        sun_y_norm = 0.3 + 0.05 * math.sin(frame * 0.002)

        # Build the frame line by line
        for row in range(h):
            col_buf = []

            for col in range(w):
                # Normalized screen coordinates
                sx = (col / w - 0.5) * 2.0  # -1 to 1
                sy = (row / h)  # 0 to 1 (top to bottom)

                if row < horizon:
                    # ── Sky ──
                    c = sky_color(row, horizon, sun_x_norm, sun_y_norm)

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
                        ch = "░" if cloud_d < 0.75 else ("▒" if cloud_d < 0.85 else "▓")

                    col_buf.append(f"{ESC}38;5;{c}m{ch}")

                else:
                    # ── Terrain ──
                    # Calculate distance based on how far below horizon
                    below_horizon = row - horizon
                    dist_ratio = below_horizon / (h - horizon)

                    # Perspective: further rows = further distance
                    dist = self.fog_dist / max(0.01, dist_ratio) * 0.3
                    dist = max(1, min(self.fog_dist, dist))

                    # World position of this terrain column
                    world_x = self.pos_x + sx * dist * math.cos(self.heading) \
                              - dist * math.sin(self.heading) * 0.1
                    world_z = self.pos_z + sx * dist * math.sin(self.heading) \
                              + dist * math.cos(self.heading) * 0.1

                    # Get height at this world position
                    th = self.get_height(world_x, world_z)

                    # Apply altitude offset — camera is above ground
                    camera_h = self.altitude
                    # Adjust perceived height
                    apparent_h = th - (1 - camera_h) * dist_ratio
                    apparent_h = max(0, min(1, apparent_h))

                    # Fog
                    fog_factor = (dist / self.fog_dist) ** 1.5

                    # Get color and character
                    c = height_to_color(apparent_h, fog_factor)
                    ch = height_to_char(th, dist, self.fog_dist)

                    # Shade based on height gradient (simple lighting)
                    if apparent_h > 0.4 and dist < self.fog_dist * 0.6:
                        # Add simple hill shading
                        neighbor_h = self.get_height(world_x + 2, world_z)
                        shade = max(0, min(1, 0.5 + (th - neighbor_h) * 5))
                        if shade > 0.6:
                            c = _blend_256(c, 232, (shade - 0.6) * 0.5)

                    col_buf.append(f"{ESC}38;5;{c}m{ch}")

            lines.append("".join(col_buf))

        # Build status line
        if self.show_stats:
            biome = self._get_biome(self.pos_x, self.pos_z)
            stats = (
                f"  POS ({self.pos_x:.0f},{self.pos_z:.0f})  "
                f"HDG {math.degrees(self.heading):.0f}°  "
                f"BIOME {biome}  "
                f"SEED {self.seed}  "
                f"ALT {self.altitude:.1f}  "
                f"SPD {self.speed:.1f}×"
            )
            # Pad stats line
            stats_padded = stats.ljust(w)
            stats_line = f"{ESC}48;5;236;38;5;252m{stats_padded}{RESET}"
            lines.append(stats_line)

        # Add trail marker
        if frame % 20 == 0:
            self.trail.append((self.pos_x, self.pos_z))
            if len(self.trail) > 50:
                self.trail.pop(0)

        # Move cursor home instead of clearing for smoother animation
        return f"{ESC}H" + "\n".join(lines) + RESET

    def _get_biome(self, x, z):
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


def run_demo(seed=None, speed=1.0, altitude=0.6, fps=20, duration=None):
    """Run the terrain flyover demo."""
    try:
        term_w = os.get_terminal_size().columns
        term_h = os.get_terminal_size().lines
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
    )

    # Clear screen and hide cursor
    sys.stdout.write(CLEAR + HIDE_CURSOR)
    sys.stdout.flush()

    frame = 0
    start_time = time.time()
    try:
        while True:
            if duration and (time.time() - start_time) > duration:
                break
            frame_start = time.time()
            output = flyover.render_frame(frame)
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
        sys.stdout.write(SHOW_CURSOR + CLEAR + RESET)
        sys.stdout.flush()
        print(f"\n🏔️  Terrain Flyover Complete!")
        print(f"   Seed: {flyover.seed}")
        print(f"   Position: ({flyover.pos_x:.0f}, {flyover.pos_z:.0f})")
        print(f"   Frames rendered: {frame}")
        print(f"   Duration: {time.time() - start_time:.1f}s")


# ── Map mode (top-down minimap) ──────────────────────────────────────

def render_minimap(flyover, map_w=80, map_h=30, center_x=0, center_z=0, scale=0.15):
    """Render a top-down ASCII minimap of the terrain."""
    lines = []
    for row in range(map_h):
        line = []
        for col in range(map_w):
            wx = center_x + (col - map_w // 2) * scale
            wz = center_z + (row - map_h // 2) * scale
            h = flyover.get_height(wx, wz)
            c = height_to_color(h)
            # Different chars for different heights in top-down view
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

    # Add position marker
    px = map_w // 2
    pz = map_h // 2
    if 0 <= px < map_w and 0 <= pz < map_h:
        row_list = list(lines[pz])
        # Overwrite the character at position px with a plane marker
        # This is approximate since we're using ANSI codes
        lines[pz] = f"{ESC}38;5;196m▶" + lines[pz][abs(lines[pz].find("m", 5))+1:] if "m" in lines[pz] else lines[pz]

    return "\n".join(lines) + RESET


def show_map(seed=None, scale=0.2, map_size=None):
    """Show a static top-down map of the terrain."""
    try:
        term_w = os.get_terminal_size().columns
        term_h = os.get_terminal_size().lines
    except OSError:
        term_w, term_h = 100, 35

    w = min(term_w - 2, 140) if map_size is None else map_size[0]
    h = min(term_h - 4, 50) if map_size is None else map_size[1]

    flyover = TerrainFlyover(seed=seed, width=w, height=h)

    sys.stdout.write(CLEAR)
    print(f"  🗺️  Terrain Map — Seed {flyover.seed} (Press Ctrl+C to exit)\n")

    output = render_minimap(flyover, map_w=w, map_h=h, scale=scale)
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


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🏔️  ASCII Terrain Flyover — Procedural terrain rendered in your terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Start flyover with random seed
  %(prog)s --seed 42           # Use specific seed
  %(prog)s --speed 2.0         # Fly faster
  %(prog)s --altitude 0.8      # Higher altitude view
  %(prog)s --map               # Show top-down map instead
  %(prog)s --fps 30            # Higher framerate
        """
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for terrain")
    parser.add_argument("--speed", type=float, default=1.0, help="Flight speed (default: 1.0)")
    parser.add_argument("--altitude", type=float, default=0.6, help="Camera altitude 0.1-1.0 (default: 0.6)")
    parser.add_argument("--fps", type=int, default=20, help="Target FPS (default: 20)")
    parser.add_argument("--duration", type=int, default=None, help="Duration in seconds (default: infinite)")
    parser.add_argument("--map", action="store_true", help="Show top-down map instead of flyover")
    parser.add_argument("--scale", type=float, default=0.2, help="Map scale for --map mode (default: 0.2)")

    args = parser.parse_args()

    if args.map:
        show_map(seed=args.seed, scale=args.scale)
    else:
        run_demo(
            seed=args.seed,
            speed=args.speed,
            altitude=max(0.1, min(1.0, args.altitude)),
            fps=args.fps,
            duration=args.duration,
        )


if __name__ == "__main__":
    main()