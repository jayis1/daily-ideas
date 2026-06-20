#!/usr/bin/env python3
"""
Terminal Water Ripple Simulator
===============================
A real-time 2D wave equation simulator rendered in the terminal using Unicode
block characters and 24-bit ANSI colors. Drop stones, place wave sources, build
walls, and watch waves propagate, interfere, and reflect — all from your terminal.

Controls:
  SPACE   Drop a stone at a random position
  D       Drop a big stone
  F       Place / remove a continuous wave source
  I       Interference demo (two symmetric drops)
  R       Toggle rain mode (auto-drops)
  P       Cycle preset wall patterns
  T       Toggle color-cycling mode
  W       Add a random wall segment
  C       Clear all walls
  X       Reset water (clear simulation)
  +/-     Increase / decrease damping
  [/]     Decrease / increase simulation speed
  1-5     Switch colour palette
  Q/Esc   Quit
"""

from __future__ import annotations

import argparse
import sys
import time
import random
import math
import json
import os
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
__version__ = "1.1.0"

# ---------------------------------------------------------------------------
# Grid dimensions (character cells)
# ---------------------------------------------------------------------------
COLS = 72
ROWS = 28

# ---------------------------------------------------------------------------
# Wave equation parameters
# ---------------------------------------------------------------------------
SPEED = 0.45             # wave propagation speed (0 < c < 0.5 for stability)
DAMPING_DEFAULT = 0.96   # velocity damping per frame (0-1)
FPS = 20

# ---------------------------------------------------------------------------
# Color palettes: list of (r, g, b) tuples indexed by intensity 0..9
# ---------------------------------------------------------------------------
PALETTES = {
    1: [  # Ocean
        (0, 0, 30), (0, 5, 60), (0, 15, 100), (0, 30, 140),
        (0, 60, 170), (10, 100, 190), (40, 150, 210), (100, 200, 230),
        (180, 230, 245), (240, 250, 255),
    ],
    2: [  # Lava
        (20, 0, 0), (60, 0, 0), (110, 10, 0), (160, 30, 0),
        (210, 60, 0), (240, 100, 0), (255, 150, 20), (255, 200, 60),
        (255, 230, 120), (255, 255, 200),
    ],
    3: [  # Toxic
        (0, 15, 0), (0, 30, 5), (0, 50, 10), (0, 80, 15),
        (0, 120, 20), (20, 160, 30), (60, 200, 50), (120, 230, 80),
        (180, 245, 130), (230, 255, 200),
    ],
    4: [  # Purple
        (10, 0, 20), (25, 0, 50), (50, 5, 90), (80, 15, 130),
        (120, 30, 165), (155, 55, 195), (185, 90, 215), (210, 140, 230),
        (230, 195, 242), (248, 235, 255),
    ],
    5: [  # Monochrome
        (8, 8, 8), (20, 20, 20), (38, 38, 38), (60, 60, 60),
        (90, 90, 90), (120, 120, 120), (155, 155, 155), (195, 195, 195),
        (225, 225, 225), (255, 255, 255),
    ],
}

PALETTE_NAMES = {1: "Ocean", 2: "Lava", 3: "Toxic", 4: "Purple", 5: "Mono"}

# Preset wall patterns
WALL_PRESETS = [
    "rectangle",
    "diamond",
    "cross",
    "circle",
    "double_slit",
]

# Unicode block characters ordered by visual density
BLOCK_CHARS = " ░▒▓█"

# Source emission interval (frames between pulses)
SOURCE_INTERVAL = 6


