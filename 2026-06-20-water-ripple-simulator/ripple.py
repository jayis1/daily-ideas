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
  V       Vortex demo (spiral drop pattern)
  R       Toggle rain mode (auto-drops)
  P       Cycle preset wall patterns
  T       Toggle color-cycling mode
  W       Add a random wall segment
  C       Clear all walls
  X       Reset water (clear simulation)
  E       Toggle energy display in HUD
  B       Toggle boundary mode (reflective / absorbing)
  S       Save snapshot to JSON file
  L       Load snapshot from JSON file
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
from array import array as pyarray

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
__version__ = "1.3.0"

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

# Boundary modes
BOUNDARY_REFLECTIVE = "reflective"
BOUNDARY_ABSORBING = "absorbing"

# Default snapshot file
DEFAULT_SNAPSHOT_FILE = "ripple_snapshot.json"


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

    def to_dict(self) -> dict:
        """Serialize to a dict for JSON snapshot."""
        return {"x": self.x, "y": self.y, "amplitude": self.amplitude, "radius": self.radius}

    @classmethod
    def from_dict(cls, d: dict) -> "WaveSource":
        """Deserialize from a dict (from JSON snapshot)."""
        return cls(d["x"], d["y"], d.get("amplitude", 5.0), d.get("radius", 1))