def clamp(v: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi."""
    return max(lo, min(hi, v))


def lerp_color(
    c1: Tuple[int, int, int],
    c2: Tuple[int, int, int],
    t: float,
) -> Tuple[int, int, int]:
    """Linearly interpolate between two RGB colors."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


class WaveSource:
    """A continuous wave source that emits pulses at regular intervals."""

    def __init__(self, x: int, y: int, amplitude: float = 5.0, radius: int = 1):
        self.x = x
        self.y = y
        self.amplitude = amplitude
        self.radius = radius


class RippleSimulator:
    """2D wave equation simulation with terminal rendering."""

    def __init__(self, cols: int = COLS, rows: int = ROWS):
        self.cols = cols
        self.rows = rows
        n = cols * rows

        # Two buffers for the wave equation (current and previous)
        self.current: List[float] = [0.0] * n
        self.previous: List[float] = [0.0] * n

        # Walls / obstacles
        self.walls: List[bool] = [False] * n

        # Continuous wave sources
        self.sources: List[WaveSource] = []

        # State
        self.damping: float = DAMPING_DEFAULT
        self.palette_id: int = 1
        self.rain_mode: bool = False
        self.rain_timer: int = 0
        self.frame: int = 0
        self.drop_count: int = 0
        self.paused: bool = False
        self.color_cycle: bool = False
        self.color_cycle_timer: int = 0
        self.wall_preset_idx: int = -1  # -1 means no preset active
        self.sim_speed: float = 1.0  # multiplier for steps per frame

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------

    def idx(self, x: int, y: int) -> int:
        """Convert (x, y) to linear buffer index."""
        return y * self.cols + x

    def in_bounds(self, x: int, y: int) -> bool:
        """Check if (x, y) is within the grid."""
        return 0 <= x < self.cols and 0 <= y < self.rows

    # ------------------------------------------------------------------
    # Wave simulation
    # ------------------------------------------------------------------

    def drop_stone(
        self,
        cx: int,
        cy: int,
        radius: int = 2,
        amplitude: float = 8.0,
    ) -> None:
        """Create a circular disturbance centred at (cx, cy)."""
        r2 = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = cx + dx, cy + dy
                if not self.in_bounds(nx, ny):
                    continue
                i = self.idx(nx, ny)
                if self.walls[i]:
                    continue
                dist2 = dx * dx + dy * dy
                if dist2 <= r2:
                    falloff = 1.0 - dist2 / (r2 + 1)
                    self.current[i] += amplitude * falloff
        self.drop_count += 1

    def step(self) -> None:
        """Advance the simulation by one time step using the discrete wave equation."""
        c2 = SPEED * SPEED
        damping = self.damping
        cols = self.cols
        cur = self.current
        prev = self.previous
        walls = self.walls
        rows = self.rows

        next_buf = [0.0] * (cols * rows)

        for y in range(1, rows - 1):
            row_off = y * cols
            for x in range(1, cols - 1):
                i = row_off + x
                if walls[i]:
                    # Wall cells stay at zero (reflective boundary)
                    next_buf[i] = 0.0
                    continue

                laplacian = (
                    cur[i - 1] + cur[i + 1]
                    + cur[i - cols] + cur[i + cols]
                    - 4.0 * cur[i]
                )
                next_buf[i] = (2.0 * cur[i] - prev[i] + c2 * laplacian) * damping

        self.previous = cur
        self.current = next_buf
        self.frame += 1

        # Emit from continuous sources
        for src in self.sources:
            if self.frame % SOURCE_INTERVAL == 0:
                self.drop_stone(src.x, src.y, radius=src.radius, amplitude=src.amplitude)
                # Undo the extra drop_count increment (sources aren't user drops)
                self.drop_count -= 1

    def clear_water(self) -> None:
        """Reset the simulation state (keep walls and sources)."""
        n = self.cols * self.rows
        self.current = [0.0] * n
        self.previous = [0.0] * n
        self.frame = 0
        self.drop_count = 0

    def clear_walls(self) -> None:
        """Remove all walls."""
        self.walls = [False] * (self.cols * self.rows)
        self.wall_preset_idx = -1

    def add_source(self, x: int, y: int, amplitude: float = 5.0, radius: int = 1) -> None:
        """Add a continuous wave source at (x, y). If a source already exists at
        that position, remove it instead (toggle behavior)."""
        # Check if there's already a source nearby — remove it
        for i, src in enumerate(self.sources):
            if abs(src.x - x) <= 2 and abs(src.y - y) <= 2:
                self.sources.pop(i)
                return
        self.sources.append(WaveSource(x, y, amplitude=amplitude, radius=radius))

    # ------------------------------------------------------------------
    # Preset wall patterns
    # ------------------------------------------------------------------

    def apply_wall_preset(self, preset_idx: int) -> None:
        """Apply a preset wall pattern, replacing any existing walls."""
        self.clear_walls()
        self.wall_preset_idx = preset_idx
        cx, cy = self.cols // 2, self.rows // 2
        cols, rows = self.cols, self.rows

        def wall(x: int, y: int) -> None:
            if self.in_bounds(x, y):
                self.walls[self.idx(x, y)] = True

        if preset_idx == 0:
            # Rectangle in the center
            for x in range(cx - 12, cx + 12):
                wall(x, cy - 5)
                wall(x, cy + 5)
            for y in range(cy - 5, cy + 5):
                wall(cx - 12, y)
                wall(cx + 12, y)
            # Gap on the left and right
            for dy in range(-1, 2):
                if self.in_bounds(cx - 12, cy + dy):
                    self.walls[self.idx(cx - 12, cy + dy)] = False
                if self.in_bounds(cx + 12, cy + dy):
                    self.walls[self.idx(cx + 12, cy + dy)] = False

        elif preset_idx == 1:
            # Diamond
            size = min(cols, rows) // 4
            for d in range(size):
                wall(cx + d, cy - size + d)
                wall(cx + d, cy + size - d)
                wall(cx - d, cy - size + d)
                wall(cx - d, cy + size - d)

        elif preset_idx == 2:
            # Cross
            arm = min(cols, rows) // 3
            for d in range(-arm, arm + 1):
                wall(cx + d, cy)
                wall(cx, cy + d)
            # Small gap in the center
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if self.in_bounds(cx + dx, cy + dy):
                        self.walls[self.idx(cx + dx, cy + dy)] = False

        elif preset_idx == 3:
            # Circle
            radius = min(cols, rows) // 4
            for y in range(cy - radius, cy + radius + 1):
                for x in range(cx - radius, cx + radius + 1):
                    dx2 = (x - cx)
                    dy2 = (y - cy)
                    dist = math.sqrt(dx2 * dx2 + dy2 * dy2)
                    if abs(dist - radius) < 1.0:
                        wall(x, y)
            # Opening at top
            for dx in range(-2, 3):
                if self.in_bounds(cx + dx, cy - radius):
                    self.walls[self.idx(cx + dx, cy - radius)] = False

        elif preset_idx == 4:
            # Double slit — classic wave interference demo
            wall_x = cx
            slit_width = 1
            slit_sep = 6
            for y in range(2, rows - 2):
                wall(wall_x, y)
            # Cut two slits
            for sw in range(slit_width):
                if self.in_bounds(wall_x, cy - slit_sep // 2 + sw):
                    self.walls[self.idx(wall_x, cy - slit_sep // 2 + sw)] = False
                if self.in_bounds(wall_x, cy + slit_sep // 2 + sw):
                    self.walls[self.idx(wall_x, cy + slit_sep // 2 + sw)] = False

    def cycle_wall_preset(self) -> None:
        """Cycle to the next wall preset (or clear walls if cycling past the end)."""
        self.wall_preset_idx = (self.wall_preset_idx + 1) % (len(WALL_PRESETS) + 1)
        if self.wall_preset_idx < len(WALL_PRESETS):
            self.apply_wall_preset(self.wall_preset_idx)
        else:
            self.clear_walls()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> List[str]:
        """Return a list of strings (one per row) with ANSI-coloured block characters."""
        palette = PALETTES[self.palette_id]
        cur = self.current
        walls = self.walls
        cols = self.cols

        # Build intensity -> color string mapping
        colors: List[str] = []
        for i in range(10):
            r, g, b = palette[i]
            colors.append(f"\033[38;2;{r};{g};{b}m")

        reset = "\033[0m"
        wall_color = "\033[38;2;180;140;100m"
        source_color = "\033[38;2;255;255;0m"  # Yellow for sources

        # Build a set of source positions for rendering
        source_set = set()
        for src in self.sources:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    sx, sy = src.x + dx, src.y + dy
                    if self.in_bounds(sx, sy):
                        source_set.add(self.idx(sx, sy))

        lines: List[str] = []
        for y in range(self.rows):
            row_off = y * cols
            line_parts: List[str] = []
            x = 0
            while x < cols:
                i = row_off + x
                if walls[i]:
                    # Render wall with a brick-like pattern
                    if (x + y) % 3 == 0:
                        line_parts.append(f"{wall_color}▓")
                    elif (x + y) % 3 == 1:
                        line_parts.append(f"{wall_color}▒")
                    else:
                        line_parts.append(f"{wall_color}░")
                    x += 1
                elif i in source_set:
                    # Render source marker
                    line_parts.append(f"{source_color}◉")
                    x += 1
                else:
                    val = cur[i]
                    # Map wave height to intensity 0..9
                    # Negative values are also interesting (troughs)
                    intensity = int(clamp(int((val + 4.0) / 8.0 * 9), 0, 9))
                    # Choose block character based on intensity
                    if intensity <= 1:
                        ch = " "
                    elif intensity <= 3:
                        ch = "░"
                    elif intensity <= 5:
                        ch = "▒"
                    elif intensity <= 7:
                        ch = "▓"
                    else:
                        ch = "█"
                    line_parts.append(f"{colors[intensity]}{ch}")
                    x += 1
            # Append reset at end of each row for clean state
            line_parts.append(reset)
            lines.append("".join(line_parts))

        return lines


# ---------------------------------------------------------------------------
# Interference demo: drop two stones symmetrically
# ---------------------------------------------------------------------------
def interference_drop(sim: RippleSimulator) -> None:
    """Create a classic two-source interference pattern."""
    cx, cy = sim.cols // 2, sim.rows // 2
    sep = max(3, min(sim.cols, sim.rows) // 6)
    sim.drop_stone(cx - sep, cy, radius=2, amplitude=10.0)
    sim.drop_stone(cx + sep, cy, radius=2, amplitude=10.0)


# ---------------------------------------------------------------------------
# Color cycling: smoothly transition between palettes
# ---------------------------------------------------------------------------
def get_cycled_palette(frame: int) -> List[Tuple[int, int, int]]:
    """Generate a palette that smoothly cycles through colors based on the frame number."""
    phase = (frame * 0.02) % 1.0
    # Cycle through hue shifts
    base_palette = PALETTES[1]  # Use ocean as base
    cycled = []
    for i, (r, g, b) in enumerate(base_palette):
        # Shift hue based on frame and position in palette
        hue_shift = math.sin(phase * math.pi * 2 + i * 0.5) * 0.5 + 0.5
        # Rotate through RGB channels
        nr = int(clamp(r + 80 * math.sin(phase * math.pi * 2 + i * 0.7), 0, 255))
        ng = int(clamp(g + 80 * math.sin(phase * math.pi * 2 + i * 0.7 + 2.094), 0, 255))
        nb = int(clamp(b + 80 * math.sin(phase * math.pi * 2 + i * 0.7 + 4.189), 0, 255))
        cycled.append((nr, ng, nb))
    return cycled


def render_with_custom_palette(sim: RippleSimulator, palette: List[Tuple[int, int, int]]) -> List[str]:
    """Render using a custom palette (for color cycling mode)."""
    cur = sim.current
    walls = sim.walls
    cols = sim.cols

    colors = []
    for i in range(min(10, len(palette))):
        r, g, b = palette[i]
        colors.append(f"\033[38;2;{r};{g};{b}m")

    reset = "\033[0m"
    wall_color = "\033[38;2;180;140;100m"
    source_color = "\033[38;2;255;255;0m"

    source_set = set()
    for src in sim.sources:
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                sx, sy = src.x + dx, src.y + dy
                if sim.in_bounds(sx, sy):
                    source_set.add(sim.idx(sx, sy))

    lines: List[str] = []
    for y in range(sim.rows):
        row_off = y * cols
        line_parts: List[str] = []
        for x in range(cols):
            i = row_off + x
            if walls[i]:
                if (x + y) % 3 == 0:
                    line_parts.append(f"{wall_color}▓")
                elif (x + y) % 3 == 1:
                    line_parts.append(f"{wall_color}▒")
                else:
                    line_parts.append(f"{wall_color}░")
            elif i in source_set:
                line_parts.append(f"{source_color}◉")
            else:
                val = cur[i]
                intensity = int(clamp(int((val + 4.0) / 8.0 * 9), 0, 9))
                if intensity <= 1:
                    ch = " "
                elif intensity <= 3:
                    ch = "░"
                elif intensity <= 5:
                    ch = "▒"
                elif intensity <= 7:
                    ch = "▓"
                else:
                    ch = "█"
                line_parts.append(f"{colors[intensity]}{ch}")
        line_parts.append(reset)
        lines.append("".join(line_parts))

    return lines


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    p = argparse.ArgumentParser(
        prog="ripple",
        description="🌊 Terminal Water Ripple Simulator — real-time 2D wave physics in your terminal.",
        epilog="Press Q or Escape to quit. Have fun making waves!",
    )
    p.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    p.add_argument(
        "--cols", type=int, default=COLS, metavar="N",
        help=f"grid width in characters (default: {COLS})",
    )
    p.add_argument(
        "--rows", type=int, default=ROWS, metavar="N",
        help=f"grid height in characters (default: {ROWS})",
    )
    p.add_argument(
        "--fps", type=int, default=FPS, metavar="N",
        help=f"target frames per second (default: {FPS})",
    )
    p.add_argument(
        "--palette", type=int, default=1, choices=range(1, 6), metavar="N",
        help="initial colour palette 1-5 (default: 1)",
    )
    p.add_argument(
        "--speed", type=float, default=SPEED, metavar="C",
        help=f"wave propagation speed (default: {SPEED})",
    )
    p.add_argument(
        "--damping", type=float, default=DAMPING_DEFAULT, metavar="D",
        help=f"wave damping factor 0-1 (default: {DAMPING_DEFAULT})",
    )
    p.add_argument(
        "--rain", action="store_true",
        help="start with rain mode enabled",
    )
    return p


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point: parse args, set up terminal, and run the simulation loop."""
    parser = build_parser()
    args = parser.parse_args()

    # Override globals with CLI args
    global SPEED
    SPEED = max(0.01, min(0.49, args.speed))
    fps = max(1, args.fps)

    sim = RippleSimulator(cols=args.cols, rows=args.rows)
    sim.damping = args.damping
    sim.palette_id = args.palette
    sim.rain_mode = args.rain

    # Hide cursor
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    CLEAR = "\033[2J\033[H"

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    # Set up terminal for raw input
    old_settings = None
    try:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)
    except (ImportError, termios.error):
        pass  # Not a real terminal (e.g., piped)

    def restore() -> None:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()
        if old_settings is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass

    # Initial splash: drop a stone in the center
    sim.drop_stone(sim.cols // 2, sim.rows // 2, radius=3, amplitude=10.0)

    try:
        while True:
            # --- Input ---
            ch: Optional[str] = None
            try:
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    ch = sys.stdin.read(1)
                    if ch == '\x1b':  # ESC sequence
                        ch2 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.01)[0] else ''
                        if ch2 == '[':
                            ch3 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.01)[0] else ''
                            # Arrow keys etc — ignore
                            ch = None
                        elif ch2 == '':
                            ch = 'q'  # bare ESC
                        else:
                            ch = None
            except Exception:
                pass

            if ch in ('q', 'Q', '\x1b'):
                break
            elif ch == ' ':
                x = random.randint(2, sim.cols - 3)
                y = random.randint(2, sim.rows - 3)
                sim.drop_stone(x, y, radius=random.randint(1, 3), amplitude=random.uniform(5, 12))
            elif ch in ('d', 'D'):
                x = random.randint(4, sim.cols - 5)
                y = random.randint(4, sim.rows - 5)
                sim.drop_stone(x, y, radius=5, amplitude=15.0)
            elif ch in ('f', 'F'):
                # Place/remove a continuous wave source
                x = random.randint(3, sim.cols - 4)
                y = random.randint(3, sim.rows - 4)
                sim.add_source(x, y, amplitude=6.0, radius=1)
            elif ch in ('i', 'I'):
                # Interference demo
                interference_drop(sim)
            elif ch in ('r', 'R'):
                sim.rain_mode = not sim.rain_mode
                sim.rain_timer = 0
            elif ch in ('p', 'P'):
                # Cycle wall presets
                sim.cycle_wall_preset()
            elif ch in ('t', 'T'):
                sim.color_cycle = not sim.color_cycle
            elif ch in ('w', 'W'):
                # Toggle a wall at a random position
                wx = random.randint(3, sim.cols - 4)
                wy = random.randint(3, sim.rows - 4)
                # Make a small wall segment
                if random.random() < 0.5:
                    for dx in range(-2, 3):
                        if sim.in_bounds(wx + dx, wy):
                            sim.walls[sim.idx(wx + dx, wy)] = True
                else:
                    for dy in range(-2, 3):
                        if sim.in_bounds(wx, wy + dy):
                            sim.walls[sim.idx(wx, wy + dy)] = True
            elif ch in ('c', 'C'):
                sim.clear_walls()
            elif ch in ('x', 'X'):
                sim.clear_water()
                # Re-drop initial stone
                sim.drop_stone(sim.cols // 2, sim.rows // 2, radius=3, amplitude=10.0)
            elif ch in ('+', '='):
                sim.damping = min(0.995, sim.damping + 0.01)
            elif ch in ('-', '_'):
                sim.damping = max(0.80, sim.damping - 0.01)
            elif ch == '[':
                sim.sim_speed = max(0.25, sim.sim_speed - 0.25)
            elif ch == ']':
                sim.sim_speed = min(4.0, sim.sim_speed + 0.25)
            elif ch is not None and ch in '12345':
                sim.palette_id = int(ch)
                sim.color_cycle = False  # Manual palette overrides cycling

            # --- Rain mode ---
            if sim.rain_mode:
                sim.rain_timer += 1
                if sim.rain_timer % 4 == 0:
                    x = random.randint(2, sim.cols - 3)
                    y = random.randint(2, sim.rows - 3)
                    sim.drop_stone(x, y, radius=random.randint(1, 2), amplitude=random.uniform(3, 8))

            # --- Simulate ---
            steps = max(1, int(sim.sim_speed))
            for _ in range(steps):
                sim.step()

            # --- Render ---
            if sim.color_cycle:
                lines = render_with_custom_palette(sim, get_cycled_palette(sim.frame))
            else:
                lines = sim.render()

            # HUD
            source_indicator = f"  │  Sources: {len(sim.sources)}" if sim.sources else ""
            speed_indicator = f"  │  Speed: {sim.sim_speed:.2f}x" if sim.sim_speed != 1.0 else ""
            preset_name = ""
            if 0 <= sim.wall_preset_idx < len(WALL_PRESETS):
                preset_name = f"  │  Wall: {WALL_PRESETS[sim.wall_preset_idx]}"
            hud = (
                f"  🌊 Water Ripple Simulator  │  "
                f"Drops: {sim.drop_count}  │  "
                f"Palette: {PALETTE_NAMES[sim.palette_id]}"
                f"{'(cycle)' if sim.color_cycle else ''}  │  "
                f"Damping: {sim.damping:.2f}  │  "
                f"Rain: {'ON' if sim.rain_mode else 'OFF'}"
                f"{source_indicator}{speed_indicator}{preset_name}"
                f"  │  Frame: {sim.frame}"
            )
            controls = (
                "  [SPACE] drop  [D] big  [F] source  [I] interfere  "
                "[R] rain  [P] preset  [T] color-cycle  "
                "[W] wall  [C] clear walls  [X] reset  [+/-] damping  "
                "[/] speed  [1-5] palette  [Q] quit"
            )

            output = CLEAR
            output += "\033[38;2;100;180;220m" + hud + "\033[0m\n"
            for line in lines:
                output += line + "\n"
            output += "\033[38;2;140;140;140m" + controls + "\033[0m"

            sys.stdout.write(output)
            sys.stdout.flush()

            time.sleep(1.0 / fps)

    except KeyboardInterrupt:
        pass
    finally:
        restore()
        sys.stdout.write(CLEAR + "Thanks for making waves! 🌊\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()