class RippleSimulator:
    """2D wave equation simulation with terminal rendering.

    Supports reflective and absorbing boundary modes, continuous wave sources,
    wall obstacles, multiple colour palettes, and snapshot save/load.
    """

    def __init__(self, cols: int = COLS, rows: int = ROWS):
        if cols < 3 or rows < 3:
            raise ValueError(f"Grid dimensions must be at least 3x3, got {cols}x{rows}")
        self.cols = cols
        self.rows = rows
        n = cols * rows

        # Two buffers for the wave equation (current and previous)
        # Using array('d') for better performance than plain Python lists
        self.current: List[float] = [0.0] * n
        self.previous: List[float] = [0.0] * n

        # Walls / obstacles
        self.walls: List[bool] = [False] * n

        # Continuous wave sources
        self.sources: List[WaveSource] = []

        # State
        self.damping: float = max(0.0, min(1.0, DAMPING_DEFAULT))
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
        self.speed: float = SPEED  # wave propagation speed (per-instance)
        self.boundary_mode: str = BOUNDARY_REFLECTIVE  # or BOUNDARY_ABSORBING
        self.show_energy: bool = False  # display energy in HUD
        self._save_msg: str = ""  # temporary HUD message for save/load feedback
        self._save_counter: int = 0  # frames remaining to show save message

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
    # Energy calculation
    # ------------------------------------------------------------------

    def total_energy(self) -> float:
        """Compute total wave energy (sum of squared amplitudes).

        This is proportional to the physical energy in the system.
        Useful for observing wave decay and conservation properties.
        """
        return sum(v * v for v in self.current)

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
        """Create a circular disturbance centred at (cx, cy).

        The disturbance has a smooth falloff from center to edge,
        producing a natural-looking wave pattern.
        """
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
        """Advance the simulation by one time step using the discrete wave equation.

        The update rule is:
            u(t+1) = (2*u(t) - u(t-1) + c^2 * laplacian(u(t))) * damping

        Boundary handling:
          - Reflective (default): boundary cells are held at 0, causing wave reflection.
          - Absorbing: boundary cells use a simple one-way wave approximation that
            absorbs outgoing waves, reducing reflections at the edges.
        """
        c2 = self.speed * self.speed
        damping = self.damping
        cols = self.cols
        cur = self.current
        prev = self.previous
        walls = self.walls
        rows = self.rows
        absorbing = (self.boundary_mode == BOUNDARY_ABSORBING)

        next_buf = [0.0] * (cols * rows)

        # Interior cells (standard wave equation)
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

        # Boundary handling
        if absorbing:
            # Absorbing boundaries: use first-order approximation to reduce reflections.
            # At edges, we approximate the outgoing wave by setting the boundary value
            # to the value just inside the grid, scaled by (1 - c).
            for x in range(cols):
                # Top row (y=0): copy from y=1
                if not walls[x]:
                    next_buf[x] = cur[x + cols] * (1.0 - self.speed) * damping
                # Bottom row (y=rows-1): copy from y=rows-2
                bot = (rows - 1) * cols + x
                bot_inner = (rows - 2) * cols + x
                if not walls[bot]:
                    next_buf[bot] = cur[bot_inner] * (1.0 - self.speed) * damping
            for y in range(1, rows - 1):
                # Left column (x=0): copy from x=1
                left = y * cols
                if not walls[left]:
                    next_buf[left] = cur[left + 1] * (1.0 - self.speed) * damping
                # Right column (x=cols-1): copy from x=cols-2
                right = y * cols + cols - 1
                if not walls[right]:
                    next_buf[right] = cur[right - 1] * (1.0 - self.speed) * damping
        # else: reflective — boundary cells stay 0 (already initialised)

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
        """Apply a preset wall pattern, replacing any existing walls.

        Available presets:
          0: rectangle   — a hollow rectangle with gaps on left/right
          1: diamond     — a diamond shape
          2: cross       — a plus sign with a small gap in the center
          3: circle      — a circle with an opening at the top
          4: double_slit — classic double-slit interference demonstration
        """
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
    # Snapshot save/load
    # ------------------------------------------------------------------

    def save_snapshot(self, filepath: str = DEFAULT_SNAPSHOT_FILE) -> str:
        """Save the current simulation state to a JSON file.

        Returns the path where the snapshot was saved.
        """
        data = {
            "version": __version__,
            "cols": self.cols,
            "rows": self.rows,
            "current": self.current,
            "previous": self.previous,
            "walls": self.walls,
            "sources": [s.to_dict() for s in self.sources],
            "damping": self.damping,
            "speed": self.speed,
            "sim_speed": self.sim_speed,
            "palette_id": self.palette_id,
            "boundary_mode": self.boundary_mode,
            "frame": self.frame,
            "drop_count": self.drop_count,
            "wall_preset_idx": self.wall_preset_idx,
        }
        with open(filepath, "w") as f:
            json.dump(data, f)
        return filepath

    @classmethod
    def load_snapshot(cls, filepath: str = DEFAULT_SNAPSHOT_FILE) -> "RippleSimulator":
        """Load a simulation state from a JSON snapshot file.

        Raises FileNotFoundError if the file doesn't exist.
        Raises ValueError if the file format is invalid.
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        sim = cls(cols=data["cols"], rows=data["rows"])
        sim.current = data["current"]
        sim.previous = data["previous"]
        sim.walls = data["walls"]
        sim.sources = [WaveSource.from_dict(s) for s in data.get("sources", [])]
        sim.damping = data.get("damping", DAMPING_DEFAULT)
        sim.speed = data.get("speed", SPEED)
        sim.sim_speed = data.get("sim_speed", 1.0)
        sim.palette_id = data.get("palette_id", 1)
        sim.boundary_mode = data.get("boundary_mode", BOUNDARY_REFLECTIVE)
        sim.frame = data.get("frame", 0)
        sim.drop_count = data.get("drop_count", 0)
        sim.wall_preset_idx = data.get("wall_preset_idx", -1)
        return sim

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> List[str]:
        """Return a list of strings (one per row) with ANSI-coloured block characters.

        Wave heights are mapped to 10 intensity levels. Walls show a textured
        brick pattern. Sources are marked with yellow ◉ symbols. NaN and Inf
        values are handled gracefully (shown as mid-intensity).
        """
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
                    # Guard against NaN/Inf which can crash int()
                    if val != val or val == float('inf') or val == float('-inf'):
                        intensity = 4  # Show as mid-level for anomalies
                    else:
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
# Vortex demo: drop stones in a spiral pattern
# ---------------------------------------------------------------------------
def vortex_drop(sim: RippleSimulator) -> None:
    """Create a vortex/spiral pattern by dropping stones in a spiral.

    This produces a visually striking interference pattern that
    demonstrates constructive and destructive interference in a
    circular arrangement.
    """
    cx, cy = sim.cols // 2, sim.rows // 2
    num_drops = 8
    for i in range(num_drops):
        angle = 2 * math.pi * i / num_drops
        radius = min(sim.cols, sim.rows) // 4
        x = int(cx + radius * math.cos(angle))
        y = int(cy + radius * math.sin(angle) * 0.6)  # Slightly squished vertically
        if sim.in_bounds(x, y):
            sim.drop_stone(x, y, radius=2, amplitude=8.0)


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
    """Render using a custom palette (for color cycling mode).

    If the palette has fewer than 10 entries, it is extended by repeating.
    """
    cur = sim.current
    walls = sim.walls
    cols = sim.cols

    # Ensure we have exactly 10 colors by repeating/interpolating if palette is short
    while len(palette) < 10:
        palette = list(palette) + palette  # Double until we have enough
    palette = palette[:10]

    colors = []
    for i in range(10):
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
                # Guard against NaN/Inf which can crash int()
                if val != val or val == float('inf') or val == float('-inf'):
                    intensity = 4
                else:
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
        help=f"grid width in characters, minimum 3 (default: {COLS})",
    )
    p.add_argument(
        "--rows", type=int, default=ROWS, metavar="N",
        help=f"grid height in characters, minimum 3 (default: {ROWS})",
    )
    p.add_argument(
        "--fps", type=int, default=FPS, metavar="N",
        help=f"target frames per second, minimum 1 (default: {FPS})",
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
    p.add_argument(
        "--absorbing", action="store_true",
        help="use absorbing boundary conditions (reduces edge reflections)",
    )
    p.add_argument(
        "--load", type=str, default=None, metavar="FILE",
        help="load a snapshot from a JSON file to resume a previous session",
    )
    p.add_argument(
        "--energy", action="store_true",
        help="display total wave energy in the HUD",
    )
    return p


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point: parse args, set up terminal, and run the simulation loop."""
    parser = build_parser()
    args = parser.parse_args()

    # Validate and clamp parameters
    cols = max(3, args.cols)
    rows = max(3, args.rows)
    fps = max(1, args.fps)
    speed = max(0.01, min(0.49, args.speed))
    damping = max(0.0, min(1.0, args.damping))

    # Load snapshot if requested
    if args.load:
        try:
            sim = RippleSimulator.load_snapshot(args.load)
            print(f"Loaded snapshot from {args.load}")
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading snapshot: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        sim = RippleSimulator(cols=cols, rows=rows)
        sim.speed = speed
        sim.damping = damping
        sim.palette_id = args.palette
        sim.rain_mode = args.rain

    sim.boundary_mode = BOUNDARY_ABSORBING if args.absorbing else BOUNDARY_REFLECTIVE
    sim.show_energy = args.energy

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
    if not args.load:
        sim.drop_stone(sim.cols // 2, sim.rows // 2, radius=3, amplitude=10.0)

    snapshot_dir = os.path.dirname(os.path.abspath(__file__))

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
            elif ch in ('v', 'V'):
                # Vortex demo
                vortex_drop(sim)
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
            elif ch in ('e', 'E'):
                sim.show_energy = not sim.show_energy
            elif ch in ('b', 'B'):
                # Toggle boundary mode
                if sim.boundary_mode == BOUNDARY_REFLECTIVE:
                    sim.boundary_mode = BOUNDARY_ABSORBING
                else:
                    sim.boundary_mode = BOUNDARY_REFLECTIVE
            elif ch in ('s', 'S'):
                # Save snapshot
                filepath = os.path.join(snapshot_dir, DEFAULT_SNAPSHOT_FILE)
                try:
                    path = sim.save_snapshot(filepath)
                    sim._save_msg = f"Saved to {path}"
                    sim._save_counter = 30  # Show for ~30 frames
                except Exception as ex:
                    sim._save_msg = f"Save error: {ex}"
                    sim._save_counter = 30
            elif ch in ('l', 'L'):
                # Load snapshot
                filepath = os.path.join(snapshot_dir, DEFAULT_SNAPSHOT_FILE)
                try:
                    loaded = RippleSimulator.load_snapshot(filepath)
                    # Transfer loaded state into current sim
                    sim.current = loaded.current
                    sim.previous = loaded.previous
                    sim.walls = loaded.walls
                    sim.sources = loaded.sources
                    sim.damping = loaded.damping
                    sim.speed = loaded.speed
                    sim.frame = loaded.frame
                    sim.drop_count = loaded.drop_count
                    sim.wall_preset_idx = loaded.wall_preset_idx
                    sim._save_msg = f"Loaded from {filepath}"
                    sim._save_counter = 30
                except Exception as ex:
                    sim._save_msg = f"Load error: {ex}"
                    sim._save_counter = 30
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
            energy_str = ""
            if sim.show_energy:
                energy = sim.total_energy()
                energy_str = f"  │  Energy: {energy:.1f}"
            boundary_str = f"  │  Boundary: {sim.boundary_mode[:3].upper()}"
            save_msg = ""
            if sim._save_msg and sim._save_counter > 0:
                save_msg = f"  │  {sim._save_msg}"
                sim._save_counter -= 1
                if sim._save_counter <= 0:
                    sim._save_msg = ""

            hud = (
                f"  🌊 Water Ripple Simulator v{__version__}  │  "
                f"Drops: {sim.drop_count}  │  "
                f"Palette: {PALETTE_NAMES[sim.palette_id]}"
                f"{'(cycle)' if sim.color_cycle else ''}  │  "
                f"Damping: {sim.damping:.2f}  │  "
                f"Rain: {'ON' if sim.rain_mode else 'OFF'}"
                f"{source_indicator}{speed_indicator}{preset_name}"
                f"{energy_str}{boundary_str}{save_msg}"
                f"  │  Frame: {sim.frame}"
            )
            controls = (
                "  [SPACE] drop  [D] big  [F] source  [I] interfere  "
                "[V] vortex  [R] rain  [P] preset  [T] color-cycle  "
                "[W] wall  [C] clear walls  [X] reset  [E] energy  "
                "[B] boundary  [S] save  [L] load  [+/-] damping  "
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